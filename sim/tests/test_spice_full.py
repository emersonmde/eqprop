"""Tests for full-circuit SPICE simulation with hardware non-idealities.

These tests require ngspice to be installed (brew install ngspice).
They validate that the full analog signal path (dividers, buffers, mux,
Howland pumps) produces correct results before PCB fabrication.
"""

import numpy as np
import pytest

from eqprop.spice import ngspice_available
from eqprop.spice_full import (
    generate_full_netlist,
    run_full_simulation,
    cross_validate_full,
)
from eqprop.network import solve_network
from eqprop.training import train
from eqprop.xor import make_xor_network, make_inputs, XOR_DATASET


pytestmark = pytest.mark.skipif(
    not ngspice_available(),
    reason="ngspice not installed (brew install ngspice)",
)


@pytest.fixture
def net():
    return make_xor_network()


@pytest.fixture
def hw_net():
    return make_xor_network(hardware=True)


@pytest.fixture
def uniform_weights():
    return np.full(16, 21200.0)


class TestVoltageReferences:
    """Verify that divider + buffer circuits produce correct reference voltages."""

    def test_vlow_reference(self, net, uniform_weights):
        """V_LOW buffer output should be within 5mV of 1.0V."""
        inputs = make_inputs(1.0, 1.0)
        result = run_full_simulation(net, uniform_weights, inputs)
        assert result is not None, "ngspice failed"
        v_low = result.get("v(vlow)") or result.get("vlow")
        assert v_low is not None, "v(vlow) not found in output"
        assert abs(v_low - 1.0) < 0.005, f"V_LOW={v_low:.4f}V, expected 1.000V"

    def test_vhigh_reference(self, net, uniform_weights):
        """V_HIGH buffer output should be within 5mV of 4.0V."""
        inputs = make_inputs(1.0, 1.0)
        result = run_full_simulation(net, uniform_weights, inputs)
        assert result is not None, "ngspice failed"
        v_high = result.get("v(vhigh)") or result.get("vhigh")
        assert v_high is not None, "v(vhigh) not found in output"
        assert abs(v_high - 4.0) < 0.005, f"V_HIGH={v_high:.4f}V, expected 4.000V"

    def test_vmid_references(self, net, uniform_weights):
        """V_MID buffers should be within 5mV of 2.5V."""
        inputs = make_inputs(1.0, 1.0)
        result = run_full_simulation(net, uniform_weights, inputs)
        assert result is not None, "ngspice failed"
        for name in ["vmid_h1", "vmid_h2", "vmid_pump"]:
            v = result.get(f"v({name})") or result.get(name)
            assert v is not None, f"v({name}) not found in output"
            assert abs(v - 2.5) < 0.005, f"{name}={v:.4f}V, expected 2.500V"


class TestMuxVoltageSag:
    """Verify CD4053B mux on-resistance causes expected voltage sag."""

    def test_input_node_sag(self, net, uniform_weights):
        """Input nodes through mux should sag slightly from ideal voltage."""
        inputs = make_inputs(1.0, 4.0)  # X1=LOW, X2=HIGH
        result = run_full_simulation(net, uniform_weights, inputs)
        assert result is not None, "ngspice failed"

        # X1 is driven through mux from vlow (1.0V)
        # Sag should be small but nonzero due to 100Ω mux + load
        v_x1 = result.get("v(x1)") or result.get("x1")
        assert v_x1 is not None, "v(x1) not found"
        # With uniform 21.2k weights, current through mux is small
        # so sag should be under 20mV
        assert abs(v_x1 - 1.0) < 0.020, f"X1={v_x1:.4f}V, sag too large"

        # X2 is driven through mux from vhigh (4.0V)
        v_x2 = result.get("v(x2)") or result.get("x2")
        assert v_x2 is not None, "v(x2) not found"
        assert abs(v_x2 - 4.0) < 0.020, f"X2={v_x2:.4f}V, sag too large"


class TestFullVsIdeal:
    """Compare full-circuit SPICE against ideal SPICE / Python solver."""

    def test_uniform_weights_full_vs_ideal(self, net, uniform_weights):
        """Full-circuit should match Python solver within 3% for uniform weights."""
        assert cross_validate_full(net, uniform_weights, XOR_DATASET, tolerance_pct=3.0)

    def test_random_weights_full_vs_ideal(self, net):
        """Full-circuit should match Python solver within 3% for random weights."""
        wp = net.weight_params
        rng = np.random.RandomState(99)
        G_rand = rng.uniform(wp.G_min, wp.G_max, 16)
        weights = 1.0 / G_rand
        assert cross_validate_full(net, weights, XOR_DATASET, tolerance_pct=3.0)

    def test_trained_weights_full_circuit(self, net):
        """Trained weights should classify all 4 XOR patterns in full-circuit SPICE."""
        result = train(net, XOR_DATASET, seed=42, log_fn=lambda *a: None)
        assert result.converged, "Training did not converge"

        threshold = 0.05  # Relaxed vs Python (0.1) due to hardware non-idealities
        for inputs, target in XOR_DATASET:
            spice_v = run_full_simulation(net, result.weights, inputs)
            assert spice_v is not None, "ngspice failed"

            yp = spice_v.get("v(yp)") or spice_v.get("yp")
            yn = spice_v.get("v(yn)") or spice_v.get("yn")
            assert yp is not None and yn is not None, "Output nodes not found"

            pred = yp - yn
            if target > 0.1:
                assert pred > threshold, (
                    f"Pattern target={target}: pred={pred:.4f}V should be > {threshold}"
                )
            else:
                assert abs(pred) < 0.1, (
                    f"Pattern target={target}: pred={pred:.4f}V should be ~0"
                )


class TestHowlandPump:
    """Verify Howland current pump behavior."""

    def test_zero_current_at_midpoint(self, net, uniform_weights):
        """DAC at 2.5V (midpoint) should produce ~0 pump output current."""
        inputs = make_inputs(1.0, 1.0)
        # No nudge → DAC at midpoint → zero current
        result_free = run_full_simulation(net, uniform_weights, inputs, nudge=None)
        assert result_free is not None, "ngspice failed"

        # Also run with explicit zero nudge
        nudge_zero = np.zeros(net.n_free)
        result_nudge = run_full_simulation(net, uniform_weights, inputs, nudge=nudge_zero)
        assert result_nudge is not None, "ngspice failed"

        # YP and YN voltages should be nearly identical between free and zero-nudge
        for node in ["yp", "yn"]:
            v_free = result_free.get(f"v({node})") or result_free.get(node)
            v_nudge = result_nudge.get(f"v({node})") or result_nudge.get(node)
            assert v_free is not None and v_nudge is not None
            assert abs(v_free - v_nudge) < 0.001, (
                f"{node}: free={v_free:.4f}V vs zero-nudge={v_nudge:.4f}V"
            )

    def test_nudge_perturbs_output(self, net, uniform_weights):
        """Nonzero nudge current should measurably shift output node voltages."""
        inputs = make_inputs(1.0, 4.0)

        # Free phase (no nudge)
        result_free = run_full_simulation(net, uniform_weights, inputs)
        assert result_free is not None

        # Nudged phase: inject 1µA into YP, -1µA into YN
        nudge = np.zeros(net.n_free)
        nudge[net.output_pos_idx] = 1e-6   # +1µA into YP
        nudge[net.output_neg_idx] = -1e-6   # -1µA into YN
        result_nudge = run_full_simulation(net, uniform_weights, inputs, nudge=nudge)
        assert result_nudge is not None

        # YP should increase, YN should decrease
        yp_free = result_free.get("v(yp)") or result_free.get("yp")
        yp_nudge = result_nudge.get("v(yp)") or result_nudge.get("yp")
        yn_free = result_free.get("v(yn)") or result_free.get("yn")
        yn_nudge = result_nudge.get("v(yn)") or result_nudge.get("yn")

        assert yp_free is not None and yp_nudge is not None
        assert yn_free is not None and yn_nudge is not None

        # 1µA through ~10-50kΩ output impedance → 10-50mV shift
        delta_yp = yp_nudge - yp_free
        delta_yn = yn_nudge - yn_free

        assert delta_yp > 0.001, f"YP shift {delta_yp*1000:.1f}mV too small"
        assert delta_yn < -0.001, f"YN shift {delta_yn*1000:.1f}mV too small"


class TestPythonMuxResistance:
    """Verify Python solver with hardware=True accounts for mux resistance."""

    def test_mux_resistance_changes_voltages(self):
        """hardware=True should produce different voltages than hardware=False."""
        net_ideal = make_xor_network(hardware=False)
        net_hw = make_xor_network(hardware=True)
        # Non-uniform weights break the symmetry that makes all nodes sit
        # at exactly V_MID regardless of mux resistance
        rng = np.random.RandomState(99)
        wp = net_ideal.weight_params
        G_rand = rng.uniform(wp.G_min, wp.G_max, 16)
        weights = 1.0 / G_rand
        inputs = make_inputs(1.0, 4.0)

        v_ideal = solve_network(net_ideal, inputs, weights)
        v_hw = solve_network(net_hw, inputs, weights)

        # Mux resistance should shift voltages measurably
        assert not np.allclose(v_ideal, v_hw, atol=1e-6), (
            "hardware=True should produce different voltages"
        )

        # But the difference should be small (within ~20mV at typical weights)
        assert np.allclose(v_ideal, v_hw, atol=0.020), (
            f"Voltage difference too large: max delta={np.max(np.abs(v_ideal - v_hw)):.4f}V"
        )

    def test_mux_resistance_default_preserves_behavior(self):
        """hardware=False (default) should match original behavior exactly."""
        net_default = make_xor_network()
        net_explicit = make_xor_network(hardware=False)
        weights = np.full(16, 21200.0)
        inputs = make_inputs(4.0, 1.0)

        v_default = solve_network(net_default, inputs, weights)
        v_explicit = solve_network(net_explicit, inputs, weights)

        np.testing.assert_array_equal(v_default, v_explicit)

    def test_hardware_training_converges(self):
        """XOR training should still converge with mux resistance (may need more epochs)."""
        net = make_xor_network(hardware=True)
        result = train(net, XOR_DATASET, seed=42, log_fn=lambda *a: None)
        assert result.converged, (
            f"Training failed to converge with hardware=True "
            f"(loss={result.final_loss:.6f} after {result.epochs_run} epochs)"
        )
