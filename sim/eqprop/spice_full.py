"""Full-circuit SPICE netlist generator with hardware non-idealities.

Models the complete analog signal path as it exists on the PCB:
  - Voltage dividers generating V_LOW, V_HIGH, V_MID references
  - Op-amp buffers (MCP6004 rail-to-rail, LM324 limited swing)
  - CD4053B analog mux on-resistance (100 ohm typical)
  - Weight resistors (1.2k series + variable pot)
  - BAT42 antiparallel diode pairs (activation functions)
  - Howland current pumps (MCP6002 + 4x10k + 1M per pump)

Imports run_ngspice and parse_raw_file from spice.py (no duplication).
"""

import os
import numpy as np

from .network import Network, solve_network
from .spice import run_ngspice, generate_netlist


def _lib_path():
    """Return absolute path to the behavioral op-amp library."""
    return os.path.join(
        os.path.dirname(__file__), "opamp_models", "behavioral.lib"
    )


def generate_full_netlist(net, weights, inputs, nudge=None, mux_resistance=100.0):
    """Generate a full-circuit SPICE netlist including hardware non-idealities.

    Args:
        net: Network with spice_names and connections.
        weights: Resistance array (one per connection).
        inputs: Voltages for fixed (clamped) nodes.
        nudge: Optional current injection array (length n_free).
            When None, Howland pumps are included with DAC at midpoint (zero current).
        mux_resistance: CD4053B on-resistance in ohms (default 100).

    Returns:
        SPICE netlist as a string.
    """
    names = net.spice_names
    r_series = net.weight_params.R_series

    lines = [
        "* Full-circuit EqProp network with hardware non-idealities",
        f".include {_lib_path()}",
        ".model BAT42 D(Is=1e-7 Rs=12 N=1.1 Cjo=15p Vj=0.25 M=0.5)",
        "",
    ]

    # ── Power rail ──────────────────────────────────────────────
    lines += [
        "* Power rail",
        "V_VCC vcc 0 5.0",
        "",
    ]

    # ── Voltage dividers + op-amp buffers ───────────────────────
    # V_LOW: 8k/2k divider from VCC → 1.0V, buffered by MCP6004
    # V_HIGH: 2k/8k divider from VCC → 4.0V, buffered by MCP6004
    # V_MID: 10k/10k divider from VCC → 2.5V, buffered by LM324 (x3)
    lines += [
        "* Voltage reference dividers",
        "R_div_low_hi vcc vlow_div 8000",
        "R_div_low_lo vlow_div 0 2000",
        "R_div_high_hi vcc vhigh_div 2000",
        "R_div_high_lo vhigh_div 0 8000",
        "R_div_mid_hi vcc vmid_div 10000",
        "R_div_mid_lo vmid_div 0 10000",
        "",
        "* Op-amp buffers (voltage followers)",
        "* MCP6004 rail-to-rail: V_LOW and V_HIGH",
        "X_buf_vlow vlow_div vlow vcc 0 vlow opamp_rr",
        "X_buf_vhigh vhigh_div vhigh vcc 0 vhigh opamp_rr",
        "* LM324 limited swing: V_MID for H1, H2, and Howland pump",
        "X_buf_vmid_h1 vmid_div vmid_h1 vcc 0 vmid_h1 opamp_lm324",
        "X_buf_vmid_h2 vmid_div vmid_h2 vcc 0 vmid_h2 opamp_lm324",
        "X_buf_vmid_pump vmid_div vmid_pump vcc 0 vmid_pump opamp_lm324",
        "",
    ]

    # ── CD4053B mux: route input voltages ───────────────────────
    # The mux selects between vlow and vhigh for each input node.
    # Each mux output has on-resistance in series.
    # Input encoding: 1.0V = LOW, 4.0V = HIGH
    lines.append("* CD4053B mux routing (on-resistance models)")

    # Map input node indices to which buffer they connect to
    # Nodes 0-3 are X1, X1c, X2, X2c — routed through mux
    # Nodes 4-5 are V_LOW, V_HIGH — direct from buffer (no mux)
    for idx in range(4):  # X1, X1c, X2, X2c
        node_name = names[idx]
        v_in = inputs[idx]
        # Select which buffered voltage the mux routes
        if abs(v_in - 1.0) < 0.1:
            source = "vlow"
        else:
            source = "vhigh"
        lines.append(f"R_mux_{node_name} {source} {node_name} {mux_resistance}")

    lines.append("")

    # ── Weight resistors ────────────────────────────────────────
    lines.append("* Weight resistors (series protection + variable pot)")
    for i in range(net.n_weights):
        ci, cj = net.connections[i]
        src = names[ci]
        dst = names[cj]
        r_pot = weights[i] - r_series

        # For mux connections (W1-W8), source is the mux output node
        # For bias connections (W9-W12), source is buffered vlow/vhigh
        # For hidden-to-output (W13-W16), source is the free node
        mid = f"w{i+1}m"
        lines.append(f"R_s{i+1} {src} {mid} {r_series}")
        lines.append(f"R_W{i+1} {mid} {dst} {r_pot:.1f}")

    lines.append("")

    # ── BAT42 diode pairs ───────────────────────────────────────
    lines.append("* Activation functions (antiparallel BAT42 pairs)")
    d_count = 1
    for free_idx in sorted(net.diode_nodes):
        global_idx = net.n_fixed + free_idx
        node = names[global_idx]
        # Map diode reference to the corresponding buffered V_MID node
        if free_idx == 0:
            vmid = "vmid_h1"
        elif free_idx == 1:
            vmid = "vmid_h2"
        else:
            vmid = f"vmid_{node}"
        lines.append(f"D{d_count}a {node} {vmid} BAT42")
        lines.append(f"D{d_count}b {vmid} {node} BAT42")
        d_count += 1

    lines.append("")

    # ── Howland current pumps ───────────────────────────────────
    # Always included. DAC voltage controls nudge current:
    #   I_out = (V_dac - V_MID) / R_SET = (V_dac - 2.5) / 1e6
    # Free phase: V_dac = 2.5V → I_out = 0
    lines.append("* Howland current pumps (MCP6002 + precision resistors)")

    if nudge is not None and np.any(nudge != 0):
        # Compute DAC voltages from nudge currents
        # nudge[2] = current into YP, nudge[3] = current into YN
        i_yp = nudge[net.output_pos_idx] if len(nudge) > net.output_pos_idx else 0.0
        i_yn = nudge[net.output_neg_idx] if len(nudge) > net.output_neg_idx else 0.0
        v_dac_a = i_yp * 1e6 + 2.5  # I = (V_dac - 2.5) / 1M
        v_dac_b = i_yn * 1e6 + 2.5
    else:
        v_dac_a = 2.5
        v_dac_b = 2.5

    # Pump A → YP node
    lines += [
        f"V_DAC_A dac_a 0 {v_dac_a}",
        "R_H1 dac_a pump_a_inp 10000",
        "R_SET_A pump_a_inp yp 1e6",
        "R_H2 vmid_pump pump_a_inn 10000",
        "R_H3 pump_a_out pump_a_inn 10000",
        "R_H4 pump_a_out yp 10000",
        "X_pump_a pump_a_inp pump_a_inn vcc 0 pump_a_out opamp_rr",
        "",
    ]

    # Pump B → YN node
    lines += [
        f"V_DAC_B dac_b 0 {v_dac_b}",
        "R_H5 dac_b pump_b_inp 10000",
        "R_SET_B pump_b_inp yn 1e6",
        "R_H6 vmid_pump pump_b_inn 10000",
        "R_H7 pump_b_out pump_b_inn 10000",
        "R_H8 pump_b_out yn 10000",
        "X_pump_b pump_b_inp pump_b_inn vcc 0 pump_b_out opamp_rr",
        "",
    ]

    # ── Analysis ────────────────────────────────────────────────
    # Save all nodes of interest: free nodes + diagnostic nodes
    free_nodes = " ".join(f"v({names[net.n_fixed + i]})" for i in range(net.n_free))
    diag_nodes = "v(vlow) v(vhigh) v(vmid_h1) v(vmid_h2) v(vmid_pump)"
    input_nodes = " ".join(f"v({names[i]})" for i in range(4))

    lines += [
        ".op",
        "",
        f".save {free_nodes} {diag_nodes} {input_nodes}",
        "",
        ".end",
    ]

    return "\n".join(lines)


def run_full_simulation(net, weights, inputs, nudge=None, mux_resistance=100.0):
    """Generate full-circuit netlist, run ngspice, return voltages.

    Returns:
        Dict mapping variable name -> voltage, or None on failure.
    """
    netlist = generate_full_netlist(net, weights, inputs, nudge, mux_resistance)
    return run_ngspice(netlist)


def cross_validate_full(net, weights, dataset, tolerance_pct=2.0):
    """Compare full-circuit SPICE vs Python solver for a set of input patterns.

    Uses the Python solver (without mux resistance) as reference, since the
    full-circuit SPICE includes mux and other non-idealities that create
    expected small differences.

    Args:
        net: Network topology.
        weights: Resistance array.
        dataset: List of (inputs, target) tuples.
        tolerance_pct: Maximum allowed percentage error.

    Returns:
        True if all free-node voltages match within tolerance.
    """
    all_ok = True

    for inputs, _ in dataset:
        py_v = solve_network(net, inputs, weights)
        spice_v = run_full_simulation(net, weights, inputs)

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


def compare_simulations(net, weights, dataset):
    """Three-way comparison: Python solver vs ideal SPICE vs full-circuit SPICE.

    Prints a diagnostic table showing node voltages and deltas for each
    input pattern. Useful for quantifying hardware non-ideality impact.

    Args:
        net: Network topology.
        weights: Resistance array.
        dataset: List of (inputs, target) tuples.

    Returns:
        List of dicts with comparison data per pattern.
    """
    from .spice import run_ngspice as _run, generate_netlist as _gen_ideal

    labels = ["(0,0)", "(0,1)", "(1,0)", "(1,1)"]
    results = []

    print(f"\n{'='*80}")
    print("THREE-WAY CROSS-VALIDATION: Python vs Ideal SPICE vs Full-Circuit SPICE")
    print(f"{'='*80}")
    print(f"{'Pattern':<9} {'Node':<6} {'Python':>8} {'Ideal':>8} "
          f"{'Full':>8} {'Ideal-Full':>11}")
    print("-" * 80)

    for idx, (inputs, target) in enumerate(dataset):
        label = labels[idx] if idx < len(labels) else f"({idx})"

        # Python solver
        py_v = solve_network(net, inputs, weights)

        # Ideal SPICE
        ideal_netlist = _gen_ideal(net, weights, inputs)
        ideal_v = _run(ideal_netlist)

        # Full-circuit SPICE
        full_v = run_full_simulation(net, weights, inputs)

        pattern_data = {"label": label, "target": target, "nodes": {}}

        for free_idx in range(net.n_free):
            global_idx = net.n_fixed + free_idx
            node = net.spice_names[global_idx]
            spice_name = f"v({node})"

            py_val = py_v[free_idx]

            ideal_val = None
            if ideal_v:
                ideal_val = ideal_v.get(spice_name) or ideal_v.get(node)

            full_val = None
            if full_v:
                full_val = full_v.get(spice_name) or full_v.get(node)

            delta = None
            if ideal_val is not None and full_val is not None:
                delta = ideal_val - full_val

            pattern_data["nodes"][node] = {
                "python": py_val,
                "ideal": ideal_val,
                "full": full_val,
                "delta": delta,
            }

            ideal_str = f"{ideal_val:.4f}" if ideal_val is not None else "  N/A  "
            full_str = f"{full_val:.4f}" if full_val is not None else "  N/A  "
            delta_str = f"{delta:+.4f}V" if delta is not None else "   N/A   "

            print(f"{label:<9} {node:<6} {py_val:8.4f} {ideal_str:>8} "
                  f"{full_str:>8} {delta_str:>11}")

        # Also print prediction line
        py_pred = net.prediction(py_v)
        ideal_pred = None
        full_pred = None
        if ideal_v:
            yp = ideal_v.get("v(yp)") or ideal_v.get("yp")
            yn = ideal_v.get("v(yn)") or ideal_v.get("yn")
            if yp is not None and yn is not None:
                ideal_pred = yp - yn
        if full_v:
            yp = full_v.get("v(yp)") or full_v.get("yp")
            yn = full_v.get("v(yn)") or full_v.get("yn")
            if yp is not None and yn is not None:
                full_pred = yp - yn

        pred_delta = None
        if ideal_pred is not None and full_pred is not None:
            pred_delta = ideal_pred - full_pred

        ideal_p = f"{ideal_pred:.4f}" if ideal_pred is not None else "  N/A  "
        full_p = f"{full_pred:.4f}" if full_pred is not None else "  N/A  "
        delta_p = f"{pred_delta:+.4f}V" if pred_delta is not None else "   N/A   "
        print(f"{label:<9} {'pred':<6} {py_pred:8.4f} {ideal_p:>8} "
              f"{full_p:>8} {delta_p:>11}")
        print()

        pattern_data["prediction"] = {
            "python": py_pred, "ideal": ideal_pred,
            "full": full_pred, "delta": pred_delta,
        }
        results.append(pattern_data)

    # Summary: diagnostic voltages from last full simulation
    if full_v:
        print("Diagnostic node voltages (last pattern):")
        for diag in ["vlow", "vhigh", "vmid_h1", "vmid_h2", "vmid_pump"]:
            v = full_v.get(f"v({diag})") or full_v.get(diag)
            if v is not None:
                print(f"  {diag:>12}: {v:.4f}V")
        print()

    return results
