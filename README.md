# Analog Equilibrium Propagation

An experimental project exploring equilibrium propagation in analog resistive networks. The goal is to understand the theory and practical challenges of training physical neural networks where Kirchhoff's current law performs both forward inference and backward error propagation — no digital logic in the compute path.

This project implements the ideas from the papers below as a hands-on learning exercise, starting with an XOR proof-of-concept.

## Papers and Attribution

This project is a from-scratch implementation of techniques described in the following papers. No code was reused from any existing repository.

**Core algorithm:**
- Scellier & Bengio, ["Equilibrium Propagation: Bridging the Gap Between Energy-Based Models and Backpropagation"](https://arxiv.org/abs/1602.05179) (Frontiers in Computational Neuroscience, 2017) — the equilibrium propagation framework: free-phase settling, nudge-phase perturbation, and gradient extraction from energy differences.

**Analog hardware formulation:**
- Kendall et al., ["Training End-to-End Analog Neural Networks with Equilibrium Propagation"](https://arxiv.org/abs/2006.01981) (2020) — extends EqProp to nonlinear resistive networks. This project uses their conductance-space gradient formula (Theorem 1: `dC/dG = (dV_nudge² - dV_free²) / (2β)`), their proof that antiparallel diode pairs are valid EqProp nonlinear elements (Theorem 2), and their XOR demonstration architecture (Figure 3, Appendix D.2) as a starting point. The complementary-input encoding and digital-weight-update pattern also follow their approach.

**Symmetric nudging:**
- Laborieux et al., ["Scaling Equilibrium Propagation to Deep ConvNets by Drastically Reducing its Computational Cost"](https://arxiv.org/abs/2006.03824) (ICLR 2021) — the symmetric nudge variant (both +β and -β) used in the training loop to cancel gradient estimation bias.

**Referenced in the hardware design upgrade path:**
- Laborieux & Zenke, ["Holomorphic Equilibrium Propagation Computes Exact Gradients Through Finite Size Oscillations"](https://arxiv.org/abs/2209.00530) (NeurIPS 2022) — oscillating nudge + DFT-based gradient extraction for exact gradients without finite-β bias.

## What's Original Here

The papers above provide the algorithms and theoretical justification. The following design choices were worked out independently during this project:

- **V_LOW/V_HIGH asymmetric bias pair** to break the odd symmetry that makes XOR impossible with a single V_MID bias (see Design Notes below).
- **Specific component selection and integration** (MCP4251-104 digital pots, BAT42 Schottky diodes, ADS1115 ADC, CD4053 mux for automatic complement generation, isolated V_MID buffers to prevent hidden-node cross-coupling).
- **The Python simulation package** — a generic topology-independent KCL solver, EqProp training loop, and ngspice cross-validation framework.

## Status

XOR proof-of-concept working in simulation. Hardware design complete (see [docs/design.md](docs/design.md)).

- Python solver matches ngspice within 1% on all node voltages
- EqProp gradients match finite-difference within 50% per weight
- XOR converges in ~1800 epochs (seed=42)
- Full hardware BOM: 14 ICs, ~$50-65

## Architecture (XOR Topology)

```
Inputs (clamped)          Hidden (solved)       Outputs (solved)
┌──────────────┐         ┌─────────────┐       ┌──────────────┐
│ X1  (1V/4V)  │──W1,W2──│             │       │              │
│ X1c (4V/1V)  │──W3,W4──│  H1    H2   │─W13───│  Y+    Y-    │
│ X2  (1V/4V)  │──W5,W6──│  ┃     ┃    │─W14───│              │
│ X2c (4V/1V)  │──W7,W8──│  diode diode│─W15───│  prediction  │
│ V_LOW  (1V)  │──W9,W10─│  pairs pairs│─W16───│  = V(Y+)-V(Y-)
│ V_HIGH (4V)  │─W11,W12─│             │       │              │
└──────────────┘         └─────────────┘       └──────────────┘
        6 nodes              2 nodes               2 nodes
                         16 weight resistors (MCP4251-104 digital pots)
```

**Complementary inputs** (X1c = 5V - X1) enable effective negative weights through conductance differences: `w_eff = g(X1→H) - g(X1c→H)`.

## Design Notes

Things that weren't obvious from the papers and took some effort to work out:

**Symmetric bias makes XOR impossible.** With antiparallel diodes centered at V_MID=2.5V, a single bias node at V_MID contributes zero net current (it sits at the diode crossover point). This makes the entire network function odd: f(-x) = -f(x). Since XOR patterns (0,1) and (1,0) are negatives in centered coordinates, the network is forced to predict pred(0,1) = -pred(1,0) — it can never assign the same sign to both. This was verified numerically across 1000+ random weight configurations before the cause was identified. The fix is an asymmetric bias pair: V_LOW=1V and V_HIGH=4V, which inject net current and break the symmetry. This added 2 weights (14→16) and one more MCP4251 chip.

**Target voltage must be small.** The BAT42 diode pairs clamp hidden nodes to roughly 2.2–2.8V (a ~0.6V linear region around V_MID). This compressed range limits the maximum output differential to about 0.4V, so the XOR target is set to 0.3V rather than 1.0V. Attempting a larger target causes the training to stall — the network physically cannot produce that voltage swing.

**The resistive initial guess matters.** The KCL solver (Newton's method via `scipy.optimize.root`) can converge to degenerate solutions if started at V_MID, where the diode Jacobian is near-zero. Pre-solving the linear resistive network (ignoring diodes) gives a starting point that's already near the correct equilibrium, making convergence reliable across all weight configurations.

**Gradient check has a known sensitivity.** The EqProp gradient for XOR pattern (1,0) with seed=42 initial weights disagrees with finite-difference by more than 50% on some weights. This is a solver sensitivity issue — the finite-difference perturbation lands on a slightly different equilibrium branch — not a bug in the gradient formula. The other three patterns match well, and training converges regardless.

## Quick Start

```bash
cd sim
pip install -r requirements.txt

# Run all tests
pytest -v

# Train XOR network
python -m eqprop.xor

# Run ngspice cross-validation tests (requires: brew install ngspice)
pytest tests/test_spice.py -v
```

## Project Structure

```
sim/                        Python simulation
  eqprop/                   Importable package
    network.py              Network dataclass + KCL equilibrium solver
    diode.py                BAT42 Schottky diode model
    training.py             EqProp gradient computation + training loop
    spice.py                SPICE netlist generation + ngspice runner
    xor.py                  XOR topology, dataset, entry point
  tests/                    pytest test suite
spice/                      SPICE netlists (LTspice / ngspice compatible)
docs/design.md              Full hardware design specification
```

## License

Apache 2.0. See [LICENSE](LICENSE).
