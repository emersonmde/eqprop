# KiCad Schematic Reference

## Project: Analog EqProp XOR Network

Schematic: `cad/eqprop-xor/eqprop-xor.kicad_sch` (KiCad 9, flat single-sheet A2)
Hardware design: `docs/design.md`

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

Note: In KiCad 9, some symbols drop the package suffix (e.g. `MCP6004` instead of
`MCP6004-xP`). The `-xP` variants are DIP packages matching the BOM. Footprints are
assigned separately via Tools > Assign Footprints before PCB layout.

## Net Naming Convention

### Power Nets
- `+5V`, `GND` — standard KiCad power symbols

### Voltage Reference Nets
- `V_MID_RAW` — 2.5V divider output (before buffers)
- `V_LOW_RAW` — ~1.0V divider output (before buffer)
- `V_HIGH_RAW` — ~4.0V divider output (before buffer)
- `V_LOW` — ~1.0V buffered output
- `V_HIGH` — ~4.0V buffered output
- `V_MID_H1` — 2.5V buffer for H1 diode pair
- `V_MID_H2` — 2.5V buffer for H2 diode pair
- `V_MID_PUMP` — 2.5V buffer for Howland pumps

### Signal Nets
- `X1`, `X1_COMP` — input 1 direct and complement
- `X2`, `X2_COMP` — input 2 direct and complement
- `H1`, `H2` — hidden node voltages
- `YP`, `YN` — output node voltages (Y+, Y-)

### SPI Bus
- `SPI_MOSI`, `SPI_MISO`, `SPI_SCK` — shared bus
- `CS_POT1` through `CS_POT8` — MCP4251 chip selects
- `CS_DAC` — MCP4822 chip select

### I2C Bus
- `I2C_SDA`, `I2C_SCL`

### Control
- `MUX_A`, `MUX_B` — CD4053 control pins (input pattern select)
- `DAC_OUTA`, `DAC_OUTB` — MCP4822 analog outputs to Howland pumps

## Schematic Sections

The schematic is organized into functional blocks on a single A2 sheet:

1. **Power + Voltage References** — USB-C input, 3 voltage dividers, MCP6004 (V_LOW/V_HIGH buffers), LM324 (V_MID buffers), bulk decoupling, power LED
2. **Microcontroller** — Arduino Nano pin assignments, 9x 10k CS pull-up resistors
3. **Input Multiplexers** — 2x CD4053B (direct + complementary), SPDT toggle switches with 10k isolation resistors
4. **Weight Network** — 8x MCP4251 digital pots (16 weight channels), 16x 1.21k series protection resistors
5. **Activation Diodes** — 4x BAT42 in antiparallel pairs with solder bridge pads, on H1/H2 nodes
6. **Nudge Current Injection** — MCP4822 DAC + MCP6002 Howland current pumps (YP/YN)
7. **Measurement + Output** — ADS1115 16-bit ADC (H1/H2/YP/YN), I2C pull-ups, LED comparators (U1D/U2D)

Detailed per-section wiring references are in `01-power-references.md` through `07-measurement-output.md`.

## Defensive Design Features (for first-spin PCB)

- DIP sockets for all ICs (populate sockets, insert ICs by hand)
- 2-pin headers or SIP sockets for BAT42 diodes (swappable to 1N4148)
- Solder bridge pads near each diode pair (bridged by default, cut and add 100-500R to soften)
- Test points on: H1, H2, YP, YN, V_MID_H1, V_MID_H2, V_MID_PUMP, V_LOW, V_HIGH, DAC_OUTA, DAC_OUTB
- 100uF bulk caps near power entry and near IC clusters

## CD4053B Pin Name Mapping

KiCad 9 uses S1/S2/S3 for the mux common pins (not Ac/Bc/Cc):
- S1 = Channel A common, S2 = Channel B common, S3 = Channel C common
- A0/A1, B0/B1, C0/C1 = selectable pins (0 = ctrl LOW, 1 = ctrl HIGH)
