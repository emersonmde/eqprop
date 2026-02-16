# Analog Equilibrium Propagation XOR Network — Design v2 (Final)

## Overview

This document specifies a hybrid analog/digital neural network that learns XOR using **equilibrium propagation (EqProp)**. The analog circuit performs forward inference and backward error propagation through physics (Kirchhoff's laws, resistive settling, diode nonlinearities). An Arduino Nano orchestrates training by measuring node voltages, computing gradients, and updating digital potentiometer weights via SPI.

**Reference paper:** Kendall et al. 2020, *"Training End-to-End Analog Neural Networks with Equilibrium Propagation"*
- XOR architecture: Figure 3, Appendix D.2
- Gradient formula: Theorem 1
- Nonlinear elements: Theorem 2

**Architecture:** 6-2-2 MLP (6 inputs → 2 hidden → 2 outputs, differential encoding)
- 4 signal inputs: X1, X1_comp, X2, X2_comp (complementary pairs)
- 2 bias inputs: V_LOW (≈1.0V), V_HIGH (≈4.0V)
- 2 hidden neurons: H1, H2
- 2 output nodes: Y+, Y− (prediction = Y+ − Y−)
- 16 total weights (12 first-layer, 4 second-layer)

**Why complementary inputs:** Positive-only conductances (resistors) cannot produce negative effective weights. Complementary inputs X1_comp = 5−X1 enable effective negative weights via conductance differences: w_eff = g(X1→H) − g(X1_comp→H). This is required for XOR.

**Why V_LOW/V_HIGH bias (not V_MID):** With antiparallel diodes centered at V_MID=2.5V, a single bias at V_MID contributes zero net current, making the network function odd: f(−x) = −f(x). Since XOR patterns (0,1) and (1,0) are negatives in centered coordinates, pred(0,1) = −pred(1,0) always — making XOR mathematically impossible with 2 hidden nodes. Asymmetric bias inputs (V_LOW≈1.0V, V_HIGH≈4.0V) break this symmetry.

---

## 1. Supply and Voltage References

### Board Power Supply

**USB-C connector** provides the primary 5V rail for the entire board. Two 5.1kΩ resistors on CC1/CC2 identify the board as a USB-C sink and request 5V from any standard USB-C power source (phone charger, laptop port, etc.). 100µF bulk capacitor on the 5V rail after the connector.

The Arduino Nano plugs into pin header sockets on the PCB and receives 5V from the board through its 5V header pin (bypassing the Nano's onboard regulator). During training, a second USB cable connects to the Arduino's own USB port for serial monitoring and firmware upload — both 5V sources coexist safely because the Nano's USB 5V passes through an onboard Schottky diode, so the board's slightly-higher direct 5V dominates.

A **green power LED** (3mm, through 1kΩ to GND from the 5V rail) indicates the board is powered.

**Operating modes:**
- **Training:** Board USB-C provides power. Arduino USB provides serial. Both connected.
- **Inference:** Board USB-C provides power only. Arduino unplugged. Toggle switches + output LEDs.

### Reference Voltage Generation

**V_MID = 2.5V master divider:** 10kΩ / 10kΩ 1% resistor divider from 5V to GND. This single divider feeds four independent op-amp voltage follower buffers:

| Rail | Purpose | Buffer | Decoupling |
|------|---------|--------|------------|
| V_MID_H1 | Return rail for H1 diode pair | LM324 #2, section A | 10µF electrolytic + 100nF ceramic |
| V_MID_H2 | Return rail for H2 diode pair | LM324 #2, section B | 10µF electrolytic + 100nF ceramic |
| V_MID_PUMP | Reference for both Howland pumps | LM324 #2, section C | 10µF electrolytic + 100nF ceramic |

MCP6004 #1, section C is **spare** (previously used for V_BIAS buffer — no longer needed since bias is provided by V_LOW/V_HIGH directly).

The three independent V_MID buffers eliminate cross-coupling between hidden neurons and isolate pump current demands from activation function references. Without this, current drawn by H1's diodes through a shared V_MID rail shifts the operating point of H2's diodes — a parasitic interaction that corrupts gradient measurements (the shift is the same order of magnitude as the gradient signal).

**V_LOW ≈ 1.0V:** 33kΩ / 8.2kΩ 1% divider from 5V (actual: 0.995V), buffered by MCP6004 #1 section A. 100nF decoupling.

**V_HIGH ≈ 4.0V:** 8.2kΩ / 33kΩ 1% divider from 5V (actual: 4.005V), buffered by MCP6004 #1 section B. 100nF decoupling.

**Why MCP6004 (not LM324) for V_LOW/V_HIGH buffers:** The LM324's output can only reach ~3.5V on a 5V supply (NPN common-emitter high-side output needs ~1.5V headroom), and its input common-mode range is limited to VCC−1.5V = 3.5V. The ≈4.0V V_HIGH_RAW voltage exceeds both limits, causing the buffer to saturate or phase-invert. The MCP6004 is a pin-compatible DIP-14 quad op-amp with rail-to-rail I/O (output swings to within 25mV of either rail, input common-mode includes both rails). It outputs ≈4.0V cleanly on a 5V supply.

### XOR Input Encoding

| Pattern | X1 | X1_comp | X2 | X2_comp | V_LOW | V_HIGH | Target (Y+ − Y−) |
|---------|-------|---------|-------|---------|--------|--------|-------------------|
| 0,0 | ≈1.0V | ≈4.0V | ≈1.0V | ≈4.0V | ≈1.0V | ≈4.0V | 0V |
| 0,1 | ≈1.0V | ≈4.0V | ≈4.0V | ≈1.0V | ≈1.0V | ≈4.0V | +0.3V |
| 1,0 | ≈4.0V | ≈1.0V | ≈1.0V | ≈4.0V | ≈1.0V | ≈4.0V | +0.3V |
| 1,1 | ≈4.0V | ≈1.0V | ≈4.0V | ≈1.0V | ≈1.0V | ≈4.0V | 0V |

Target of ±0.3V (not ±1.0V) is realistic given diode clamping limits hidden nodes to ~2.2–2.8V range, yielding max ~0.4V output differential. The Python simulation (`python -m eqprop.xor` from the `sim/` directory) confirms convergence with 0.3V targets.

---

## 2. Weight Elements

### Component: MCP4251-104 (100kΩ dual digital potentiometer)

- 8-bit resolution, 257 tap positions (0–256)
- SPI interface, DIP-14 package
- ±20% end-to-end resistance tolerance (compensated by measured voltages)
- Wiper current limit: ±2.5mA

### Series Protection Resistor

Each pot channel has a **1.21kΩ 1% metal film resistor** in series (1.21kΩ is the nearest E96 value to 1.2kΩ, available in 1% metal film).

**Effective resistance range:**
- Minimum (tap 256, wiper at terminal A): ~390Ω wiper + 1,210Ω series = **1,600Ω**
- Maximum (tap 1, wiper near terminal B): ~100kΩ + 1,210Ω = **101,210Ω**
- Conductance range: 9.9µS to 625µS — **63:1 ratio**

**Current limit verification:** Worst-case 3.0V drop / 1,600Ω = 1.88mA (within 2.5mA limit, 25% margin).

**Firmware enforces minimum tap = 1.** Tap 0 gives only 6% current margin.

**SHDN and WP pins:** The MCP4251 DIP-14 has active-low SHDN (pin 12, hardware shutdown) and WP (pin 11, write protect) pins. Both must be tied to VDD for normal operation. If left floating, the device may enter shutdown (pots become open circuits) or block SPI writes to wiper registers.

### Weight Topology and Chip Assignment

**First layer (input → hidden), 12 weights:**

| Weight | Connection | Chip | Channel |
|--------|------------|------|---------|
| W1 | X1 → H1 | MCP4251 #1 | Pot A |
| W2 | X1 → H2 | MCP4251 #1 | Pot B |
| W3 | X1_comp → H1 | MCP4251 #2 | Pot A |
| W4 | X1_comp → H2 | MCP4251 #2 | Pot B |
| W5 | X2 → H1 | MCP4251 #3 | Pot A |
| W6 | X2 → H2 | MCP4251 #3 | Pot B |
| W7 | X2_comp → H1 | MCP4251 #4 | Pot A |
| W8 | X2_comp → H2 | MCP4251 #4 | Pot B |
| W9 | V_LOW → H1 | MCP4251 #5 | Pot A |
| W10 | V_LOW → H2 | MCP4251 #5 | Pot B |
| W11 | V_HIGH → H1 | MCP4251 #6 | Pot A |
| W12 | V_HIGH → H2 | MCP4251 #6 | Pot B |

**Second layer (hidden → output), 4 weights:**

| Weight | Connection | Chip | Channel |
|--------|------------|------|---------|
| W13 | H1 → Y+ | MCP4251 #7 | Pot A |
| W14 | H1 → Y− | MCP4251 #7 | Pot B |
| W15 | H2 → Y+ | MCP4251 #8 | Pot A |
| W16 | H2 → Y− | MCP4251 #8 | Pot B |

### Why Digital Pots (Not MOSFETs or Capacitors)

**MOSFETs rejected:** 2N7000 in triode region requires V_DS << 2(V_GS − V_th). With ±2V input swings the MOSFET transitions between triode and saturation, breaking the resistive model. Critically, the drain-source I-V characteristic is directional — this violates EqProp's requirement that W_ij = W_ji (symmetric connections). During the nudge phase, backward error propagation through a directional impedance is distorted.

**Capacitor storage rejected:** Fundamental tension between stability and updatability. Large caps (1µF) are stable but gradient signals (~0.2µV updates) require impractical 100MΩ scaling resistors. Small caps (10nF) update easily but drift 180mV/min. No sweet spot exists.

**Digital pots work because:** They are perfectly bidirectional, linear, symmetric resistors. They satisfy all EqProp mathematical requirements. The analog computation (forward pass, nudge settling) uses pure physics through the resistive network. Only the weight update step is digital — identical to the paper's approach (Python between SPICE simulation runs).

---

## 3. Activation Functions

### Component: BAT42 Schottky Diode (DO-35 through-hole)

Two BAT42 diodes per hidden neuron, connected in **antiparallel** between the hidden node and its dedicated V_MID rail.

- **H1:** BAT42 pair between node H1 and V_MID_H1
- **H2:** BAT42 pair between node H2 and V_MID_H2

### Behavior

V_f ≈ 0.3V (vs 0.6V for 1N4148). Creates a **0.6V linear region** (approximately 2.2V to 2.8V):
- Between 2.2V and 2.8V: neither diode conducts significantly; node voltage is determined by the resistive network (weighted average of inputs)
- Above 2.8V: forward-biased Schottky shunts current to V_MID, clamping voltage
- Below 2.2V: reverse Schottky conducts, clamping voltage
- Effective saturation rails: ~2.0V and ~3.0V (accounting for soft turn-on)

The narrower linear region (vs 1.2V for 1N4148) provides stronger nonlinearity — hidden neurons saturate more aggressively, which is critical for XOR's sharp decision boundaries.

### EqProp Validity

Each diode pair is a two-terminal element with a continuous, monotonic I-V characteristic. Its pseudo-power (integral of I-V curve) is well-defined. The antiparallel arrangement ensures bidirectional current flow, satisfying EqProp's symmetry requirements per Theorem 2.

### Fallback

If Schottky diodes prove too aggressive (hidden nodes always saturated, no useful gradient information), substitute 1N4148 diodes (1.2V linear region, DO-35 package). Optionally add 100–500Ω series resistors with the Schottky diodes to soften the clamping.

---

## 4. Nudge Current Injection

### Improved Howland Current Pump

Two pumps (one per output node) convert a control voltage from the DAC to a bidirectional output current with high output impedance.

**Op-amp: MCP6002** (dual rail-to-rail I/O op-amp, DIP-8, single 5V supply)
- Rail-to-rail output eliminates compliance voltage concerns (output swings to within 25mV of each rail)
- Input offset: ~4.5mV (produces ~4.5nA offset current — present in both phases, mostly cancels)
- Input bias current: ~1pA (negligible)
- Pump A (Y+ node): MCP6002 section A
- Pump B (Y− node): MCP6002 section B

### Howland Pump Resistor Network

Standard improved Howland topology with 5 resistors per pump:

- Four feedback resistors: **10kΩ 0.1% metal film** (matched for high output impedance)
- Current-setting resistor R_set: **1MΩ 0.1% metal film**

Output current formula:
```
I_out = (V_control − V_MID_PUMP) / R_set
I_out = (V_control − 2.5V) / 1MΩ
```

### DAC: MCP4822 (Dual 12-bit SPI DAC)

- Internal 2.048V reference with 2× gain bit → output range 0V to 4.096V
- Channel A drives Pump A (Y+ node)
- Channel B drives Pump B (Y− node)
- At V_control = 2.5V (DAC code ≈ 2500): I_out = 0 (free phase)
- Maximum offset ±1.5V → maximum current ±1.5µA

### β Calibration

With output node impedance of ~10–50kΩ:
- At ±1.5µA: perturbation = 15–75mV (0.5–2% of node swing) — good for small-β approximation
- Start with ±50nA (±100 DAC counts offset from midpoint) and increase if gradients are too small
- β_scale maps directly to DAC offset from midpoint

### Alternating β Sign

On even training steps, DAC_Y+ gets positive offset and DAC_Y- gets negative. On odd steps, reversed. This reduces gradient estimation bias per the paper's recommendation.

### Power-On Behavior

MCP4822 powers up with outputs at 0V → injects -2.5µA per pump. Small and transient. Arduino setup() sets DAC to midpoint within milliseconds. No protection circuit needed.

### Output Impedance

With 0.1% resistors, theoretical Z_out is extremely high. Practical Z_out on breadboard with MCP6002 is 10–100MΩ. At network impedance of 10–50kΩ, this is >200:1 — pump appears as ideal current source to the network.

---

## 5. Voltage Measurement

### Primary ADC: ADS1115 (16-bit, 4-channel, I2C)

**PGA setting: ±6.144V** (NOT ±4.096V — the tighter range clips voltages near V_HIGH ≈ 4.0V and provides no headroom for transients).

At ±6.144V: LSB = 187.5µV. Full 0–5V range covered with headroom.

**Channel assignment:**

| Channel | Node | Purpose |
|---------|------|---------|
| AIN0 | H1 | Hidden node 1 voltage |
| AIN1 | H2 | Hidden node 2 voltage |
| AIN2 | Y+ | Output node positive |
| AIN3 | Y− | Output node negative |

**Measurement protocol per phase:**
1. Configure for AIN0, 128 SPS, single-shot mode. Start conversion.
2. Wait for DRDY (~8ms at 128 SPS).
3. Read 16-bit result → V_H1.
4. Repeat for AIN1 (V_H2), AIN2 (V_Y+), AIN3 (V_Y−).
5. Total per phase: ~32ms.

**Noise analysis:** At 128 SPS, internal noise is ~8µV RMS. Expected gradient signal produces ~26mV hidden node voltage changes. SNR = 26mV / 8µV = 3,250. **No averaging needed** for single-shot measurements.

**Input impedance:** 6.4MΩ sampling impedance causes 0.16% loading on ~10kΩ network nodes. Negligible and identical in both phases (cancels in gradient computation).

**PCB design notes:** Use the bare ADS1115 chip (MSOP-10 package), not a breakout module. Required additions: 4.7kΩ pull-up resistors on SDA and SCL to VDD. ADDR pin tied to GND (I2C address 0x48). 100nF decoupling capacitor close to VDD/GND pins.

### Secondary ADC: Arduino Built-in 10-bit ADC

Measures input node voltages (which don't change between free/nudge phases):
- A0 → X1 voltage
- A1 → X2 voltage

Complement voltages (X1_comp, X2_comp) are computed in firmware as 5.0 − X1 and 5.0 − X2. V_LOW and V_HIGH are fixed reference voltages measured once at startup.

Resolution ~5mV — adequate for input nodes where voltage drops across weights are 1–3V.

---

## 6. Input Selection

### Component: 2× CD4053 (Triple 2:1 Analog Mux, DIP-16)

Both CD4053 chips share the same control pins (D2, D3). The second chip has V_LOW and V_HIGH **swapped** on its analog inputs, automatically generating complement voltages with no extra pins or logic.

**CD4053 #1 — Direct inputs:**
- Channel A: Selects X1 between V_LOW (≈1.0V) and V_HIGH (≈4.0V). Control: Arduino D2.
- Channel B: Selects X2 between V_LOW and V_HIGH. Control: Arduino D3.
- Channel C: Unused. Tie control pin low, tie common to ground.

**CD4053 #2 — Complementary inputs (V_LOW/V_HIGH swapped):**
- Channel A: Selects X1_comp between V_HIGH (≈4.0V) and V_LOW (≈1.0V). Control: Arduino D2.
- Channel B: Selects X2_comp between V_HIGH and V_LOW. Control: Arduino D3.
- Channel C: Unused. Tie control pin low, tie common to ground.

Both powered from 5V, V_EE tied to GND. On-resistance: ~100Ω typical.

When D2 goes HIGH, CD4053 #1 routes V_HIGH → X1 (4.0V), while CD4053 #2 routes V_LOW → X1_comp (1.0V). Complements are always correct, generated by physics, no firmware computation needed during analog settling.

**Source impedance at input nodes:** Buffer output (~1Ω) + CD4053 R_on (~100Ω) = ~101Ω. This is 6% of minimum weight resistance (1,600Ω). The Arduino's built-in ADC measures actual voltage at the network node, capturing any sag.

### Inference Mode: Toggle Switches

Two SPDT toggle switches allow manual input selection when the Arduino is unplugged. Each switch is wired to the shared CD4053 **control pins** (not the analog input nodes) through a **10kΩ series isolation resistor**:

```
Arduino D2 ──────────┬──── CD4053 #1 & #2 Control A (X1/X1_comp select)
                     │
X1 Toggle ─── 10kΩ ──┘     Throws: VDD (5V) = HIGH = X1 gets V_HIGH, X1_comp gets V_LOW
                                    GND      = LOW  = X1 gets V_LOW,  X1_comp gets V_HIGH

Arduino D3 ──────────┬──── CD4053 #1 & #2 Control B (X2/X2_comp select)
                     │
X2 Toggle ─── 10kΩ ──┘     Throws: VDD (5V) = HIGH = X2 gets V_HIGH, X2_comp gets V_LOW
                                    GND      = LOW  = X2 gets V_LOW,  X2_comp gets V_HIGH
```

**During training:** Arduino GPIO drives the control pin directly (~25Ω output impedance), overpowering the switch's 10kΩ path. Maximum contention current is 5V / 10kΩ = 0.5mA into the GPIO — well within the 40mA limit. Switch position is irrelevant.

**During inference:** Arduino removed from its header socket — GPIO pins physically disconnected. The switch drives through 10kΩ into the CD4053 CMOS input (effectively infinite impedance). Clean logic levels, no floating pins, no contention.

**No mode switch needed.** The transition from training to inference requires only unplugging the Arduino.

---

## 7. Output Indication

Two spare op-amp sections used as comparators for visual output, wired **active-low**. The LM324 (#2) can only reach ~3.5V output on 5V supply, too low to drive LEDs brightly. Active-low sinking (to ~0.2V at up to 20mA) works for both ICs. The MCP6004 (#1) could drive LEDs either way, but active-low is used for consistency.

**Comparator A (MCP6004 #1, section D):**
- Non-inverting input = Y−
- Inverting input = Y+
- Output LOW when Y+ > Y− → sinks current through **green LED**
- LED wired: 5V → 470Ω → green LED anode → LED cathode → comparator output
- Green = "XOR output is 1"

**Comparator B (LM324 #2, section D):**
- Non-inverting input = Y+
- Inverting input = Y−
- Output LOW when Y− > Y+ → sinks current through **red LED**
- LED wired: 5V → 470Ω → red LED anode → LED cathode → comparator output
- Red = "XOR output is 0"

**LED current:** (5V − ~2V LED drop − 0.2V output low) / 470Ω ≈ **6mA** — bright and clearly visible. When the comparator output is HIGH (~3.5V for LM324 #2, ~4.9V for MCP6004 #1), the LED is off (insufficient forward voltage across the LED for LM324; for MCP6004, only ~0.1V remains across LED + resistor).

Works after training with no Arduino — pure analog readout. Comparators draw negligible current from output nodes (>1MΩ input impedance for LM324, >10TΩ for MCP6004).

---

## 8. Op-Amp Allocation (Complete)

11 of 12 sections allocated — one spare (MCP6004 #1 section C).

| IC | Section A | Section B | Section C | Section D |
|----|-----------|-----------|-----------|-----------|
| MCP6004 #1 | V_LOW buffer | V_HIGH buffer | **Spare** | LED comparator (Y+ > Y−) |
| LM324 #2 | V_MID_H1 buffer | V_MID_H2 buffer | V_MID_PUMP buffer | LED comparator (Y− > Y+) |
| MCP6002 | Howland pump A (Y+) | Howland pump B (Y−) | — | — |

MCP6004 #1 section C was previously the V_BIAS buffer — freed by replacing the single V_MID bias with V_LOW/V_HIGH pair (which already have their own buffers in sections A and B). MCP6004 is used instead of LM324 for #1 because the V_HIGH buffer (4.0V) exceeds the LM324's output swing and input common-mode range on a 5V supply.

---

## 9. SPI Bus

Nine devices share the SPI bus. All use Mode 0,0 (CPOL=0, CPHA=0). Clock: 1MHz.

| Device | CS Pin | Function |
|--------|--------|----------|
| MCP4251 #1 (W1, W2) | D4 | Weight pots: X1 → H1, H2 |
| MCP4251 #2 (W3, W4) | D5 | Weight pots: X1_comp → H1, H2 |
| MCP4251 #3 (W5, W6) | D6 | Weight pots: X2 → H1, H2 |
| MCP4251 #4 (W7, W8) | D7 | Weight pots: X2_comp → H1, H2 |
| MCP4251 #5 (W9, W10) | D8 | Weight pots: V_LOW → H1, H2 |
| MCP4251 #6 (W11, W12) | D10 | Weight pots: V_HIGH → H1, H2 |
| MCP4251 #7 (W13, W14) | A2 | Weight pots: H1 → Y+, Y− |
| MCP4251 #8 (W15, W16) | A3 | Weight pots: H2 → Y+, Y− |
| MCP4822 (nudge DAC) | D9 | Current pump control |

**10kΩ pull-up resistors to VCC on each CS line** ensure all devices are deselected during Arduino reset/boot, preventing spurious writes.

MCP4251 SDO goes high-impedance when CS is high. MCP4822 is write-only. No bus contention.

---

## 10. Arduino Nano Pin Assignment

| Pin | Function | Device |
|-----|----------|--------|
| D2 | CD4053 control A | X1/X1_comp input select (both muxes) |
| D3 | CD4053 control B | X2/X2_comp input select (both muxes) |
| D4 | SPI CS | MCP4251 #1 (W1, W2) |
| D5 | SPI CS | MCP4251 #2 (W3, W4) |
| D6 | SPI CS | MCP4251 #3 (W5, W6) |
| D7 | SPI CS | MCP4251 #4 (W7, W8) |
| D8 | SPI CS | MCP4251 #5 (W9, W10) |
| D9 | SPI CS | MCP4822 (nudge DAC) |
| D10 | SPI CS | MCP4251 #6 (W11, W12) |
| D11 | SPI MOSI | Shared bus |
| D12 | SPI MISO | Shared bus |
| D13 | SPI SCK | Shared bus |
| A0 | Analog input | X1 voltage measurement |
| A1 | Analog input | X2 voltage measurement |
| A2 | SPI CS | MCP4251 #7 (W13, W14) |
| A3 | SPI CS | MCP4251 #8 (W15, W16) |
| A4 | I2C SDA | ADS1115 |
| A5 | I2C SCL | ADS1115 |

**Used: 17 pins. Spare: D0, D1 (serial TX/RX), A6, A7.**

D10 is now used as an actual CS pin (still configured as OUTPUT, satisfying SPI hardware requirement). A2 and A3 repurposed from analog input to digital output for CS — A2 was formerly X_bias measurement (no longer needed since bias is fixed V_LOW/V_HIGH).

---

## 11. Network Topology (Circuit Description)

This section describes the complete analog network for LTspice schematic entry.

### Node List

| Node Name | Type | Voltage Range | Connected To |
|-----------|------|---------------|--------------|
| X1 | Input (driven) | ≈1.0V or ≈4.0V | W1, W2 (through series R) |
| X1_comp | Input (driven) | ≈4.0V or ≈1.0V | W3, W4 (through series R) |
| X2 | Input (driven) | ≈1.0V or ≈4.0V | W5, W6 (through series R) |
| X2_comp | Input (driven) | ≈4.0V or ≈1.0V | W7, W8 (through series R) |
| V_LOW | Bias (fixed) | ≈1.0V | W9, W10 (through series R) |
| V_HIGH | Bias (fixed) | ≈4.0V | W11, W12 (through series R) |
| H1 | Hidden (floating) | ~2.0–3.0V | W1,W3,W5,W7,W9,W11 (input side) + W13,W14 (output side) + D1a/D1b to V_MID_H1 |
| H2 | Hidden (floating) | ~2.0–3.0V | W2,W4,W6,W8,W10,W12 (input side) + W15,W16 (output side) + D2a/D2b to V_MID_H2 |
| Y+ | Output (floating) | ~2.0–3.5V | W13, W15 + Howland pump A output |
| Y− | Output (floating) | ~2.0–3.5V | W14, W16 + Howland pump B output |

### Connection List (Each Weight)

Each weight is: **input_node → 1.21kΩ series R → MCP4251 pot (variable R) → output_node**

For LTspice simulation, replace each MCP4251 channel with a simple variable resistor. The series 1.21kΩ resistor is always present.

```
X1 ──── 1.21kΩ ── [R_W1:  1.6k to 101.21k] ─── H1
X1 ──── 1.21kΩ ── [R_W2:  1.6k to 101.21k] ─── H2
X1c ─── 1.21kΩ ── [R_W3:  1.6k to 101.21k] ─── H1
X1c ─── 1.21kΩ ── [R_W4:  1.6k to 101.21k] ─── H2
X2 ──── 1.21kΩ ── [R_W5:  1.6k to 101.21k] ─── H1
X2 ──── 1.21kΩ ── [R_W6:  1.6k to 101.21k] ─── H2
X2c ─── 1.21kΩ ── [R_W7:  1.6k to 101.21k] ─── H1
X2c ─── 1.21kΩ ── [R_W8:  1.6k to 101.21k] ─── H2
V_LOW ─ 1.21kΩ ── [R_W9:  1.6k to 101.21k] ─── H1
V_LOW ─ 1.21kΩ ── [R_W10: 1.6k to 101.21k] ─── H2
V_HI ── 1.21kΩ ── [R_W11: 1.6k to 101.21k] ─── H1
V_HI ── 1.21kΩ ── [R_W12: 1.6k to 101.21k] ─── H2
H1 ──── 1.21kΩ ── [R_W13: 1.6k to 101.21k] ─── Y+
H1 ──── 1.21kΩ ── [R_W14: 1.6k to 101.21k] ─── Y−
H2 ──── 1.21kΩ ── [R_W15: 1.6k to 101.21k] ─── Y+
H2 ──── 1.21kΩ ── [R_W16: 1.6k to 101.21k] ─── Y−
```

### Diode Connections

```
H1 ── anode  ── D1a (BAT42) ── cathode ── V_MID_H1
H1 ── cathode ── D1b (BAT42) ── anode   ── V_MID_H1

H2 ── anode  ── D2a (BAT42) ── cathode ── V_MID_H2
H2 ── cathode ── D2b (BAT42) ── anode   ── V_MID_H2
```

### Howland Pump Connections

Each pump output connects to one output node. The pump reference is V_MID_PUMP (2.5V). The control voltage comes from the MCP4822 DAC.

For LTspice simulation, model each pump as an **ideal current-controlled current source** (behavioral source): `I_pump = (V_control - 2.5) / 1e6` where V_control is a parameter that changes between free and nudge phases.

---

## 12. Training Procedure (Firmware Pseudocode)

```
CONSTANTS:
  R_SET = 1e6          // Howland R_set (1MΩ)
  LEARNING_RATE = 0.01 // α — tune empirically
  BETA = 50e-9         // Start with 50nA/V, increase if gradients too small
  MIN_TAP = 1
  MAX_TAP = 256
  DAC_MIDPOINT = 2500  // DAC code for 2.5V output
  XOR_TARGETS = [0.0, 0.3, 0.3, 0.0]  // patterns 00, 01, 10, 11
  V_LOW_NOM = 0.995    // Nominal V_LOW from 33k/8.2k divider (measured at startup)
  V_HIGH_NOM = 4.005   // Nominal V_HIGH from 8.2k/33k divider (measured at startup)

setup():
  Initialize SPI (Mode 0, 1MHz), I2C, Serial
  Set MCP4822 both channels to DAC_MIDPOINT (zero nudge)
  For each of 16 pots: set tap to random(MIN_TAP, MAX_TAP)
  Configure D10, A2, A3 as OUTPUT (CS pins)

loop():
  pattern = step_count % 4
  target = XOR_TARGETS[pattern]

  // Set inputs via CD4053 (both chips share same control pins)
  // CD4053 #1 gives X1/X2, CD4053 #2 gives X1_comp/X2_comp automatically
  digitalWrite(D2, pattern & 0x01)  // X1 (and X1_comp via swapped mux)
  digitalWrite(D3, pattern & 0x02)  // X2 (and X2_comp via swapped mux)
  delay(5)  // 5ms settling

  // === FREE PHASE ===
  MCP4822_write(CHAN_A, DAC_MIDPOINT)  // zero current
  MCP4822_write(CHAN_B, DAC_MIDPOINT)
  delay(2)

  // Measure input voltages (Arduino 10-bit ADC)
  V_X1  = analogRead(A0) * 5.0 / 1024
  V_X2  = analogRead(A1) * 5.0 / 1024
  V_X1C = 5.0 - V_X1   // complement (also verified by CD4053 #2)
  V_X2C = 5.0 - V_X2

  // Measure floating node voltages (ADS1115 16-bit)
  V_H1_free = ADS1115_read(AIN0)
  V_H2_free = ADS1115_read(AIN1)
  V_YP_free = ADS1115_read(AIN2)
  V_YN_free = ADS1115_read(AIN3)

  // Compute error
  prediction = V_YP_free - V_YN_free
  error = target - prediction
  loss = 0.5 * error * error

  // === NUDGE PHASE ===
  // Compute nudge currents
  I_pos = BETA * (target + V_YN_free - V_YP_free)
  I_neg = -I_pos

  // Alternating beta sign (bias reduction)
  if (step_count % 2 == 1):
    I_pos = -I_pos
    I_neg = -I_neg

  // Convert to DAC codes: V_dac = I * R_SET + 2.5
  V_dac_pos = I_pos * R_SET + 2.5
  V_dac_neg = I_neg * R_SET + 2.5
  code_pos = clamp(round(V_dac_pos * 4096 / 4.096), 0, 4095)
  code_neg = clamp(round(V_dac_neg * 4096 / 4.096), 0, 4095)
  MCP4822_write(CHAN_A, code_pos)
  MCP4822_write(CHAN_B, code_neg)
  delay(5)  // settling

  // Measure nudged floating node voltages
  V_H1_nudge = ADS1115_read(AIN0)
  V_H2_nudge = ADS1115_read(AIN1)
  V_YP_nudge = ADS1115_read(AIN2)
  V_YN_nudge = ADS1115_read(AIN3)

  // Turn off nudge
  MCP4822_write(CHAN_A, DAC_MIDPOINT)
  MCP4822_write(CHAN_B, DAC_MIDPOINT)

  // === WEIGHT UPDATE ===
  // Build voltage arrays (inputs same in both phases)
  // Node order: X1, X1c, X2, X2c, V_LOW, V_HIGH, H1, H2, YP, YN
  V_free[10]  = {V_X1, V_X1C, V_X2, V_X2C, V_LOW_NOM, V_HIGH_NOM,
                 V_H1_free, V_H2_free, V_YP_free, V_YN_free}
  V_nudge[10] = {V_X1, V_X1C, V_X2, V_X2C, V_LOW_NOM, V_HIGH_NOM,
                 V_H1_nudge, V_H2_nudge, V_YP_nudge, V_YN_nudge}

  for each weight w in weights[0..15]:
    i = w.node_i_index  // index into V_free/V_nudge
    j = w.node_j_index

    dV_free  = V_free[i]  - V_free[j]
    dV_nudge = V_nudge[i] - V_nudge[j]

    // Gradient: ∂L/∂g = (ΔV_nudge² − ΔV_free²) / 2β
    gradient = (dV_nudge*dV_nudge - dV_free*dV_free) / (2 * BETA)

    // If beta was negated this step, negate gradient
    if (step_count % 2 == 1):
      gradient = -gradient

    // Update conductance
    R_current = tap_to_resistance(w.current_tap)
    G_current = 1.0 / R_current
    G_new = G_current - LEARNING_RATE * gradient

    // Prevent negative/zero conductance
    G_new = max(G_new, 1.0 / 101210.0)  // max resistance
    G_new = min(G_new, 1.0 / 1600.0)    // min resistance

    // Convert to tap
    R_new = 1.0 / G_new
    R_pot = R_new - 1210.0  // subtract series resistor
    tap_new = round((100000.0 - R_pot) * 256.0 / 100000.0)
    tap_new = clamp(tap_new, MIN_TAP, MAX_TAP)

    MCP4251_write(w.chip, w.channel, tap_new)
    w.current_tap = tap_new

  // Log
  Serial.printf("step=%d loss=%.6f pred=%.4f target=%.1f\n",
                step_count, loss, prediction, target)
  step_count++
```

### Timing

| Phase | Duration | Notes |
|-------|----------|-------|
| Input settling | 5ms | Conservative for breadboard RC |
| Free phase ADC | 32ms | 4 channels × 8ms each at 128 SPS |
| Nudge settling | 5ms | Conservative |
| Nudge phase ADC | 32ms | 4 channels × 8ms each |
| Computation + SPI | ~5ms | Gradient math + 16 pot writes |
| Serial logging | ~1ms | One line at 115200 baud |
| **Total per sample** | **~78ms** | |
| **Per epoch (4 samples)** | **~312ms** | |
| **5000 epochs** | **~26 minutes** | |

---

## 13. Gradient Signal Analysis

### Expected Magnitudes

Assumptions: weights average 20kΩ, hidden node impedance ~7kΩ (3 parallel weight paths), output node impedance ~10kΩ (2 parallel weight paths).

**Output nodes:** Nudge current 50nA × 10kΩ = 0.5mV perturbation. Small but measurable at 187.5µV LSB.

**Hidden nodes:** Output perturbation attenuates through second-layer weight divider. At 0.5mV output perturbation: ΔV_hidden ≈ 0.5mV × 7kΩ / (20kΩ + 7kΩ) ≈ 0.13mV.

With larger β (say 1µA/V effective nudge), perturbations scale up 20×: output ~10mV, hidden ~2.6mV. At 187.5µV LSB, hidden node changes of 2.6mV = 14 LSBs — measurable but benefits from 4× averaging.

With β producing 10µA/V: output ~100mV, hidden ~26mV = 139 LSBs. Very comfortable.

**The firmware should log raw gradient values** and the operator should tune β empirically: start small, increase until gradients are reliably above the noise floor (~10 LSBs minimum) but perturbations stay below ~5% of node voltage swing.

### Gradient Formula Applied

For a first-layer weight with ~1.0V free-phase voltage drop and 26mV hidden node perturbation:

```
ΔV_free  ≈ 1.000V
ΔV_nudge ≈ 1.026V
ΔV_nudge² − ΔV_free² = 1.026² − 1.000² = 0.053 V²
gradient = 0.053 / (2 × β)
```

The 0.053 V² signal is computed from ADC readings. Individual measurements that produce this are changes of ~26mV on absolute voltages of 2–3V. The critical requirement is that the ADC can resolve the 26mV difference between free and nudged readings — at 187.5µV/LSB, this is 139 counts of resolution.

---

## 14. Power Budget

| Component | Current |
|-----------|---------|
| Arduino Nano | ~20mA |
| 8× MCP4251 | ~0.008mA |
| MCP4822 | ~0.5mA |
| MCP6004 + LM324 | ~2.5mA |
| MCP6002 | ~0.1mA |
| ADS1115 | ~0.2mA |
| 2× CD4053 | ~0.2mA |
| 3× LEDs (2 output + 1 power) | ~15mA |
| Voltage dividers | ~0.5mA |
| Network currents | ~8mA worst case |
| **Total** | **~48mA** |

Well within USB supply capability.

---

## 15. Complete Parts List

| Component | Qty | Package | Function |
|-----------|-----|---------|----------|
| MCP4251-104 (100kΩ dual digipot) | 8 | DIP-14 | Weight resistors (16 weights). Tie SHDN and WP pins to VDD. |
| MCP4822 (dual 12-bit DAC) | 1 | DIP-8 | Nudge current control |
| MCP6004 (quad rail-to-rail op-amp) | 1 | DIP-14 | V_LOW/V_HIGH buffers + spare + LED comparator |
| LM324N (quad op-amp) | 1 | DIP-14 | V_MID buffers + LED comparator |
| MCP6002 (dual rail-to-rail op-amp) | 1 | DIP-8 | Howland current pumps |
| ADS1115 (16-bit ADC) | 1 | MSOP-10 | Node voltage measurement |
| CD4053 (triple 2:1 analog mux) | 2 | DIP-16 | Input + complement selection |
| Arduino Nano | 1 | Module (pin header sockets on PCB) | Training orchestration |
| BAT42 Schottky diode | 4 | DO-35 | Activation functions |
| USB-C connector (power only) | 1 | SMD | Board power input |
| SPDT toggle switch | 2 | Through-hole | Inference input selection |
| 1.21kΩ 1% metal film resistor | 16 | Axial | Pot series protection |
| 10kΩ 0.1% metal film resistor | 8 | Axial | Howland pump feedback (4 per pump) |
| 1MΩ 0.1% metal film resistor | 2 | Axial | Howland R_set |
| 10kΩ 1% resistor | 13 | Axial | V_MID divider (2) + CS pull-ups (9) + switch isolation (2) |
| 5.1kΩ 1% resistor | 2 | Axial | USB-C CC1/CC2 pull-downs |
| 4.7kΩ resistor | 2 | Axial | I2C pull-ups (SDA, SCL) |
| 33kΩ 1% resistor | 2 | Axial | V_LOW / V_HIGH dividers |
| 8.2kΩ 1% resistor | 2 | Axial | V_LOW / V_HIGH dividers |
| 1kΩ resistor | 1 | Axial | Power LED current limiting |
| 470Ω resistor | 2 | Axial | Output LED current limiting (active-low) |
| Green LED (3mm) | 2 | T-1 | XOR=1 indicator + power indicator |
| Red LED (3mm) | 1 | T-1 | XOR=0 indicator |
| 100nF ceramic capacitor | 20 | Radial | IC decoupling (15, one per non-Arduino IC) + voltage ref output (5: V_MID_H1, V_MID_H2, V_MID_PUMP, V_LOW, V_HIGH) |
| 10µF electrolytic capacitor | 3 | Radial | V_MID rail stiffening |
| 100µF electrolytic capacitor | 3 | Radial | Power rail bulk decoupling (2 near ICs + 1 after USB-C) |

**Total ICs: 14. Estimated BOM: ~$50–65 (excluding PCB fabrication).**

---

## 16. Known Limitations and Risks (Priority Order)

### Risk 1: Training convergence without bidirectional amplifiers
The paper uses VCVS (voltage gain A=4) + CCCS (current gain 1/A) between layers to prevent signal decay. Without them, hidden node voltages are compressed into a ~0.6V range (2.2–2.8V from Schottky clamping) instead of the full 3V input range. Second-layer voltage drops and gradients are proportionally smaller.

**Status:** Python simulation confirms XOR convergence in ~1800 epochs with the complementary-input + V_LOW/V_HIGH bias topology (16 weights). The key limitation that was blocking convergence — the odd-symmetry problem from V_MID bias — has been solved. Signal attenuation without amplifiers is tolerable for 2 layers.

**Mitigation:** For a 2-layer XOR network this is tolerable. The ADS1115 has sufficient resolution. If training fails after 10,000 epochs, amplifiers must be added.

**Escape hatch:** Hybrid digital approach — INA219 current sense + DAC-driven current source. Adds ~4 ICs.

### Risk 2: Schottky activation too aggressive
The 0.6V linear region may cause hidden nodes to saturate on every input pattern, providing no useful gradient information.

**Diagnosis:** Monitor hidden node voltages during training. If H1 and H2 are always near 2.0V or 3.0V regardless of input pattern, saturation is the problem.

**Fix:** Swap BAT42 to 1N4148 (1.2V linear range). Or add 100–500Ω series resistors with the Schottky diodes.

### Risk 3: Weight dynamic range insufficient
63:1 conductance range may not be enough for XOR, which needs some connections dominant and others negligible.

**Diagnosis:** Weights clustering at tap 256 (minimum R) or tap 1 (maximum R) during training.

**Fix:** Use MCP4251-504 (500kΩ pots) for wider range. Settling time increases (500kΩ × 50pF ≈ 25µs) but remains acceptable.

### Risk 4: Howland pump offset current
MCP6002's ~4.5mV input offset produces ~4.5nA unwanted DC current. Present in both phases, mostly cancels in gradient subtraction. Residual is a small constant bias on output node voltages.

**Fix if needed:** Calibrate in firmware — measure current at nominal zero and subtract.

### Risk 5: Volatile weight storage
The MCP4251 digital pots are **volatile** — wiper positions reset to midpoint (tap 128) when power is removed. Trained weights are lost on power-down.

**Mitigation:** Keep the board powered via USB-C during and after training. Unplugging only the Arduino (not the power) preserves weights.

**Fix for persistence:** Swap to **MCP4261** (pin-compatible drop-in replacement, same DIP-14 package). The MCP4261 has built-in EEPROM — trained weights survive power cycling indefinitely. Arduino firmware writes final wiper positions to EEPROM with a single SPI command after training completes. No other circuit changes needed.

### Risk 6: Pot tolerance mismatch
±20% end-to-end resistance tolerance means the R-vs-tap calibration in firmware is approximate. Equivalent to a per-weight learning rate varying by ±20%. SGD is robust to this.

**Fix if needed:** Per-pot calibration at startup — set tap to known values, measure network response.

---

## 17. LTspice Simulation Strategy

The purpose of simulation is to verify the design before purchasing components. Key things to validate:

### Simulation 1: Static Settling
Set all 16 weights to specific resistance values. Apply one XOR input pattern. Verify the circuit reaches a stable operating point. Check that hidden node voltages are within the expected 2.0–3.0V range. Verify output node voltages.

### Simulation 2: Diode Activation
Sweep a weight value while holding others fixed. Verify hidden nodes transition smoothly between the linear region (2.2–2.8V) and saturation. Confirm the Schottky diodes provide useful nonlinearity.

### Simulation 3: Nudge Response
Apply a small current (50nA–10µA) at one output node. Measure voltage changes at all nodes. Verify the perturbation propagates backward to hidden nodes. Confirm perturbation magnitudes match the analysis in Section 13.

### Simulation 4: Full Training Loop (SPICE + Python)
Use LTspice parametric simulation to sweep weight values. Post-process with Python to compute gradients and update weights. Iterate. Verify XOR convergence.

### LTspice Component Models
- **BAT42:** Built-in SPICE model (or use `.model BAT42 D(Is=1e-7 Rs=12 N=1.1 Cjo=15p Vj=0.25 M=0.5)`)
- **Resistors:** Standard, include 1.21kΩ series in each weight path
- **Current source:** Use behavioral source `B1 Y+ 0 I=(V(Vctrl)-2.5)/1e6` for Howland pump
- **Voltage sources:** Ideal DC sources for V_LOW, V_HIGH, V_MID rails
- **Op-amps (if modeling comparators):** Use LM324 subcircuit or ideal comparator model

---

## 18. Upgrade Path

### v1.1: Add Bidirectional Amplifiers
If training fails, add hybrid amplifiers between layers. Uses INA219 current sensors + DAC-driven current sources. +4 ICs. Circuit topology unchanged.

### v1.2: Holomorphic Equilibrium Propagation (Firmware-Only)
Laborieux & Zenke 2022 ("Holomorphic Equilibrium Propagation") eliminates finite-β bias entirely. Instead of DC nudge currents, the DAC generates an oscillating nudge signal at a known frequency. The ADC samples node voltages and a DFT extracts the component at the nudge frequency — this gives the exact gradient without the small-β approximation.

**Implementation:** Firmware-only change. Replace the DC nudge + two-phase measurement with:
1. DAC outputs a sinusoidal nudge current at frequency f (e.g., 100 Hz)
2. ADC samples node voltages at ≥4× rate (e.g., 400 SPS — within ADS1115 capability)
3. DFT on ADC readings extracts the amplitude and phase at frequency f
4. Gradient computed from the DFT coefficients

No hardware changes required. Removes the systematic bias from finite β, potentially improving convergence speed and stability.

### v1.3: Softer Activation Functions
Recent scaling work (Laborieux et al. 2021, "Scaling Equilibrium Propagation to Deep ConvNets") confirms softer activation functions train more reliably in deeper networks. If BAT42 Schottky diodes (0.6V linear region) prove too aggressive, swap to 1N4148 silicon diodes (1.2V linear region, same DO-35 package). The wider linear region provides smoother gradients at the cost of weaker nonlinearity.

### v2: Depth Scaling
For networks deeper than 2 layers:
- **Residual connections:** Add bypass resistors between layers (Hopfield-ResNet architecture). A single resistor from each input to the corresponding output-layer node provides a skip connection, preventing vanishing gradients.
- **Intermediate nudge injection:** Additional Howland pumps at hidden layers inject nudge signals at intermediate nodes, improving gradient propagation. Requires additional DAC channels (MCP4822 per layer pair).

### v3: Memristor Weights
Replace MCP4251 digital pots with Knowm M+SDC memristors. Two 8-DIP packages (16 memristors). Arduino applies voltage pulses for weight updates instead of SPI commands. Circuit topology unchanged. Cost: ~$240 for memristors.

### v4: Fully Analog Training
Custom PCB with AD633 analog multipliers, sample-and-hold circuits for gradient computation. Removes Arduino from training loop entirely. Only phase sequencing remains digital.

---

## 19. Key Insight — Why This Is a Real Analog Neural Network

**Forward pass:** The circuit physically settles to equilibrium via Kirchhoff's laws. Weighted sums computed by Ohm's law and KCL. Diodes compute activation functions. No clock cycles, no sequential operations. Pure analog physics.

**Nudge phase:** Error signal physically propagates backward through the network. Current injection at outputs causes the circuit to re-settle. Voltage changes at all nodes encode gradient information. Backward propagation through physics, not digital computation.

**Weight update:** The only digital step. Arduino reads voltages, computes gradients, programs pots. Same approach as the paper (Python between SPICE simulation runs).

**Inference after training:** Arduino disconnects. Apply input voltages, circuit settles, read outputs. Settling time: ~10µs on breadboard, ~1µs on PCB, nanoseconds on ASIC. Scales to large networks: a 1000×1000 resistive crossbar settles in the same time as a 2×2. Orders of magnitude faster and more energy-efficient than digital for large networks.
