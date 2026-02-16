# Section 6: Nudge Current Injection System

## Components

| Ref | Component | KiCad Symbol | Notes |
|-----|-----------|-------------|-------|
| U14 | MCP4822 (dual DAC) | `Analog_DAC:MCP4822` | Control voltage source |
| U15 | MCP6002 (dual op-amp) | `Amplifier_Operational:MCP6002-xP` | Howland current pumps |
| R_H1 | Howland resistor | `Device:R` | 10kΩ 0.1% |
| R_H2 | Howland resistor | `Device:R` | 10kΩ 0.1% |
| R_H3 | Howland resistor | `Device:R` | 10kΩ 0.1% |
| R_H4 | Howland resistor | `Device:R` | 10kΩ 0.1% |
| R_H5 | Howland resistor | `Device:R` | 10kΩ 0.1% |
| R_H6 | Howland resistor | `Device:R` | 10kΩ 0.1% |
| R_H7 | Howland resistor | `Device:R` | 10kΩ 0.1% |
| R_H8 | Howland resistor | `Device:R` | 10kΩ 0.1% |
| R_SET_A | Current-setting resistor | `Device:R` | 1MΩ 0.1% |
| R_SET_B | Current-setting resistor | `Device:R` | 1MΩ 0.1% |
| C_U14 | DAC decoupling | `Device:C` | 100nF |
| C_U15 | Op-amp decoupling | `Device:C` | 100nF |

## MCP4822 DAC (U14)

### Pin Connections

| MCP4822 Pin | Net | Notes |
|-------------|-----|-------|
| VDD | `+5V` | |
| CS | `CS_DAC` | From Arduino D9 |
| SCK | `SPI_SCK` | Shared SPI bus |
| SDI | `SPI_MOSI` | Shared SPI bus |
| LDAC | `GND` | Tie low for immediate output update on CS rising edge |
| VOUTA | `DAC_OUTA` | Control voltage for Pump A (Y+ node) |
| VOUTB | `DAC_OUTB` | Control voltage for Pump B (Y- node) |
| AVSS | `GND` | |

Notes:
- MCP4822 is write-only (no SDO/MISO pin) — no SPI bus contention
- Internal 2.048V reference with 2x gain → output range 0V to 4.096V
- At DAC code ~2500: output ≈ 2.5V → zero current from pump
- 100nF decoupling cap (C_U14) from VDD to AVSS, close to IC

## Improved Howland Current Pump — Circuit Topology

Two identical pumps, one per output node. Each pump converts a voltage from the DAC
into a bidirectional current with high output impedance.

**V_MID_PUMP** is the 2.5V buffered reference from Section 1 (LM324 #2 section C, U2C).

Formula: I_out = (V_control - V_MID_PUMP) / R_SET = (V_control - 2.5V) / 1MΩ

### Pump A (Y+ node) — MCP6002 Section A (U15A)

```
DAC_OUTA ─── R_H1 (10kΩ) ──┬── (+) U15A
                             │
                 R_SET_A (1MΩ) ── YP
                             │
V_MID_PUMP ─── R_H2 (10kΩ) ──┬── (-) U15A
                               │
                    R_H3 (10kΩ) ── U15A output
                               │
                    R_H4 (10kΩ) ── U15A output ─── YP
```

Explicit connections:
- R_H1 (10kΩ): one end → `DAC_OUTA`, other end → U15A non-inv input (+)
- R_SET_A (1MΩ): one end → U15A non-inv input (+), other end → `YP`
- R_H2 (10kΩ): one end → `V_MID_PUMP`, other end → U15A inv input (-)
- R_H3 (10kΩ): one end → U15A output, other end → U15A inv input (-)
- R_H4 (10kΩ): one end → U15A output, other end → `YP`

So:
- U15A non-inv input (+) connects to: R_H1 (from DAC_OUTA) AND R_SET_A (to YP)
- U15A inv input (-) connects to: R_H2 (from V_MID_PUMP) AND R_H3 (from U15A output)
- U15A output connects to: R_H3 (to inv input) AND R_H4 (to YP)
- `YP` node connects to: R_SET_A AND R_H4

### Pump B (Y- node) — MCP6002 Section B (U15B)

Identical topology, different nets:
- R_H5 (10kΩ): one end → `DAC_OUTB`, other end → U15B non-inv input (+)
- R_SET_B (1MΩ): one end → U15B non-inv input (+), other end → `YN`
- R_H6 (10kΩ): one end → `V_MID_PUMP`, other end → U15B inv input (-)
- R_H7 (10kΩ): one end → U15B output, other end → U15B inv input (-)
- R_H8 (10kΩ): one end → U15B output, other end → `YN`

### MCP6002 Power (U15 power unit)

| MCP6002 Pin | Net |
|-------------|-----|
| VDD | `+5V` |
| VSS | `GND` |

C_U15 (100nF): `+5V` to `GND`, close to IC.

## Howland Pump Schematic Drawing Guide

The Howland pump looks like a non-inverting amplifier with positive feedback added.
When drawing in KiCad:

1. Place the op-amp section (U15A or U15B)
2. Place R_H1 horizontally leading into the (+) input from the left
3. Place R_SET vertically/diagonally from the (+) input down to the output node
4. Place R_H2 horizontally leading into the (-) input from the left
5. Place R_H3 from the op-amp output back to the (-) input (negative feedback)
6. Place R_H4 from the op-amp output to the output node (where R_SET also goes)

The output node (YP or YN) is where R_SET and R_H4 meet — this is the current
injection point into the analog network.

## Verification

At V_control = 2.5V (DAC midpoint):
- I_out = (2.5 - 2.5) / 1MΩ = 0 (free phase, no nudge)

At V_control = 2.5 ± 0.05V (small offset for nudge):
- I_out = ±0.05V / 1MΩ = ±50nA

Maximum nudge (V_control = 2.5 ± 1.5V):
- I_out = ±1.5µA

## Test Points

Add test points on `DAC_OUTA`, `DAC_OUTB`, `YP`, `YN`.
YP and YN are shared with Section 7 (measurement).
