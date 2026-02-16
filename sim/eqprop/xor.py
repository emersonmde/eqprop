"""XOR topology definition, dataset, and training entry point.

This is the first proof-of-concept topology: 6 inputs, 2 hidden, 2 outputs,
16 weight resistors. Future topologies (e.g. larger classifiers) would be
sibling modules following the same pattern.

Entry point: python -m eqprop.xor
"""

import sys
import numpy as np

from .network import Network, solve_network

# ─── Voltage Rails ──────────────────────────────────────────
V_MID = 2.5     # Diode return rail (V)
V_LOW = 1.0     # Low bias input (V)
V_HIGH = 4.0    # High bias input (V)


def make_xor_network():
    """Create the 16-weight complementary-input XOR network.

    Node numbering (global):
        0=X1, 1=X1_comp, 2=X2, 3=X2_comp, 4=V_LOW, 5=V_HIGH,
        6=H1, 7=H2, 8=YP, 9=YN

    Free nodes (0-indexed into free array):
        0=H1, 1=H2, 2=YP, 3=YN
    """
    connections = [
        (0, 6),   # W1:  X1 -> H1
        (0, 7),   # W2:  X1 -> H2
        (1, 6),   # W3:  X1_comp -> H1
        (1, 7),   # W4:  X1_comp -> H2
        (2, 6),   # W5:  X2 -> H1
        (2, 7),   # W6:  X2 -> H2
        (3, 6),   # W7:  X2_comp -> H1
        (3, 7),   # W8:  X2_comp -> H2
        (4, 6),   # W9:  V_LOW -> H1
        (4, 7),   # W10: V_LOW -> H2
        (5, 6),   # W11: V_HIGH -> H1
        (5, 7),   # W12: V_HIGH -> H2
        (6, 8),   # W13: H1 -> YP
        (6, 9),   # W14: H1 -> YN
        (7, 8),   # W15: H2 -> YP
        (7, 9),   # W16: H2 -> YN
    ]

    return Network(
        n_fixed=6,
        n_free=4,
        connections=connections,
        diode_nodes={0: V_MID, 1: V_MID},     # H1, H2 have diode pairs
        output_pos_idx=2,                       # YP
        output_neg_idx=3,                       # YN
        nudge_signs={2: +1.0, 3: -1.0},        # nudge into YP, out of YN
        spice_names=[
            "x1", "x1c", "x2", "x2c", "vlow", "vhigh",
            "h1", "h2", "yp", "yn",
        ],
    )


def make_inputs(v_x1, v_x2):
    """Build the 6-element input vector from X1 and X2 voltages.

    Complementary inputs enable effective negative weights:
        w_eff = g(X1->H) - g(X1_comp->H)
    """
    return [v_x1, 5.0 - v_x1, v_x2, 5.0 - v_x2, V_LOW, V_HIGH]


# XOR dataset: (inputs, target differential voltage)
# Target 0.3V is achievable given diode clamping limits hidden nodes
# to ~2.2-2.8V range, yielding max ~0.4V output differential.
XOR_DATASET = [
    (make_inputs(1.0, 1.0), 0.0),   # (0,0) -> 0
    (make_inputs(1.0, 4.0), 0.3),   # (0,1) -> 1
    (make_inputs(4.0, 1.0), 0.3),   # (1,0) -> 1
    (make_inputs(4.0, 4.0), 0.0),   # (1,1) -> 0
]


def test_xor(net, weights, threshold=0.1):
    """Verify trained weights produce correct XOR outputs.

    Returns True if all 4 patterns are classified correctly.
    """
    labels = ["(0,0)", "(0,1)", "(1,0)", "(1,1)"]
    ok = True

    print("\n" + "=" * 60)
    print("XOR VERIFICATION")
    print("=" * 60)

    for (inputs, target), label in zip(XOR_DATASET, labels):
        v = solve_network(net, inputs, weights)
        pred = net.prediction(v)
        if target > 0.1:
            correct = pred > threshold
        else:
            correct = abs(pred) < threshold
        status = "PASS" if correct else "FAIL"
        print(f"  {label}: pred={pred:+.4f}V  target={target:.1f}V  [{status}]")
        if not correct:
            ok = False

    print(f"\n  Final weights:")
    for i, r in enumerate(weights):
        tap = net.weight_params.resistance_to_tap(r)
        print(f"    W{i+1:2d}: R={r:8.0f} ohm  (tap={tap:3d})")

    print(f"\n  XOR test: {'PASS' if ok else 'FAIL'}")
    return ok


def main():
    from .training import train

    net = make_xor_network()

    print("=" * 60)
    print("TRAINING (complementary inputs + V_LOW/V_HIGH bias, 16 weights)")
    print("=" * 60)

    result = train(net, XOR_DATASET, seed=42)

    if result.converged:
        print(f"  *** Converged at epoch {result.epochs_run} ***")
    else:
        print(f"  *** Did not converge after {result.epochs_run} epochs ***")

    passed = test_xor(net, result.weights)

    print()
    if passed:
        print("SUCCESS: Network learned XOR via equilibrium propagation.")
    else:
        if not result.converged:
            print("Did not converge. Try: lr=5e-10 or beta=5e-5")
        print("FAILED: XOR not learned.")

    sys.exit(0 if passed else 1)


if __name__ == "__main__":
    main()
