# KiCad Schematic Guide — Overview

## Project: Analog EqProp XOR Network

Reference: `docs/design.md` (v2 Final)

## KiCad Symbol Library Reference

| Component | Qty | KiCad Symbol | Package |
|-----------|-----|-------------|---------|
| MCP4251-104 | 8 | `Potentiometer_Digital:MCP4251-xxxx-P` | DIP-14 |
| MCP4822 | 1 | `Analog_DAC:MCP4822` | DIP-8 |
| MCP6002 | 1 | `Amplifier_Operational:MCP6002-xP` | DIP-8 |
| MCP6004 | 1 | `Amplifier_Operational:MCP6004-xP` | DIP-14 |
| LM324N | 1 | `Amplifier_Operational:LM324` | DIP-14 |
| ADS1115 | 1 | `Analog_ADC:ADS1115IDGS` | VSSOP-10 |
| CD4053B | 2 | `Analog_Switch:CD4053B` | DIP-16 |
| BAT42 | 4 | `Diode:BAT42` | DO-35 |
| Arduino Nano | 1 | `MCU_Module:Arduino_Nano_v3.x` | Module |

## Net Naming Convention

### Power Nets
- `+5V`, `GND` — standard KiCad power symbols

### Voltage Reference Nets
- `V_MID_RAW` — 2.5V divider output (before buffers)
- `V_LOW_RAW` — ≈1.0V divider output (before buffer)
- `V_HIGH_RAW` — ≈4.0V divider output (before buffer)
- `V_LOW` — ≈1.0V buffered output
- `V_HIGH` — ≈4.0V buffered output
- `V_MID_H1` — 2.5V buffer for H1 diode pair
- `V_MID_H2` — 2.5V buffer for H2 diode pair
- `V_MID_PUMP` — 2.5V buffer for Howland pumps

### Signal Nets
- `X1`, `X1_COMP` — input 1 direct and complement
- `X2`, `X2_COMP` — input 2 direct and complement
- `H1`, `H2` — hidden node voltages
- `YP`, `YN` — output node voltages (Y+, Y−)

### SPI Bus
- `SPI_MOSI`, `SPI_MISO`, `SPI_SCK` — shared bus
- `CS_POT1` through `CS_POT8` — MCP4251 chip selects
- `CS_DAC` — MCP4822 chip select

### I2C Bus
- `I2C_SDA`, `I2C_SCL`

### Control
- `MUX_A`, `MUX_B` — CD4053 control pins (input pattern select)
- `DAC_OUTA`, `DAC_OUTB` — MCP4822 analog outputs to Howland pumps

## Schematic Sections (7 files)

1. `01-power-references.md` — USB-C, dividers, MCP6004/LM324 buffers, power LED
2. `02-arduino.md` — Arduino Nano pin assignments and net labels
3. `03-input-muxes.md` — 2x CD4053B, toggle switches
4. `04-weight-resistors.md` — 8x MCP4251 + 16x 1.21kΩ series resistors
5. `05-activation-diodes.md` — 4x BAT42 in antiparallel pairs
6. `06-nudge-system.md` — MCP4822 DAC + MCP6002 Howland pumps
7. `07-measurement-output.md` — ADS1115 ADC + LED comparators

## Schematic Organization

Flat schematic (single sheet or 2 sheets). Group components spatially by section.
Suggested layout on sheet: power/refs at top-left, Arduino at bottom-left,
signal flow left-to-right: inputs → muxes → weights → hidden nodes → weights → output nodes.

## Defensive Design Features (for first-spin PCB)

- DIP sockets for all ICs (populate sockets, insert ICs by hand)
- 2-pin headers or SIP sockets for BAT42 diodes (swappable to 1N4148)
- Solder bridge pads near each diode pair (bridged by default, cut and add 100-500Ω to soften)
- Test points on: H1, H2, YP, YN, V_MID_H1, V_MID_H2, V_MID_PUMP, V_LOW, V_HIGH
- 100µF bulk caps near power entry and near IC clusters
