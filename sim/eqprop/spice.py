"""SPICE netlist generation and ngspice cross-validation.

Generates netlists from a Network definition, runs ngspice in batch mode,
parses .raw output files, and compares results against the Python solver.
"""

import os
import struct
import subprocess
import tempfile
import numpy as np

from .network import Network, solve_network


def ngspice_available():
    """Check if ngspice is installed and accessible."""
    try:
        result = subprocess.run(
            ["ngspice", "--version"],
            capture_output=True, text=True, timeout=5,
        )
        return result.returncode == 0
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False


def generate_netlist(net, weights, inputs, nudge=None):
    """Generate a SPICE netlist string from a Network definition.

    Args:
        net: Network with spice_names and connections.
        weights: Resistance array (one per connection).
        inputs: Voltages for fixed (clamped) nodes.
        nudge: Optional current injection array (length n_free).

    Returns:
        SPICE netlist as a string.
    """
    names = net.spice_names
    r_series = net.weight_params.R_series

    lines = [
        "* Auto-generated EqProp network",
        ".model BAT42 D(Is=1e-7 Rs=12 N=1.1 Cjo=15p Vj=0.25 M=0.5)",
        "",
        "* Input voltages",
    ]

    # Voltage sources for fixed nodes
    for idx in range(net.n_fixed):
        label = names[idx].upper()
        node = names[idx]
        lines.append(f"V_{label} {node} 0 {inputs[idx]}")

    # Reference voltages for diode pairs
    lines.append("")
    lines.append("* Reference voltages")
    for free_idx, v_ref in net.diode_nodes.items():
        global_idx = net.n_fixed + free_idx
        node = names[global_idx]
        lines.append(f"V_MID_{node.upper()} vmid_{node} 0 {v_ref}")

    # Weight resistors
    lines.append("")
    lines.append("* Weight resistors (series protection + variable pot)")
    for i in range(net.n_weights):
        ci, cj = net.connections[i]
        src = names[ci]
        dst = names[cj]
        r_pot = weights[i] - r_series
        mid = f"w{i+1}m"
        lines.append(f"R_s{i+1} {src} {mid} {r_series}")
        lines.append(f"R_W{i+1} {mid} {dst} {r_pot:.1f}")

    # Diode pairs
    lines.append("")
    lines.append("* Activation functions (antiparallel BAT42 pairs)")
    d_count = 1
    for free_idx in sorted(net.diode_nodes):
        global_idx = net.n_fixed + free_idx
        node = names[global_idx]
        vmid = f"vmid_{node}"
        lines.append(f"D{d_count}a {node} {vmid} BAT42")
        lines.append(f"D{d_count}b {vmid} {node} BAT42")
        d_count += 1

    # Nudge current sources
    if nudge is not None and np.any(nudge != 0):
        lines.append("")
        lines.append("* Nudge current sources")
        for free_idx in range(net.n_free):
            if nudge[free_idx] != 0.0:
                global_idx = net.n_fixed + free_idx
                node = names[global_idx]
                lines.append(f"I_nudge_{node} 0 {node} {nudge[free_idx]}")

    # Save free-node voltages
    save_nodes = " ".join(
        f"v({names[net.n_fixed + i]})" for i in range(net.n_free)
    )

    lines += [
        "",
        ".op",
        "",
        f".save {save_nodes}",
        "",
        ".end",
    ]

    return "\n".join(lines)


def run_ngspice(netlist_str):
    """Run ngspice in batch mode and return node voltages.

    Returns:
        Dict mapping variable name -> voltage, or None on failure.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        netlist_path = os.path.join(tmpdir, "circuit.cir")
        raw_path = os.path.join(tmpdir, "output.raw")
        log_path = os.path.join(tmpdir, "output.log")

        with open(netlist_path, "w") as f:
            f.write(netlist_str)

        result = subprocess.run(
            ["ngspice", "-b", "-r", raw_path, "-o", log_path, netlist_path],
            capture_output=True, text=True, timeout=30,
        )

        if result.returncode != 0:
            return None

        return parse_raw_file(raw_path)


def parse_raw_file(raw_path):
    """Parse ngspice binary .raw file and extract node voltages.

    Falls back to ASCII parser if no binary marker is found.
    """
    with open(raw_path, "rb") as f:
        content = f.read()

    header_end = content.find(b"Binary:\n")
    if header_end == -1:
        return parse_raw_file_ascii(raw_path)

    header = content[:header_end].decode("ascii", errors="replace")
    binary_data = content[header_end + len(b"Binary:\n"):]

    variables = []
    in_variables = False
    for line in header.split("\n"):
        line = line.strip()
        if line.startswith("Variables:"):
            in_variables = True
            continue
        if line.startswith("Values:") or line.startswith("Binary:"):
            break
        if in_variables and line:
            parts = line.split()
            if len(parts) >= 3:
                variables.append(parts[1])

    n_vars = len(variables)
    if len(binary_data) < n_vars * 8:
        return None

    values = struct.unpack(f"<{n_vars}d", binary_data[:n_vars * 8])
    return {name: val for name, val in zip(variables, values)}


def parse_raw_file_ascii(raw_path):
    """Fallback parser for ASCII .raw files."""
    with open(raw_path, "r") as f:
        content = f.read()

    variables = []
    values = {}
    in_variables = False
    in_values = False

    for line in content.split("\n"):
        line = line.strip()
        if line.startswith("Variables:"):
            in_variables = True
            continue
        if line.startswith("Values:"):
            in_variables = False
            in_values = True
            continue
        if in_variables and line:
            parts = line.split()
            if len(parts) >= 3:
                variables.append(parts[1])
        if in_values and line:
            parts = line.split()
            if len(parts) == 2:
                idx = int(parts[0])
                val = float(parts[1])
                if idx < len(variables):
                    values[variables[idx]] = val
            elif len(parts) == 1:
                try:
                    val = float(parts[0])
                    idx = len(values)
                    if idx < len(variables):
                        values[variables[idx]] = val
                except ValueError:
                    pass

    return values if values else None


def cross_validate(net, weights, dataset, tolerance_pct=1.0):
    """Compare Python solver against ngspice for a set of input patterns.

    Args:
        net: Network topology.
        weights: Resistance array.
        dataset: List of (inputs, target) or (inputs, label) tuples.
        tolerance_pct: Maximum allowed percentage error.

    Returns:
        True if all node voltages match within tolerance.
    """
    all_ok = True

    for inputs, _ in dataset:
        py_v = solve_network(net, inputs, weights)
        netlist = generate_netlist(net, weights, inputs)
        spice_v = run_ngspice(netlist)

        if spice_v is None:
            all_ok = False
            continue

        for free_idx in range(net.n_free):
            global_idx = net.n_fixed + free_idx
            node = net.spice_names[global_idx]
            spice_name = f"v({node})"

            py_val = py_v[free_idx]
            sp_val = spice_v.get(spice_name)
            if sp_val is None:
                sp_val = spice_v.get(node)
            if sp_val is None:
                all_ok = False
                continue

            if abs(py_val) > 1e-6:
                err_pct = abs(py_val - sp_val) / abs(py_val) * 100
            else:
                err_pct = abs(py_val - sp_val) * 100

            if err_pct >= tolerance_pct:
                all_ok = False

    return all_ok
