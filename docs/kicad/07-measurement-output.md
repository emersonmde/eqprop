# Section 7: Measurement + Output Indication

## Components

| Ref | Component | KiCad Symbol | Notes |
|-----|-----------|-------------|-------|
| U16 | ADS1115 (16-bit ADC) | `Analog_ADC:ADS1115IDGS` | VSSOP-10 (SMD) |
| R_SDA | I2C SDA pull-up | `Device:R` | 4.7kΩ |
| R_SCL | I2C SCL pull-up | `Device:R` | 4.7kΩ |
| C_U16 | ADC decoupling | `Device:C` | 100nF |
| D_GRN | Green LED (XOR=1) | `Device:LED` | 3mm green |
| D_RED | Red LED (XOR=0) | `Device:LED` | 3mm red |
| R_LED_G | Green LED resistor | `Device:R` | 470Ω |
| R_LED_R | Red LED resistor | `Device:R` | 470Ω |

## ADS1115 (U16) — 16-bit ADC

### Pin Connections

| ADS1115 Pin | Net | Notes |
|-------------|-----|-------|
| ADDR | `GND` | I2C address = 0x48 |
| ALERT/RDY | unconnected | (or connect to Arduino interrupt pin if desired) |
| GND | `GND` | |
| AIN0 | `H1` | Hidden node 1 voltage |
| AIN1 | `H2` | Hidden node 2 voltage |
| AIN2 | `YP` | Output node Y+ |
| AIN3 | `YN` | Output node Y- |
| VDD | `+5V` | |
| SDA | `I2C_SDA` | |
| SCL | `I2C_SCL` | |

### Decoupling
C_U16 (100nF): VDD to GND, placed as close to the IC as possible.

### I2C Pull-Up Resistors
- R_SDA (4.7kΩ): `I2C_SDA` → `+5V`
- R_SCL (4.7kΩ): `I2C_SCL` → `+5V`

### PGA Setting Note (firmware, not schematic)
Use ±6.144V PGA range (NOT ±4.096V). The tighter range clips voltages near V_HIGH≈4.0V.
At ±6.144V: LSB = 187.5µV, full 0-5V range covered with headroom.

### PCB Note
The ADS1115IDGS is VSSOP-10 (0.5mm pitch SMD). This is the one component that
genuinely benefits from factory assembly. Keep analog input traces short and away
from SPI/digital traces to minimize noise coupling.

## LED Output Comparators

These use the remaining op-amp sections from the two LM324s placed in Section 1.
The comparators are wired **active-low** for consistency. The LM324 (#2) output can
only reach ~3.5V on the high side, while the MCP6004 (#1) is rail-to-rail. Active-low
sinking works reliably for both ICs.

### Comparator A — Green LED "XOR = 1" (U1D, MCP6004 #1 Section D)

This was left unwired in Section 1. Now complete the connections:

| U1D Pin | Net | Notes |
|---------|-----|-------|
| Non-inverting input (+) | `YN` | Y- output node |
| Inverting input (-) | `YP` | Y+ output node |
| Output | → D_GRN cathode | Sinks current when Y+ > Y- |

When Y+ > Y- (positive prediction, XOR=1):
- (+) input (YN) < (-) input (YP) → output goes LOW
- Output sinks current through LED → LED ON

LED wiring:
```
+5V ─── R_LED_G (470Ω) ─── D_GRN anode ─── D_GRN cathode ─── U1D output
```

LED current: (5V - 2.0V LED drop - ~0.05V MCP6004 output low) / 470Ω ≈ 6.3mA (bright).
When output is HIGH (~4.95V for MCP6004): only ~0.05V across LED+resistor → LED OFF.

### Comparator B — Red LED "XOR = 0" (U2D, LM324 #2 Section D)

| U2D Pin | Net | Notes |
|---------|-----|-------|
| Non-inverting input (+) | `YP` | Y+ output node |
| Inverting input (-) | `YN` | Y- output node |
| Output | → D_RED cathode | Sinks current when Y- > Y+ |

When Y- > Y+ (negative or zero prediction):
- (+) input (YP) < (-) input (YN) → output goes LOW → LED ON

LED wiring:
```
+5V ─── R_LED_R (470Ω) ─── D_RED anode ─── D_RED cathode ─── U2D output
```

### LED Behavior Summary

| Condition | Y+ vs Y- | Green LED | Red LED |
|-----------|----------|-----------|---------|
| XOR = 1 (target 0.3V) | Y+ > Y- | ON | OFF |
| XOR = 0 (target 0V) | Y+ ≈ Y- or Y- > Y+ | OFF | ON (or dim) |

Both LEDs work with no Arduino — pure analog readout after training.
Comparator inputs draw negligible current from output nodes (>1MΩ for LM324, >10TΩ for MCP6004).

## Test Points

Add test points on: `YP`, `YN` (if not already added in Section 6).

Also useful: test points on U1D output and U2D output for debugging comparator behavior.

## Complete I2C Bus

The I2C bus only has one device (ADS1115). Connections:
- Arduino A4 → `I2C_SDA` → R_SDA (4.7kΩ) → `+5V`
- Arduino A5 → `I2C_SCL` → R_SCL (4.7kΩ) → `+5V`
- ADS1115 SDA → `I2C_SDA`
- ADS1115 SCL → `I2C_SCL`

## Full Component Count Summary (All Sections)

| Category | Count |
|----------|-------|
| ICs + modules | 14 ICs + 1 Arduino module (1x MCP6004, 1x LM324, 8x MCP4251, 1x MCP4822, 1x MCP6002, 1x ADS1115, 2x CD4053B, 1x Arduino Nano) |
| Diodes | 4x BAT42 |
| LEDs | 3 (1x green power, 1x green XOR=1, 1x red XOR=0) |
| Resistors | 50 (16x 1.21kΩ series, 9x 10kΩ CS pull-up, 8x 10kΩ 0.1% Howland, 2x 1MΩ 0.1% R_SET, 2x 10kΩ V_MID divider, 2x 33kΩ V_LOW/V_HIGH divider, 2x 8.2kΩ V_LOW/V_HIGH divider, 2x 5.1kΩ USB-C CC, 2x 4.7kΩ I2C, 1x 1kΩ power LED, 2x 470Ω output LEDs, 2x 10kΩ switch isolation) + 4x solder bridge pads (diode series) |
| Capacitors | 26 (20x 100nF ceramic [15 IC decoupling + 5 voltage ref output], 3x 10µF electrolytic [V_MID rails], 3x 100µF electrolytic [1 after USB-C + 2 near IC clusters]) |
| Switches | 2x SPDT toggle |
| Connectors | 1x USB-C + Arduino pin headers + test points |
