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
