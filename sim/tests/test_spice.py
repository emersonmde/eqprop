"""Tests for ngspice cross-validation.

These tests require ngspice to be installed (brew install ngspice).
They are automatically skipped if ngspice is not available.
"""

import numpy as np
import pytest

from eqprop.spice import ngspice_available, cross_validate
from eqprop.training import train
from eqprop.xor import make_xor_network, XOR_DATASET


pytestmark = pytest.mark.skipif(
    not ngspice_available(),
    reason="ngspice not installed (brew install ngspice)",
)


@pytest.fixture
def net():
    return make_xor_network()


class TestCrossValidation:
    def test_uniform_weights(self, net):
        """Python matches ngspice within 1% for uniform 21.2k weights."""
        weights = np.full(16, 21200.0)
        assert cross_validate(net, weights, XOR_DATASET)

    def test_random_weights(self, net):
        """Python matches ngspice within 1% for random weights."""
        wp = net.weight_params
        rng = np.random.RandomState(99)
        G_rand = rng.uniform(wp.G_min, wp.G_max, 16)
        weights = 1.0 / G_rand
        assert cross_validate(net, weights, XOR_DATASET)

    def test_trained_weights(self, net):
        """Python matches ngspice within 1% at the actual trained operating point."""
        result = train(net, XOR_DATASET, seed=42, log_fn=lambda *a: None)
        assert result.converged
        assert cross_validate(net, result.weights, XOR_DATASET)
