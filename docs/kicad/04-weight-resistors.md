# Section 4: Weight Resistors

## Components

### 8x MCP4251-104 Digital Potentiometers

| Ref | KiCad Symbol | CS Net | Weights | Connections |
|-----|-------------|--------|---------|-------------|
| U6 | `Potentiometer_Digital:MCP4251-xxxx-P` | `CS_POT1` | W1, W2 | X1→H1, X1→H2 |
| U7 | `Potentiometer_Digital:MCP4251-xxxx-P` | `CS_POT2` | W3, W4 | X1_COMP→H1, X1_COMP→H2 |
| U8 | `Potentiometer_Digital:MCP4251-xxxx-P` | `CS_POT3` | W5, W6 | X2→H1, X2→H2 |
| U9 | `Potentiometer_Digital:MCP4251-xxxx-P` | `CS_POT4` | W7, W8 | X2_COMP→H1, X2_COMP→H2 |
| U10 | `Potentiometer_Digital:MCP4251-xxxx-P` | `CS_POT5` | W9, W10 | V_LOW→H1, V_LOW→H2 |
| U11 | `Potentiometer_Digital:MCP4251-xxxx-P` | `CS_POT6` | W11, W12 | V_HIGH→H1, V_HIGH→H2 |
| U12 | `Potentiometer_Digital:MCP4251-xxxx-P` | `CS_POT7` | W13, W14 | H1→YP, H1→YN |
| U13 | `Potentiometer_Digital:MCP4251-xxxx-P` | `CS_POT8` | W15, W16 | H2→YP, H2→YN |

### 16x 1.21kΩ Series Protection Resistors

| Ref | Value | Weight | Input-Side Net | Resistor → Pot Terminal |
|-----|-------|--------|---------------|------------------------|
| R_W1 | 1.21kΩ 1% | W1 | `X1` | → U6 P0A |
| R_W2 | 1.21kΩ 1% | W2 | `X1` | → U6 P1A |
| R_W3 | 1.21kΩ 1% | W3 | `X1_COMP` | → U7 P0A |
| R_W4 | 1.21kΩ 1% | W4 | `X1_COMP` | → U7 P1A |
| R_W5 | 1.21kΩ 1% | W5 | `X2` | → U8 P0A |
| R_W6 | 1.21kΩ 1% | W6 | `X2` | → U8 P1A |
| R_W7 | 1.21kΩ 1% | W7 | `X2_COMP` | → U9 P0A |
| R_W8 | 1.21kΩ 1% | W8 | `X2_COMP` | → U9 P1A |
| R_W9 | 1.21kΩ 1% | W9 | `V_LOW` | → U10 P0A |
| R_W10 | 1.21kΩ 1% | W10 | `V_LOW` | → U10 P1A |
| R_W11 | 1.21kΩ 1% | W11 | `V_HIGH` | → U11 P0A |
| R_W12 | 1.21kΩ 1% | W12 | `V_HIGH` | → U11 P1A |
| R_W13 | 1.21kΩ 1% | W13 | `H1` | → U12 P0A |
| R_W14 | 1.21kΩ 1% | W14 | `H1` | → U12 P1A |
| R_W15 | 1.21kΩ 1% | W15 | `H2` | → U13 P0A |
| R_W16 | 1.21kΩ 1% | W16 | `H2` | → U13 P1A |

## MCP4251 Pin Connections (Same for All 8 Chips)

The MCP4251 in KiCad has these pins. Each chip is identical except for CS net
and which network nodes connect to the pot terminals.

### SPI + Power (same for all chips)

| MCP4251 Pin | Net | Notes |
|-------------|-----|-------|
| CS | (see per-chip CS net above) | Active low |
| SCK | `SPI_SCK` | |
| SDI | `SPI_MOSI` | |
| SDO | `SPI_MISO` | |
| VDD | `+5V` | |
| VSS | `GND` | |
| SHDN | `+5V` | Active low — tie high for normal operation |
| WP | `+5V` | Active low — tie high to allow writes |

### Pot Terminal Connections

Each MCP4251 has two pots: P0 (Pot A in our design) and P1 (Pot B).
Each pot has three terminals: PxA, PxW (wiper), PxB.

**Rheostat configuration:** We use each pot as a 2-terminal variable resistor.
- PxA → series resistor (input side)
- PxW → output node (network side)
- PxB → tie to PxW (failsafe: if wiper loses contact, shorts to max resistance
  instead of open circuit)

At tap 0 (zero scale): wiper at PxB end → R(A-W) ≈ 100kΩ (max resistance).
At tap 256 (full scale): wiper at PxA end → R(A-W) ≈ 390Ω (wiper resistance only).
Firmware enforces minimum tap = 1.

### Per-Chip Wiring Detail

**U6 (MCP4251 #1) — W1: X1→H1, W2: X1→H2**
- P0A → R_W1 (other end of R_W1 → `X1`)
- P0W → `H1`
- P0B → `H1` (tie to P0W)
- P1A → R_W2 (other end of R_W2 → `X1`)
- P1W → `H2`
- P1B → `H2` (tie to P1W)
- CS → `CS_POT1`

**U7 (MCP4251 #2) — W3: X1_COMP→H1, W4: X1_COMP→H2**
- P0A → R_W3 (→ `X1_COMP`)
- P0W → `H1`, P0B → `H1`
- P1A → R_W4 (→ `X1_COMP`)
- P1W → `H2`, P1B → `H2`
- CS → `CS_POT2`

**U8 (MCP4251 #3) — W5: X2→H1, W6: X2→H2**
- P0A → R_W5 (→ `X2`)
- P0W → `H1`, P0B → `H1`
- P1A → R_W6 (→ `X2`)
- P1W → `H2`, P1B → `H2`
- CS → `CS_POT3`

**U9 (MCP4251 #4) — W7: X2_COMP→H1, W8: X2_COMP→H2**
- P0A → R_W7 (→ `X2_COMP`)
- P0W → `H1`, P0B → `H1`
- P1A → R_W8 (→ `X2_COMP`)
- P1W → `H2`, P1B → `H2`
- CS → `CS_POT4`

**U10 (MCP4251 #5) — W9: V_LOW→H1, W10: V_LOW→H2**
- P0A → R_W9 (→ `V_LOW`)
- P0W → `H1`, P0B → `H1`
- P1A → R_W10 (→ `V_LOW`)
- P1W → `H2`, P1B → `H2`
- CS → `CS_POT5`

**U11 (MCP4251 #6) — W11: V_HIGH→H1, W12: V_HIGH→H2**
- P0A → R_W11 (→ `V_HIGH`)
- P0W → `H1`, P0B → `H1`
- P1A → R_W12 (→ `V_HIGH`)
- P1W → `H2`, P1B → `H2`
- CS → `CS_POT6`

**U12 (MCP4251 #7) — W13: H1→YP, W14: H1→YN**
- P0A → R_W13 (→ `H1`)
- P0W → `YP`, P0B → `YP`
- P1A → R_W14 (→ `H1`)
- P1W → `YN`, P1B → `YN`
- CS → `CS_POT7`

**U13 (MCP4251 #8) — W15: H2→YP, W16: H2→YN**
- P0A → R_W15 (→ `H2`)
- P0W → `YP`, P0B → `YP`
- P1A → R_W16 (→ `H2`)
- P1W → `YN`, P1B → `YN`
- CS → `CS_POT8`

## Complete Weight Path Diagram

Each weight path looks like this:
```
Input Node ─── 1.21kΩ (R_Wn) ─── PxA ─┤ MCP4251 ├─ PxW ─── Output Node
                                       └─ PxB ───┘         (tied to PxW)
```

## Signal Flow Summary

```
Input layer (6 nodes)           Hidden layer (2 nodes)      Output layer (2 nodes)

X1 ─────── R_W1 ── pot ──┐
X1_COMP ── R_W3 ── pot ──┤
X2 ─────── R_W5 ── pot ──┤
X2_COMP ── R_W7 ── pot ──┼── H1 ── R_W13 ─ pot ──┬── YP
V_LOW ──── R_W9 ── pot ──┤       ── R_W14 ─ pot ──┼── YN
V_HIGH ─── R_W11 ─ pot ──┘                        │
                                                   │
X1 ─────── R_W2 ── pot ──┐                        │
X1_COMP ── R_W4 ── pot ──┤                        │
X2 ─────── R_W6 ── pot ──┤                        │
X2_COMP ── R_W8 ── pot ──┼── H2 ── R_W15 ─ pot ──┤
V_LOW ──── R_W10 ─ pot ──┤       ── R_W16 ─ pot ──┘
V_HIGH ─── R_W12 ─ pot ──┘
```

6 input nodes each connect to both H1 and H2 (12 first-layer weights).
H1 connects to YP (W13) and YN (W14). H2 connects to YP (W15) and YN (W16).

## Decoupling

Each MCP4251 gets a 100nF ceramic capacitor from VDD to GND, close to IC.
That's 8x 100nF caps: C_U6 through C_U13.

## CS Pull-Ups

The 9x 10kΩ pull-up resistors from Section 2 connect the CS nets to `+5V`.
They are listed in the Arduino section but physically should be placed near the
MCP4251 chips on the PCB (or near the Arduino — either works, near Arduino is cleaner).
