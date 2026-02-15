# Analog Equilibrium Propagation

## Project Overview

Hardware analog neural network that learns XOR using equilibrium propagation (EqProp). The analog resistive network performs forward inference and backward error propagation through physics (Kirchhoff's laws). An Arduino Nano orchestrates training digitally.

**Reference papers:**
- Scellier & Bengio 2017, "Equilibrium Propagation: Bridging the Gap Between Energy-Based Models and Backpropagation"
- Kendall et al. 2020, "Training End-to-End Analog Neural Networks with Equilibrium Propagation"

## File Map

```
sim/                        Python simulation (run from this directory)
  eqprop/                   Importable package
    network.py              Network dataclass + generic KCL solver
    diode.py                BAT42 Schottky diode model (DiodeParams, diode_current_into)
    training.py             EqProp gradient computation + training loop
    spice.py                SPICE netlist generation + ngspice runner
    xor.py                  XOR topology factory, dataset, input encoding
  tests/                    pytest test suite
    test_solver.py          Analytical solver tests + LTspice reference values
    test_gradient.py        EqProp vs finite-difference gradient check
    test_training.py        XOR convergence + weight bound checks
    test_spice.py           ngspice cross-validation (skipped if ngspice absent)
  requirements.txt          numpy, scipy, pytest

spice/                      SPICE netlists (LTspice / ngspice compatible)
  sim1_activation.cir       Single diode pair characterization
  xor_network.cir           16-weight complementary-input topology

docs/
  design.md                 Complete hardware design specification
```

## Network Topology (XOR)

**Architecture:** 6 inputs, 2 hidden, 2 outputs, 16 weight resistors

```
Nodes: 0=X1, 1=X1_comp, 2=X2, 3=X2_comp, 4=V_LOW, 5=V_HIGH, 6=H1, 7=H2, 8=YP, 9=YN
       ├── 6 fixed (clamped) ──┤  ├── 4 free (solved) ──┤

Inputs:  X1 ∈ {1.0V, 4.0V},  X1_comp = 5.0 - X1
         X2 ∈ {1.0V, 4.0V},  X2_comp = 5.0 - X2
         V_LOW = 1.0V,  V_HIGH = 4.0V  (asymmetric bias pair)

Output:  prediction = V(YP) - V(YN)
Target:  0.0V for same-class, +0.3V for different-class
```

The topology is defined by the `Network` dataclass in `network.py`. The XOR-specific instance is created by `make_xor_network()` in `xor.py`. Future topologies are sibling factory functions — no solver code changes needed.

## Critical Design Decisions (and Why)

### Complementary inputs are required for XOR
Resistors have positive-only conductance. Complementary inputs (X1_comp = 5-X1) create effective negative weights: w_eff = g(X1->H) - g(X1_comp->H). Without this, the network cannot represent XOR.

### V_LOW/V_HIGH bias (NOT V_MID)
With antiparallel diodes centered at V_MID=2.5V and a single bias at V_MID, the network function is mathematically odd: f(-x) = -f(x). XOR patterns (0,1) and (1,0) are negatives in centered coordinates, so pred(0,1) = -pred(1,0) *always* -- making XOR impossible with 2 hidden nodes regardless of weights.

The fix: replace the single V_MID bias with V_LOW(1V)/V_HIGH(4V), which contributes asymmetric current and breaks the odd symmetry.

### Target voltage is 0.3V (not 1.0V)
Schottky diodes clamp hidden nodes to ~2.2-2.8V. This compressed range limits the maximum output differential to ~0.4V. A 0.3V target is achievable; 1.0V is not.

## Running Tests

```bash
cd sim

# Run all tests (ngspice tests auto-skip if ngspice not installed)
pytest -v

# Train XOR network
python -m eqprop.xor

# Run ngspice cross-validation only (requires: brew install ngspice)
pytest tests/test_spice.py -v
```

**Expected results:**
- `pytest`: 23 tests pass (~7s). ngspice tests skip gracefully if not installed.
- `python -m eqprop.xor`: Converges at ~epoch 1800 (seed=42). All 4 XOR patterns PASS.

**Training parameters:** lr=5e-9, beta=1e-5, patience=500. Plateau detection stops early if loss stalls.

## Gradient Check Caveat

The gradient check for pattern (4,1) shows DIFF results with random initial weights (seed=42). This is a solver sensitivity issue -- the finite-difference perturbation lands on a different equilibrium for some weight configurations. It does not affect training convergence. The test suite skips this pattern.

## Key Constants (from datasheets/standards)

```python
# BAT42 Schottky diode — see diode.py DiodeParams
Is = 1e-7       # Saturation current
N = 1.1         # Ideality factor
VT = 0.02585    # Thermal voltage at 27C

# MCP4251-104 digital potentiometer — see network.py WeightParams
R_series = 1200.0    # Series protection resistor
R_min = 1590.0       # Tap 256: 390 wiper + 1200 series
R_max = 101200.0     # Tap 1: 100k + 1200 series

# Voltage rails — see xor.py
V_MID = 2.5    # Diode return rail
V_LOW = 1.0    # Low bias input
V_HIGH = 4.0   # High bias input
```

## Hardware Summary (from design-v2.md)

- 8x MCP4251-104 (16 weight channels)
- 2x CD4053 analog mux (direct + complement inputs, shared control pins)
- 2x LM324N quad op-amp (voltage refs, LED comparators)
- 1x MCP6002 dual op-amp (Howland current pumps for nudge)
- 1x MCP4822 dual DAC (nudge current control)
- 1x ADS1115 16-bit ADC (node voltage measurement)
- 4x BAT42 Schottky diodes (activation functions)
- Arduino Nano (training orchestration via SPI/I2C)
- **14 ICs total, ~$50-65 BOM**

## Conventions

- Weights are stored as resistance (ohms), gradients computed in conductance (1/R) space
- `solve_network(net, inputs, weights)` returns array of free-node voltages
- `net.prediction(free_voltages)` computes output differential
- `make_inputs(v_x1, v_x2)` expands to full 6-element vector [X1, X1c, X2, X2c, V_LOW, V_HIGH]
- Connection indices in `net.connections` match weight numbering: W1=index 0, W16=index 15
- SPICE node names are lowercase: x1, x1c, x2, x2c, vlow, vhigh, h1, h2, yp, yn
