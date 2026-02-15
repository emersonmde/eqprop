"""Tests for the KCL equilibrium solver.

Verifies the generic solver against analytical solutions, symmetry
properties, and known LTspice reference voltages.
"""

import numpy as np
import pytest

from eqprop.network import Network, solve_network, resistive_initial_guess
from eqprop.diode import BAT42
from eqprop.xor import make_xor_network, make_inputs, V_MID


# ─── Helpers ────────────────────────────────────────────────

def _make_old_3input_network():
    """Original 3-input topology from sim2_full_network.cir.

    Nodes: 0=X1, 1=X2, 2=XBIAS, 3=H1, 4=H2, 5=YP, 6=YN
    """
    connections = [
        (0, 3), (0, 4),   # X1 -> H1, H2
        (1, 3), (1, 4),   # X2 -> H1, H2
        (2, 3), (2, 4),   # XBIAS -> H1, H2
        (3, 5), (3, 6),   # H1 -> YP, YN
        (4, 5), (4, 6),   # H2 -> YP, YN
    ]
    return Network(
        n_fixed=3,
        n_free=4,
        connections=connections,
        diode_nodes={0: V_MID, 1: V_MID},  # H1, H2
        output_pos_idx=2,
        output_neg_idx=3,
        nudge_signs={2: +1.0, 3: -1.0},
    )


# ─── Analytical Tests ──────────────────────────────────────

class TestVolteDivider:
    """Two voltage sources connected to one free node via resistors."""

    def test_equal_resistors(self):
        """With equal R, free node = average of sources."""
        net = Network(
            n_fixed=2, n_free=1,
            connections=[(0, 2), (1, 2)],
        )
        v = solve_network(net, [1.0, 3.0], [10000.0, 10000.0])
        assert v[0] == pytest.approx(2.0, abs=1e-6)

    def test_unequal_resistors(self):
        """Weighted average: V = (V1/R1 + V2/R2) / (1/R1 + 1/R2)."""
        net = Network(
            n_fixed=2, n_free=1,
            connections=[(0, 2), (1, 2)],
        )
        v = solve_network(net, [0.0, 5.0], [10000.0, 40000.0])
        expected = (0.0 / 10000 + 5.0 / 40000) / (1 / 10000 + 1 / 40000)
        assert v[0] == pytest.approx(expected, abs=1e-6)

    def test_three_sources(self):
        """Three sources into one node."""
        net = Network(
            n_fixed=3, n_free=1,
            connections=[(0, 3), (1, 3), (2, 3)],
        )
        R = [5000.0, 10000.0, 20000.0]
        V_in = [1.0, 3.0, 5.0]
        v = solve_network(net, V_in, R)
        expected = sum(vi / ri for vi, ri in zip(V_in, R)) / sum(1 / ri for ri in R)
        assert v[0] == pytest.approx(expected, abs=1e-6)


class TestSymmetry:
    """XOR network symmetry properties with uniform weights."""

    def test_uniform_weights_hidden_symmetry(self):
        """With uniform weights, H1 == H2 for any input pattern."""
        net = make_xor_network()
        weights = np.full(16, 21200.0)
        for v_x1, v_x2 in [(1.0, 1.0), (1.0, 4.0), (4.0, 1.0), (4.0, 4.0)]:
            v = solve_network(net, make_inputs(v_x1, v_x2), weights)
            assert v[0] == pytest.approx(v[1], abs=1e-6), \
                f"H1 != H2 for pattern ({v_x1}, {v_x2})"

    def test_uniform_weights_output_symmetry(self):
        """With uniform weights, YP == YN (zero prediction)."""
        net = make_xor_network()
        weights = np.full(16, 21200.0)
        for v_x1, v_x2 in [(1.0, 1.0), (1.0, 4.0), (4.0, 1.0), (4.0, 4.0)]:
            v = solve_network(net, make_inputs(v_x1, v_x2), weights)
            assert v[2] == pytest.approx(v[3], abs=1e-6), \
                f"YP != YN for pattern ({v_x1}, {v_x2})"


class TestDiodeClamping:
    """Hidden nodes should stay within diode-clamped range."""

    def test_hidden_nodes_clamped(self):
        """H1, H2 stay in 1.8-3.2V with strong (low-R) weights."""
        net = make_xor_network()
        weights = np.full(16, 5000.0)
        for v_x1, v_x2 in [(1.0, 1.0), (4.0, 4.0), (1.0, 4.0)]:
            v = solve_network(net, make_inputs(v_x1, v_x2), weights)
            assert 1.8 < v[0] < 3.2, f"H1={v[0]:.3f}V out of range"
            assert 1.8 < v[1] < 3.2, f"H2={v[1]:.3f}V out of range"


# ─── LTspice Reference Values ──────────────────────────────

class TestLTspiceReference:
    """Validate against known LTspice results from the original 3-input topology.

    These reference values come from sim2_full_network.cir with uniform
    21.2k weights. The generic solver with a 3-input Network instance
    must match — no duplicated solver code.
    """

    @pytest.fixture
    def old_net(self):
        return _make_old_3input_network()

    @pytest.mark.parametrize("name,inputs,expected_h1", [
        ("(1,1)", [4.0, 4.0, 2.5], 2.70137),
        ("(0,0)", [1.0, 1.0, 2.5], 2.29863),
        ("(1,0)", [4.0, 1.0, 2.5], 2.50000),
    ])
    def test_h1_voltage(self, old_net, name, inputs, expected_h1):
        w = np.full(10, 21200.0)
        v = solve_network(old_net, inputs, w)
        err_pct = abs(v[0] - expected_h1) / expected_h1 * 100
        assert err_pct < 1.0, \
            f"Pattern {name}: V(h1)={v[0]:.5f} vs LTspice {expected_h1:.5f} ({err_pct:.3f}%)"


class TestNudgeSlope:
    """Nudge current propagation from output to hidden nodes."""

    def test_nudge_slope_ratio(self):
        """Output nudge should propagate to hidden with ~4x ratio."""
        net = _make_old_3input_network()
        w = np.full(10, 21200.0)
        inputs = [1.0, 4.0, 2.5]

        v0 = solve_network(net, inputs, w)
        nudge = np.zeros(4)
        nudge[2] = 10e-6  # 10uA into YP
        vn = solve_network(net, inputs, w, nudge=nudge)

        ratio = (vn[2] - v0[2]) / (vn[0] - v0[0])
        assert abs(ratio - 4.0) < 0.5, f"Nudge ratio {ratio:.2f}, expected ~4.0"
