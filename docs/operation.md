# Using the board as a learning demo

This procedure describes the intended interface. It becomes usable only after firmware and bring-up acceptance are complete; there is currently no ready-to-flash demo image.

1. Connect power and serial diagnostics. Wait for firmware to report calibrated initialization and either restored weights or an untrained state. POWER confirms the rail is present, not successful initialization.
2. In manual mode, set the two switches labeled INPUT X1 and INPUT X2. Verify their printed 0/1 positions during first bring-up.
3. Read the PREDICTION LEDs: D_GRN2 represents class 0 and D_GRN1 class 1. These are analog comparator outputs and can show a class before weights or calibration are valid. They do not identify training mode.
4. With trained/restored weights, check 00→0, 01→1, 10→1 and 11→0. Record the measured YP−YN as well as the LED class when debugging marginal results.
5. LEARN/STOP requests training or a phase-boundary stop once the firmware implements it. Training temporarily overrides input switches. After stopping, the firmware restores free-phase DAC commands and manual input control while retaining weights.
6. Save trained weights using the eventual documented firmware command before removing power; digital pots are volatile. Power-cycle and verify restoration before handing the demo to someone else.

The back-side guide summarizes complementary inputs, hidden nodes, differential output and free/nudged learning. Reference designators and test points remain useful for tracing the full schematic. For unexpected behavior, return to bring-up.md: check supply/reference levels, DAC free-phase residual, ADC range/settling, tap readback and input encoding before changing learning parameters.
