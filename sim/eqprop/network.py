"""Generic resistive network definition and KCL equilibrium solver."""

from dataclasses import dataclass, field
from typing import Dict, List, Tuple
import numpy as np
from scipy.optimize import root, least_squares

from .diode import DiodeParams, BAT42, diode_current_into


@dataclass(frozen=True)
class WeightParams:
    """Physical constraints of the weight resistors (MCP4251-104 digital pots)."""
    # MCP4251 DS22060B: 256 resistor segments, 257 wiper positions;
    # 75 ohm typical wiper resistance. PCB ties W to B, so the tail shunts RW.
    # https://ww1.microchip.com/downloads/aemDocuments/documents/OTH/ProductDocuments/DataSheets/22060b.pdf
    R_series: float = 2490.0
    N_taps: int = 256
    R_pot_full: float = 100000.0
    R_wiper: float = 75.0

    @property
    def R_min(self):
        return self.tap_to_resistance(self.N_taps)

    @property
    def R_max(self):
        return self.tap_to_resistance(0)

    @property
    def G_min(self):
        return 1.0 / self.R_max

    @property
    def G_max(self):
        return 1.0 / self.R_min

    def resistance_to_tap(self, r):
        """Nearest nominal resistance, including the tied W/B terminal circuit."""
        return min(range(self.N_taps + 1), key=lambda t: abs(self.tap_to_resistance(t) - r))

    def tap_to_resistance(self, tap):
        """Nominal two-terminal resistance; device tolerance needs calibration."""
        if not 0 <= tap <= self.N_taps:
            raise ValueError("MCP4251 tap must be in 0..256")
        tail = self.R_pot_full * tap / self.N_taps
        shunt = self.R_wiper * tail / (self.R_wiper + tail)
        return self.R_series + self.R_pot_full - tail + shunt

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
    mux_connections: frozenset = field(default_factory=frozenset)
    mux_resistance: float = 0.0

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

    for w_idx, (w, (i, j)) in enumerate(zip(weights, net.connections)):
        r_eff = w + (net.mux_resistance if w_idx in net.mux_connections else 0.0)
        g = 1.0 / r_eff
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
        for w_idx, (w, (i, j)) in enumerate(zip(weights, net.connections)):
            r_eff = w + (net.mux_resistance if w_idx in net.mux_connections else 0.0)
            current = (all_v[i] - all_v[j]) / r_eff
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
    # Numerical acceptance budget, not a hardware specification: 0.1 nA
    # corresponds to 10 uV across 100 kohm, below one ADS1115 LSB at
    # +/-4.096 V (125 uV; TI ADS1115 datasheet, full-scale-range table).
    # MINPACK can report stalled progress at an accurate root, so evaluate
    # physical KCL directly instead of trusting only its success flag.
    residual = kcl(sol.x)
    if not np.all(np.isfinite(residual)) or np.max(np.abs(residual)) > 1e-10:
        # A resistor-only seed can lie deep in exponential diode conduction.
        # Restart near each diode reference with a trust-region least-squares
        # solve. Express residuals in microamps for numerical conditioning;
        # acceptance still uses the original KCL in amperes below.
        seed = resistive_initial_guess(net, inputs, weights)
        for idx, reference in net.diode_nodes.items():
            seed[idx] = reference
        sol = least_squares(lambda v: kcl(v) / 1e-6, seed,
                            x_scale='jac', ftol=1e-12, xtol=1e-12,
                            gtol=1e-12, max_nfev=200)
        residual = kcl(sol.x)
    if (not np.all(np.isfinite(sol.x))
            or not np.all(np.isfinite(residual))
            or np.max(np.abs(residual)) > 1e-10):
        raise RuntimeError(
            f"Equilibrium failed KCL check: {sol.message}; residual={residual} A"
        )
    return sol.x
