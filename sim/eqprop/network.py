"""Generic resistive network definition and KCL equilibrium solver."""

from dataclasses import dataclass, field
from typing import Dict, List, Tuple
import numpy as np
from scipy.optimize import root

from .diode import DiodeParams, BAT42, diode_current_into


@dataclass(frozen=True)
class WeightParams:
    """Physical constraints of the weight resistors (MCP4251-104 digital pots)."""
    R_series: float = 1200.0    # Series protection resistor (ohm)
    R_min: float = 1590.0       # Tap 256: 390 wiper + 1200 series
    R_max: float = 101200.0     # Tap 1: 100k + 1200 series
    N_taps: int = 256           # MCP4251 tap positions
    R_pot_full: float = 100000.0  # Full-scale pot resistance (ohm)

    @property
    def G_min(self):
        return 1.0 / self.R_max

    @property
    def G_max(self):
        return 1.0 / self.R_min

    def resistance_to_tap(self, r):
        """Map continuous resistance to nearest MCP4251 tap (1..N_taps)."""
        r_pot = r - self.R_series
        tap = round((self.R_pot_full - r_pot) * self.N_taps / self.R_pot_full)
        return int(np.clip(tap, 1, self.N_taps))

    def tap_to_resistance(self, tap):
        """Map MCP4251 tap position to exact resistance."""
        r_pot = self.R_pot_full * (1.0 - tap / self.N_taps)
        return r_pot + self.R_series

    def quantize_weights(self, weights):
        """Round-trip weights through hardware tap positions.

        Returns (quantized_weights, taps).
        """
        taps = [self.resistance_to_tap(r) for r in weights]
        return np.array([self.tap_to_resistance(t) for t in taps]), taps


# Standard MCP4251-104 parameters
MCP4251 = WeightParams()


@dataclass
class Network:
    """Topology and component parameters for a resistive analog network.

    Nodes are numbered globally: fixed nodes first (0..n_fixed-1),
    then free nodes (n_fixed..n_fixed+n_free-1). The solver returns
    voltages for the free nodes only.

    Attributes:
        n_fixed: Number of clamped (input/bias) nodes.
        n_free: Number of free (solved) nodes.
        connections: Weight topology as (global_src, global_dst) pairs.
            One entry per weight resistor.
        diode_nodes: Maps free-node index (0-based into free array) to
            the reference voltage for its antiparallel diode pair.
        output_pos_idx: Free-node index of the positive output node.
        output_neg_idx: Free-node index of the negative output node.
        nudge_signs: Maps free-node index to nudge sign (+1 or -1).
            Nudge current = sign * beta * error for that node.
        spice_names: SPICE node name for each global node index.
        diode_params: Diode model parameters.
        weight_params: Weight resistor constraints.
    """
    n_fixed: int
    n_free: int
    connections: List[Tuple[int, int]]
    diode_nodes: Dict[int, float] = field(default_factory=dict)
    output_pos_idx: int = 0
    output_neg_idx: int = 1
    nudge_signs: Dict[int, float] = field(default_factory=dict)
    spice_names: List[str] = field(default_factory=list)
    diode_params: DiodeParams = field(default_factory=lambda: BAT42)
    weight_params: WeightParams = field(default_factory=lambda: MCP4251)

    @property
    def n_weights(self):
        return len(self.connections)

    def prediction(self, free_voltages):
        """Compute output prediction from free-node voltages."""
        return free_voltages[self.output_pos_idx] - free_voltages[self.output_neg_idx]

    def nudge_currents(self, beta, error):
        """Build nudge current vector for the free nodes.

        Returns array of length n_free with nudge current for each node.
        """
        nudge = np.zeros(self.n_free)
        for free_idx, sign in self.nudge_signs.items():
            nudge[free_idx] = sign * beta * error
        return nudge


def resistive_initial_guess(net, inputs, weights):
    """Linear pre-solve ignoring diodes — good starting point for Newton.

    For each free node, solve the resistive KCL assuming no diode current.
    This avoids the degenerate Jacobian at V_MID where diode conductance
    is near-zero.
    """
    fixed = list(inputs)
    G_mat = np.zeros((net.n_free, net.n_free))
    I_vec = np.zeros(net.n_free)

    for w, (i, j) in zip(weights, net.connections):
        g = 1.0 / w
        i_free = i - net.n_fixed if i >= net.n_fixed else -1
        j_free = j - net.n_fixed if j >= net.n_fixed else -1

        if i_free >= 0 and j_free >= 0:
            G_mat[i_free, i_free] += g
            G_mat[j_free, j_free] += g
            G_mat[i_free, j_free] -= g
            G_mat[j_free, i_free] -= g
        elif i_free >= 0:
            G_mat[i_free, i_free] += g
            I_vec[i_free] += g * fixed[j]
        elif j_free >= 0:
            G_mat[j_free, j_free] += g
            I_vec[j_free] += g * fixed[i]

    return np.linalg.solve(G_mat, I_vec)


def solve_network(net, inputs, weights, nudge=None, x0=None):
    """Solve KCL for network equilibrium.

    Args:
        net: Network topology and parameters.
        inputs: Voltages for the fixed (clamped) nodes.
        weights: Resistance values for each connection (ohms).
        nudge: Optional current injection vector (length n_free).
            Positive = current flowing into the node.
        x0: Optional initial guess for free-node voltages.

    Returns:
        Array of free-node voltages at equilibrium.
    """
    fixed = list(inputs)
    if nudge is None:
        nudge = np.zeros(net.n_free)

    def kcl(state):
        all_v = fixed + list(state)
        I = np.zeros(net.n_free)

        # Resistive currents from weight connections
        for w, (i, j) in zip(weights, net.connections):
            current = (all_v[i] - all_v[j]) / w
            if j >= net.n_fixed:
                I[j - net.n_fixed] += current
            if i >= net.n_fixed:
                I[i - net.n_fixed] -= current

        # Diode activation currents
        for free_idx, v_ref in net.diode_nodes.items():
            I[free_idx] += diode_current_into(
                state[free_idx], v_ref, net.diode_params
            )

        # External current injection (nudge)
        I += nudge

        return I

    if x0 is None:
        x0 = resistive_initial_guess(net, inputs, weights)

    sol = root(kcl, x0, method='hybr', tol=1e-12)
    return sol.x
