# Analog equilibrium propagation — XOR prototype B.1

A two-hidden-node analog resistive network for learning XOR through equilibrium propagation. The circuit settles physically; a classic 5 V Arduino Nano will measure equilibria and update sixteen programmable resistances. **The PCB is routed and checked; Nano firmware and physical validation are not yet implemented/completed.**

Start every new session with [project state and next steps](docs/project-state.md). It records what exists, what remains, and where to find the design, fabrication, programming and debugging instructions.

## Working files

- [Native KiCad project](cad/eqprop-xor/eqprop-xor.kicad_pro), including its child sheets and local libraries.
- [Design rationale and datasheets](docs/design.md), [component/pin tables](docs/kicad/00-overview.md), [preferred-parts BOM](docs/bom-pcbway.csv).
- [PCBWay fabrication and assembly](docs/fabrication.md).
- [Nano firmware contract](docs/firmware.md), [bench bring-up](docs/bring-up.md), [demo operation](docs/operation.md).
- [Engineering review](docs/ee-review.md), [validation evidence](docs/validation/).

## Simulation and release checks

From the repository root, using Python 3 and a virtual environment:

```sh
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r sim/requirements.txt
PYTHONPATH=sim python -m pytest sim/tests -q
PYTHONPATH=sim python -m eqprop.xor
python tools/generate_bom.py
python tools/export_manufacturing.py
```

Install ngspice for the SPICE tests; those tests skip when it is absent, so skipped tests do not constitute a complete release check. KiCad 9's `kicad-cli` is required for manufacturing export. The script discovers PATH or the standard macOS install; `--kicad-cli` can specify another executable. Generated fabrication files go in ignored `build/manufacturing/`. Save the exact approved release with the PCBWay order records when an order is placed.

The regression suite checks KCL, gradients, training, quantization, SPICE behavior and BOM consistency. These are retained because later hardware/firmware changes need them. Nominal DC models do not prove stability, noise, component spread or online finite-tap learning.

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

## License

Apache 2.0. See [LICENSE](LICENSE).
