"""Tests for EqProp training loop.

Verifies XOR convergence, correct predictions, and weight bounds.
"""

import numpy as np
import pytest

from eqprop.network import solve_network
from eqprop.training import train
from eqprop.xor import make_xor_network, XOR_DATASET


@pytest.fixture(scope="module")
def trained():
    """Train once and share across tests in this module."""
    net = make_xor_network()
    result = train(
        net, XOR_DATASET,
        seed=42,
        log_fn=lambda epoch, loss, preds: None,  # silent
    )
    return net, result


class TestConvergence:
    def test_loss_below_threshold(self, trained):
        _, result = trained
        assert result.final_loss < 0.005, \
            f"Loss {result.final_loss:.6f} did not converge below 0.005"

    def test_converged_flag(self, trained):
        _, result = trained
        assert result.converged, "Training did not report convergence"

    def test_converged_within_5000_epochs(self, trained):
        _, result = trained
        assert result.epochs_run < 5000, \
            f"Converged at epoch {result.epochs_run}, expected < 5000"


class TestPredictions:
    @pytest.mark.parametrize("pattern_idx,label,target", [
        (0, "(0,0)", 0.0),
        (1, "(0,1)", 0.3),
        (2, "(1,0)", 0.3),
        (3, "(1,1)", 0.0),
    ])
    def test_xor_pattern(self, trained, pattern_idx, label, target):
        net, result = trained
        inputs, _ = XOR_DATASET[pattern_idx]
        v = solve_network(net, inputs, result.weights)
        pred = net.prediction(v)

        if target > 0.1:
            assert pred > 0.1, f"Pattern {label}: pred={pred:+.4f}, expected > 0.1"
        else:
            assert abs(pred) < 0.1, f"Pattern {label}: pred={pred:+.4f}, expected ~0"


class TestWeightBounds:
    def test_weights_within_range(self, trained):
        net, result = trained
        wp = net.weight_params
        for i, r in enumerate(result.weights):
            assert wp.R_min <= r <= wp.R_max, \
                f"W{i+1}={r:.0f} ohm outside [{wp.R_min}, {wp.R_max}]"


class TestQuantization:
    def test_quantized_xor_passes(self, trained):
        """XOR predictions survive round-trip through hardware tap positions."""
        net, result = trained
        q_weights, taps = net.weight_params.quantize_weights(result.weights)
        for inputs, target in XOR_DATASET:
            v = solve_network(net, inputs, q_weights)
            pred = net.prediction(v)
            if target > 0.1:
                assert pred > 0.1, \
                    f"Quantized pred={pred:+.4f}, expected > 0.1 for target={target}"
            else:
                assert abs(pred) < 0.1, \
                    f"Quantized pred={pred:+.4f}, expected ~0 for target={target}"

    def test_quantization_error_bounded(self, trained):
        """Interior weights shift by at most half a tap step (~195 ohm).

        Weights clamped at R_min/R_max by training may not sit on the tap
        grid, so we skip them — they're already at maximum/minimum attenuation.
        """
        net, result = trained
        wp = net.weight_params
        q_weights, _ = wp.quantize_weights(result.weights)
        half_step = wp.R_pot_full / wp.N_taps / 2.0  # ~195 ohm
        for i, (r, qr) in enumerate(zip(result.weights, q_weights)):
            if r == wp.R_min or r == wp.R_max:
                continue  # boundary-clamped, not on tap grid
            assert abs(r - qr) <= half_step + 1e-6, \
                f"W{i+1}: |{r:.0f} - {qr:.0f}| = {abs(r-qr):.0f} > {half_step:.0f}"

    def test_tap_round_trip_idempotent(self, trained):
        """tap_to_resistance(resistance_to_tap(r)) produces a fixed point."""
        net, result = trained
        wp = net.weight_params
        q_weights, taps = wp.quantize_weights(result.weights)
        q2_weights, taps2 = wp.quantize_weights(q_weights)
        np.testing.assert_array_equal(q_weights, q2_weights)
        assert taps == taps2

    def test_sensitivity_to_uniform_tap_shift(self, trained):
        """XOR still classifies correctly with all taps shifted +/-2 positions."""
        net, result = trained
        wp = net.weight_params
        _, taps = wp.quantize_weights(result.weights)
        for direction in (+2, -2):
            shifted_taps = [int(np.clip(t + direction, 1, wp.N_taps)) for t in taps]
            shifted_weights = np.array([wp.tap_to_resistance(t) for t in shifted_taps])
            for inputs, target in XOR_DATASET:
                v = solve_network(net, inputs, shifted_weights)
                pred = net.prediction(v)
                if target > 0.1:
                    assert pred > 0.05, \
                        f"Shift {direction:+d}: pred={pred:+.4f}, expected > 0.05"
                else:
                    assert abs(pred) < 0.15, \
                        f"Shift {direction:+d}: pred={pred:+.4f}, expected < 0.15"
