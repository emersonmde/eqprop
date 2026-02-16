# Section 5: Activation Functions (Diodes)

## Components

| Ref | Component | KiCad Symbol | Notes |
|-----|-----------|-------------|-------|
| D1a | BAT42 (H1 forward) | `Diode:BAT42` | Anode=H1, Cathode=V_MID_H1 |
| D1b | BAT42 (H1 reverse) | `Diode:BAT42` | Anode=V_MID_H1, Cathode=H1 |
| D2a | BAT42 (H2 forward) | `Diode:BAT42` | Anode=H2, Cathode=V_MID_H2 |
| D2b | BAT42 (H2 reverse) | `Diode:BAT42` | Anode=V_MID_H2, Cathode=H2 |

## Antiparallel Wiring

Each hidden node has two BAT42 diodes in **antiparallel** (opposite polarity, in parallel)
connected between the hidden node and its dedicated V_MID rail.

### H1 Diode Pair
```
        D1a (BAT42)
H1 ──►|──── V_MID_H1      (D1a: anode=H1, cathode=V_MID_H1)
H1 ────|◄── V_MID_H1      (D1b: anode=V_MID_H1, cathode=H1)
        D1b (BAT42)
```

In KiCad:
- D1a: pin A (anode) → `H1`, pin K (cathode) → `V_MID_H1`
- D1b: pin A (anode) → `V_MID_H1`, pin K (cathode) → `H1`

### H2 Diode Pair
```
        D2a (BAT42)
H2 ──►|──── V_MID_H2      (D2a: anode=H2, cathode=V_MID_H2)
H2 ────|◄── V_MID_H2      (D2b: anode=V_MID_H2, cathode=H2)
        D2b (BAT42)
```

In KiCad:
- D2a: pin A (anode) → `H2`, pin K (cathode) → `V_MID_H2`
- D2b: pin A (anode) → `V_MID_H2`, pin K (cathode) → `H2`

## Behavior

- When H1 > V_MID_H1 + ~0.3V: D1a conducts, shunting current to V_MID_H1 (clamping)
- When H1 < V_MID_H1 - ~0.3V: D1b conducts, pulling H1 back toward V_MID_H1
- Linear region: ~2.2V to ~2.8V (0.6V window centered on 2.5V)
- Effective saturation: ~2.0V and ~3.0V (accounting for soft turn-on)

## Defensive PCB Features

### Diode Sockets (for swappability)
Use 2-pin female headers or SIP sockets for each diode footprint on the PCB.
This allows hand-swapping BAT42 → 1N4148 if the Schottky activation proves too aggressive.
Both diodes are DO-35 (same package), so they're pin-compatible.

### Optional Series Softening Resistors
Add pads for an optional series resistor in each diode path. Populate with 0Ω jumpers
by default. If activation is too aggressive, replace with 100-500Ω to soften clamping.

In KiCad, add a resistor in series with each diode:

```
H1 ── R_D1a (0Ω) ── D1a anode ── D1a cathode ── V_MID_H1
V_MID_H1 ── D1b anode ── D1b cathode ── R_D1b (0Ω) ── H1
```

| Ref | Value | Purpose |
|-----|-------|---------|
| R_D1a | 0Ω (or 100-500Ω) | Series with D1a |
| R_D1b | 0Ω (or 100-500Ω) | Series with D1b |
| R_D2a | 0Ω (or 100-500Ω) | Series with D2a |
| R_D2b | 0Ω (or 100-500Ω) | Series with D2b |

These add 4 more resistors but give significant debugging flexibility on a first-spin PCB.

## Test Points

Add test points on `H1` and `H2` nets. These are the most important diagnostic points
in the entire network — monitoring hidden node voltages tells you if the diodes are
working correctly, if nodes are saturating, and if the network is differentiating
between input patterns.

## EqProp Validity Note

The antiparallel diode pair is a two-terminal element with a continuous, monotonic,
bidirectional I-V characteristic. This satisfies EqProp's Theorem 2 requirement.
The dedicated V_MID rails (V_MID_H1, V_MID_H2) prevent cross-coupling between
hidden neurons through the diode return path.
