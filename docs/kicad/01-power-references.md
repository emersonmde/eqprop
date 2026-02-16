# Section 1: Power + Voltage References

## Components in this section

| Ref | Component | KiCad Symbol | Value |
|-----|-----------|-------------|-------|
| J1 | USB-C connector | `Connector:USB_C_Receptacle_USB2.0` (or simpler power-only) | — |
| U1 | MCP6004 #1 | `Amplifier_Operational:MCP6004-xP` | Rail-to-rail I/O (required for V_HIGH 4.0V buffer) |
| U2 | LM324 #2 | `Amplifier_Operational:LM324` | OK for 2.5V V_MID buffers |
| R1 | V_MID divider top | `Device:R` | 10kΩ 1% |
| R2 | V_MID divider bottom | `Device:R` | 10kΩ 1% |
| R3 | V_LOW divider top | `Device:R` | 8kΩ 1% |
| R4 | V_LOW divider bottom | `Device:R` | 2kΩ 1% |
| R5 | V_HIGH divider top | `Device:R` | 2kΩ 1% |
| R6 | V_HIGH divider bottom | `Device:R` | 8kΩ 1% |
| R_CC1 | USB-C CC1 pull-down | `Device:R` | 5.1kΩ |
| R_CC2 | USB-C CC2 pull-down | `Device:R` | 5.1kΩ |
| R_LED1 | Power LED resistor | `Device:R` | 1kΩ |
| D_PWR | Power LED | `Device:LED` | Green 3mm |
| C1 | Bulk cap after USB-C | `Device:C_Polarized` | 100µF |
| C2 | U1 VCC decoupling | `Device:C` | 100nF |
| C3 | U2 VCC decoupling | `Device:C` | 100nF |
| C4 | V_MID_H1 electrolytic | `Device:C_Polarized` | 10µF |
| C5 | V_MID_H1 ceramic | `Device:C` | 100nF |
| C6 | V_MID_H2 electrolytic | `Device:C_Polarized` | 10µF |
| C7 | V_MID_H2 ceramic | `Device:C` | 100nF |
| C8 | V_MID_PUMP electrolytic | `Device:C_Polarized` | 10µF |
| C9 | V_MID_PUMP ceramic | `Device:C` | 100nF |
| C10 | V_LOW decoupling | `Device:C` | 100nF |
| C11 | V_HIGH decoupling | `Device:C` | 100nF |
| C12 | Bulk cap near U1/U2 | `Device:C_Polarized` | 100µF |
| C13 | Bulk cap near digital cluster | `Device:C_Polarized` | 100µF |

## USB-C Power Input

If using a full USB-C receptacle symbol:
- VBUS → `+5V`
- GND → `GND`
- CC1 → 5.1kΩ (R_CC1) → `GND`
- CC2 → 5.1kΩ (R_CC2) → `GND`
- All other pins (D+, D-, SBU1, SBU2, SHIELD) → leave unconnected or tie SHIELD to GND

Simpler alternative: use `Connector_Generic:Conn_01x02` labeled "USB-C Power" and handle
the CC resistors on the footprint. The full receptacle symbol is better for PCB correctness.

C1 (100µF polarized): `+5V` to `GND`, placed close to connector.

## Voltage Dividers

### V_MID (2.5V)
```
+5V ─── R1 (10kΩ) ─── V_MID_RAW ─── R2 (10kΩ) ─── GND
```

### V_LOW (1.0V)
```
+5V ─── R3 (8kΩ) ─── V_LOW_RAW ─── R4 (2kΩ) ─── GND
```

### V_HIGH (4.0V)
```
+5V ─── R5 (2kΩ) ─── V_HIGH_RAW ─── R6 (8kΩ) ─── GND
```

## MCP6004 #1 (U1) — V_LOW/V_HIGH buffers + spare + comparator

**Why MCP6004 instead of LM324:** The LM324 cannot output 4.0V on a 5V supply (VOH ≈ 3.5V)
and its input common-mode range (0V to VCC−1.5V = 3.5V) is exceeded by V_HIGH_RAW = 4.0V.
The MCP6004 is a pin-compatible DIP-14 quad op-amp with rail-to-rail I/O.

KiCad splits the MCP6004 into 5 units: A, B, C, D (op-amp sections) + E (power pins).
Pinout is identical to LM324 (standard quad op-amp DIP-14 pinout).

### Power unit (U1E)
- VDD → `+5V`
- VSS → `GND`
- C2 (100nF): `+5V` to `GND` close to pin

### Section A (U1A) — V_LOW buffer
- Non-inverting input (+) → `V_LOW_RAW`
- Inverting input (−) → output (direct wire, voltage follower)
- Output → net `V_LOW`
- C10 (100nF): `V_LOW` to `GND`

### Section B (U1B) — V_HIGH buffer
- Non-inverting input (+) → `V_HIGH_RAW`
- Inverting input (−) → output (voltage follower)
- Output → net `V_HIGH`
- C11 (100nF): `V_HIGH` to `GND`

### Section C (U1C) — Spare (parked)
- Non-inverting input (+) → `GND`
- Inverting input (−) → output (follower configuration, output at GND)
- Output → leave floating (no load)

### Section D (U1D) — LED comparator (wired in Section 7)
- Leave pins unconnected for now, wire in Section 7

## LM324 #2 (U2) — V_MID buffers + comparator

### Power unit (U2E)
- V+ → `+5V`
- V- → `GND`
- C3 (100nF): `+5V` to `GND` close to pin

### Section A (U2A) — V_MID_H1 buffer
- Non-inverting input (+) → `V_MID_RAW`
- Inverting input (−) → output (voltage follower)
- Output → net `V_MID_H1`
- C4 (10µF polarized): `V_MID_H1` to `GND`
- C5 (100nF): `V_MID_H1` to `GND`

### Section B (U2B) — V_MID_H2 buffer
- Non-inverting input (+) → `V_MID_RAW`
- Inverting input (−) → output (voltage follower)
- Output → net `V_MID_H2`
- C6 (10µF polarized): `V_MID_H2` to `GND`
- C7 (100nF): `V_MID_H2` to `GND`

### Section C (U2C) — V_MID_PUMP buffer
- Non-inverting input (+) → `V_MID_RAW`
- Inverting input (−) → output (voltage follower)
- Output → net `V_MID_PUMP`
- C8 (10µF polarized): `V_MID_PUMP` to `GND`
- C9 (100nF): `V_MID_PUMP` to `GND`

### Section D (U2D) — LED comparator (wired in Section 7)
- Leave pins unconnected for now

## Power LED
```
+5V ─── R_LED1 (1kΩ) ─── D_PWR anode ─── D_PWR cathode ─── GND
```

## Bulk Capacitors
- C1 (100µF): after USB-C connector, `+5V` to `GND`
- C12 (100µF): near U1/U2 analog op-amp cluster, `+5V` to `GND`
- C13 (100µF): near digital IC cluster (MCP4251s / Arduino area), `+5V` to `GND`

## Test Points for this section
Add test point symbols (`Connector:TestPoint`) on: `V_LOW`, `V_HIGH`, `V_MID_H1`, `V_MID_H2`, `V_MID_PUMP`
