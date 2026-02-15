"""Equilibrium propagation gradient computation and training loop."""

from dataclasses import dataclass
from typing import Callable, List, Optional, Tuple
import numpy as np

from .network import Network, solve_network


@dataclass
class TrainResult:
    """Result of a training run."""
    weights: np.ndarray
    final_loss: float
    converged: bool
    epochs_run: int


def eqprop_gradient(net, inputs, weights, target, beta, free_eq=None):
    """Compute EqProp gradient for one pattern using symmetric nudge.

    The gradient of the cost w.r.t. each weight's conductance is:
        dC/dG_k = (dv_pos_k^2 - dv_neg_k^2) / (4 * beta)
    where dv is the voltage drop across weight k in the nudged states.

    Args:
        net: Network topology.
        inputs: Clamped input voltages.
        weights: Current resistance values.
        target: Target differential voltage.
        beta: Nudge strength.
        free_eq: Optional free-phase equilibrium (avoids re-solving).

    Returns:
        (gradient_array, prediction, free_eq_voltages)
    """
    if free_eq is None:
        free_eq = solve_network(net, inputs, weights)

    pred = net.prediction(free_eq)
    error = target - pred

    # Symmetric nudge: +beta and -beta directions
    nudge_pos = net.nudge_currents(beta, error)
    nudge_neg = net.nudge_currents(-beta, error)

    V_pos = solve_network(net, inputs, weights, nudge=nudge_pos, x0=free_eq)
    V_neg = solve_network(net, inputs, weights, nudge=nudge_neg, x0=free_eq)

    all_pos = list(inputs) + list(V_pos)
    all_neg = list(inputs) + list(V_neg)

    grad = np.zeros(net.n_weights)
    for w_idx, (i, j) in enumerate(net.connections):
        dv_pos = all_pos[i] - all_pos[j]
        dv_neg = all_neg[i] - all_neg[j]
        grad[w_idx] = (dv_pos ** 2 - dv_neg ** 2) / (4 * beta)

    return grad, pred, free_eq


def train(
    net: Network,
    dataset: List[Tuple],
    n_epochs: int = 50000,
    lr: float = 5e-9,
    beta: float = 1e-5,
    seed: int = 42,
    patience: int = 500,
    min_delta: float = 1e-6,
    log_fn: Optional[Callable] = None,
    log_interval: int = 5000,
) -> TrainResult:
    """Train the network via equilibrium propagation.

    Early stopping triggers on either condition:
      - loss < 0.005: converged successfully
      - loss hasn't improved by min_delta in `patience` epochs: stuck on plateau

    Args:
        net: Network topology and parameters.
        dataset: List of (inputs, target) tuples.
        n_epochs: Maximum training epochs.
        lr: Learning rate for conductance updates.
        beta: Nudge strength.
        seed: Random seed for weight initialization.
        patience: Epochs without improvement before stopping.
        min_delta: Minimum loss improvement to reset patience.
        log_fn: Optional callback(epoch, loss, predictions) for logging.
            If None, prints to stdout.
        log_interval: Epochs between log messages.

    Returns:
        TrainResult with final weights, loss, convergence flag, and epoch count.
    """
    wp = net.weight_params
    rng = np.random.RandomState(seed)
    G_init = rng.uniform(wp.G_min, wp.G_max, net.n_weights)
    weights = 1.0 / G_init
    verbose = log_fn is None

    if verbose:
        def log_fn(epoch, loss, preds):
            pred_str = " ".join(f"{p:+.3f}" for p in preds)
            print(f"  Epoch {epoch:5d}  loss={loss:.6f}  preds=[{pred_str}]")
        print(f"  lr={lr:.0e}  beta={beta:.0e}  epochs={n_epochs}  patience={patience}")

    best_loss = float('inf')
    stall_count = 0

    for epoch in range(n_epochs):
        epoch_loss = 0.0
        grad_acc = np.zeros(net.n_weights)

        for inputs, target in dataset:
            grad, pred, _ = eqprop_gradient(net, inputs, weights, target, beta)
            grad_acc += grad
            epoch_loss += 0.5 * (target - pred) ** 2

        # Batch weight update in conductance space
        for w_idx in range(net.n_weights):
            G = 1.0 / weights[w_idx]
            G = np.clip(G - lr * grad_acc[w_idx], wp.G_min, wp.G_max)
            weights[w_idx] = 1.0 / G

        # Plateau detection
        if epoch_loss < best_loss - min_delta:
            best_loss = epoch_loss
            stall_count = 0
        else:
            stall_count += 1

        # Logging
        if epoch % log_interval == 0 or epoch == n_epochs - 1:
            preds = []
            for inputs, target in dataset:
                v = solve_network(net, inputs, weights)
                preds.append(net.prediction(v))
            log_fn(epoch, epoch_loss, preds)

        # Converged
        if epoch_loss < 0.005:
            preds = [net.prediction(solve_network(net, inp, weights))
                     for inp, _ in dataset]
            log_fn(epoch, epoch_loss, preds)
            return TrainResult(weights, epoch_loss, True, epoch)

        # Plateau
        if stall_count >= patience:
            preds = [net.prediction(solve_network(net, inp, weights))
                     for inp, _ in dataset]
            log_fn(epoch, epoch_loss, preds)
            if verbose:
                print(f"  *** Plateau detected at epoch {epoch} "
                      f"(no improvement for {patience} epochs, "
                      f"best_loss={best_loss:.6f}) ***")
            return TrainResult(weights, epoch_loss, False, epoch)

    return TrainResult(weights, epoch_loss, False, n_epochs)
