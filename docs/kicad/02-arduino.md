# Section 2: Arduino Nano

## Component

| Ref | Component | KiCad Symbol |
|-----|-----------|-------------|
| U3 | Arduino Nano v3.x | `MCU_Module:Arduino_Nano_v3.x` |

## Power Connections

- 5V pin → `+5V` (board powers the Nano through this pin)
- GND pins (there are 2) → `GND`
- VIN → leave unconnected (not used; board power comes via 5V pin)

Note: The Arduino's own USB port is only used for serial monitoring and firmware upload
during training. The board's USB-C provides the actual 5V power to the circuit.

## Pin Assignments — All Net Labels

| Arduino Pin | KiCad Pin Name | Net Label | Direction | Function |
|-------------|---------------|-----------|-----------|----------|
| D2 | D2 | `MUX_A` | OUTPUT | CD4053 control A (X1/X1_comp select) |
| D3 | D3 | `MUX_B` | OUTPUT | CD4053 control B (X2/X2_comp select) |
| D4 | D4 | `CS_POT1` | OUTPUT | MCP4251 #1 CS (W1, W2) |
| D5 | D5 | `CS_POT2` | OUTPUT | MCP4251 #2 CS (W3, W4) |
| D6 | D6 | `CS_POT3` | OUTPUT | MCP4251 #3 CS (W5, W6) |
| D7 | D7 | `CS_POT4` | OUTPUT | MCP4251 #4 CS (W7, W8) |
| D8 | D8 | `CS_POT5` | OUTPUT | MCP4251 #5 CS (W9, W10) |
| D9 | D9 | `CS_DAC` | OUTPUT | MCP4822 CS |
| D10 | D10 | `CS_POT6` | OUTPUT | MCP4251 #6 CS (W11, W12) |
| D11 | D11 | `SPI_MOSI` | OUTPUT | SPI MOSI (shared bus) |
| D12 | D12 | `SPI_MISO` | INPUT | SPI MISO (shared bus) |
| D13 | D13 | `SPI_SCK` | OUTPUT | SPI SCK (shared bus) |
| A0 | A0 | `X1` | ANALOG IN | X1 voltage measurement (connects to X1 mux output net) |
| A1 | A1 | `X2` | ANALOG IN | X2 voltage measurement (connects to X2 mux output net) |
| A2 | A2 | `CS_POT7` | OUTPUT | MCP4251 #7 CS (W13, W14) |
| A3 | A3 | `CS_POT8` | OUTPUT | MCP4251 #8 CS (W15, W16) |
| A4 | A4 | `I2C_SDA` | BIDIR | ADS1115 SDA |
| A5 | A5 | `I2C_SCL` | BIDIR | ADS1115 SCL |

## Unused Pins

- D0, D1 — Serial TX/RX (reserved for USB serial, leave unconnected on PCB)
- A6, A7 — Spare analog inputs (leave unconnected)
- AREF — leave unconnected
- RST — leave unconnected (has internal pull-up)

## CS Pull-Up Resistors

Each CS line gets a 10kΩ pull-up to `+5V`. This ensures all SPI devices are
deselected during Arduino reset/boot (CS is active LOW).

| Resistor | From | To |
|----------|------|----|
| R_PU1 (10kΩ) | `CS_POT1` | `+5V` |
| R_PU2 (10kΩ) | `CS_POT2` | `+5V` |
| R_PU3 (10kΩ) | `CS_POT3` | `+5V` |
| R_PU4 (10kΩ) | `CS_POT4` | `+5V` |
| R_PU5 (10kΩ) | `CS_POT5` | `+5V` |
| R_PU6 (10kΩ) | `CS_POT6` | `+5V` |
| R_PU7 (10kΩ) | `CS_POT7` | `+5V` |
| R_PU8 (10kΩ) | `CS_POT8` | `+5V` |
| R_PU9 (10kΩ) | `CS_DAC` | `+5V` |

Total: 9x 10kΩ pull-up resistors.

## Notes on KiCad Symbol

The Arduino Nano v3.x symbol in KiCad is a single unit with all pins on one symbol.
Pin names on the symbol should match standard Arduino naming (D0-D13, A0-A7, 5V, GND, VIN, etc.).
Place the Arduino at the left side of the schematic, with signal nets radiating right toward
the components they connect to.

The symbol's footprint includes the full Nano module outline with dual-row pin headers.
On the PCB, use female pin header sockets so the Nano is removable.

## Sense Connections for X1/X2

Arduino A0 and A1 connect directly to the `X1` and `X2` nets (the mux common outputs
from Section 3). No separate net names needed — just label the wire from A0 as `X1`
and from A1 as `X2`. The Arduino's ADC input impedance is ~100MΩ, so loading on
the mux output is negligible.
