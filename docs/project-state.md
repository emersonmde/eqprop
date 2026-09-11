# Session handoff — B.1

Last updated: 2026-09-10. Read this before resuming fabrication, firmware, debugging or demonstrations.

## Current state

| Stage | Status |
|---|---|
| Electrical design and PCB | B.1 routed, 106 × 88 mm, two layers; reviewed SMD analog design with local libraries and custom rules. |
| Verification | 47 regression tests pass with ngspice available; KiCad ERC/DRC and schematic parity clean; 500 connected pins checked against manifest. Evidence under validation/. |
| Manufacturing | Preferred parts selected; 131 fitted parts (124 SMD, seven THT), 16 copper test points and four mounting holes. No PCBWay upload/order/payment is recorded. Sourcing, substitutions and DFM are unconfirmed. |
| Firmware | No Nano firmware source or verified flashing procedure exists yet. Python training is the reference algorithm, not MCU firmware. |
| Physical hardware | Not received or tested. No measured calibration, power budget, stability, settling or real learning results. |

The user selected black solder mask, white silkscreen and ENIG, with 1.6 mm FR-4 and 1 oz copper. Last discussed quantity was five PCBs with two assembled; reconfirm quantities and current pricing at checkout. The prior browser login/quote is not durable project state.

## Resume by stage

1. **Fabrication:** follow fabrication.md. Generate a fresh package locally, check its logs and hashes, review PCBWay's sourcing and placement preview, then obtain order approval. Do not upload an old chat artifact merely because its filename says B.1.
2. **Programming:** follow firmware.md and the native io.kicad_sch. Implement hardware diagnostics first, then calibrated sampling and phase control, then learning and persistence.
3. **Debugging:** follow bring-up.md. Save real observations in `docs/bench/` with board ID, supply, firmware commit, settings, instruments and pass/fail results. Start from power/reference tests before relying on classification.
4. **Demo:** follow operation.md only after startup validity, saved-weight restoration and all XOR patterns have been physically verified.

## Design constraints that must survive context resets

- Six clamped nodes: X1, its complement, X2, its complement, V_LOW and V_HIGH. Two diode nonlinear hidden nodes H1/H2; differential output YP−YN. Target 0 V for 00/11 and +0.3 V for 01/10.
- Sixteen weights use eight MCP4251-104E/SL chips, W tied to B, with 2.49 kohm fixed series resistors. Codes are 0..256 inclusive. Resistance/tap calibration is device dependent.
- TMUX1133 input selection, TLV906x references/measurement buffers, ADS1115 sampling, MCP4822 dual DAC and balanced Howland pumps are the current design. Old CD4053/LM324/MCP600x notes do not describe this board.
- Pump current is `2e-6 * (V_DAC - V_MID_PUMP)` A. Free phase uses calibrated active DAC outputs, not shutdown or a hardcoded 2.500 V. TP5 measures V_MID_PUMP; it is not automatically sampled by the MCU.
- The nominal model uses beta=1e-6 A/V. Firmware must enforce measured DAC/pump compliance and settling. Do not copy obsolete large-beta examples into hardware.
- ADC channels are buffered; the default ±2.048 V PGA setting clips midrail. See bring-up.md for range and sequencing.
- SW3 uses analog-only Nano A6, with an external 2.2 kohm pull-up. Prediction LEDs show class, not training/validity status. Runtime state must be reported over serial.
- Manual input switches are connected through 10 kohm resistors, allowing MCU override for training. Restore high-impedance control for manual operation.
- USB-C supplies nominal 5 V through PTC, reverse blocking and controlled rise time. Use classic 5 V Nano A000005; alternative Nano models/clones are not automatically compatible.

## Evidence limits

The corrected solver checks finite voltages and KCL residuals, retrying stalled solves. Gradient checks cover all four patterns. Training followed by final quantization passes modeled comparator thresholds at 4.4, 4.7 and 5.0 V, with separate training at each supply. This is not validation of online quantized training or supply-invariant stored weights. Diode parameters are nominal assumptions and op-amp models are generic DC approximations.

## Repository map and maintenance

Native CAD and intended component/pin manifest are under cad/eqprop-xor/. docs/design.md contains equations and datasheet links; docs/kicad/ contains convenient pin tables, secondary to the native design. tools/ contains reproducible BOM and manufacturing exports. sim/ and spice/ contain useful models and regressions. build/ is disposable generated output and is not versioned.

Revision A duplicate documents, stale schematic image, redundant BOM alias and duplicate check reports were removed during cleanup. Git retains previously committed history. Do not delete tests merely because they are not firmware: their purpose is detecting circuit/model regressions.

After each stage, update the status table and record exact order ID/release hashes, firmware commit, measurements or operating steps as applicable. Never mark a planned check as passed.
