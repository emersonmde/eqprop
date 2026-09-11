# Revision B.1: small demo-interface improvements

This supersedes B for fabrication. The board remains 106 x 88 mm, two layers, 1.6 mm FR-4 and 1 oz copper. Finish preference: black solder mask both sides, white silkscreen both sides, ENIG. The 3D render uses generic red LED models; the BOM still specifies green LEDs. Nano and slide-switch models are absent, so render imagery is not a complete mechanical assembly model.

## Changes

- Existing prediction LEDs now share an X coordinate beside the input switches. D_GRN2 indicates 0; D_GRN1 indicates 1. One series resistor moved locally to maintain courtyard clearance. Only the affected terminal routes were modified; the analog ICs and power entry stayed in place.
- INPUT X1 / INPUT X2, switch-state marks, PREDICTION, POWER and LEARN / STOP clarify the controls. Component references and debug net labels remain. Verify switch continuity against the printed states during first bring-up before applying automated input drive.
- Back-side guide shows complementary inputs, hidden nodes H1/H2, differential output YP/YN, bidirectional resistive coupling, the free/nudged comparison and XOR truth table. It is a functional guide, not a replacement for the full schematic.
- SW3 is a normally-open B3U-1000P momentary switch from LEARN_BUTTON to GND. Nano A6 (module pad 25) reads it. R_BUTTON1, 2.2k 1%, pulls the input to +5V. The resistor reuses the existing LED resistor MPN. Pressed current is approximately 2.3 mA at nominal 5 V; the unpressed input consumes no intentional DC current.
- A6 is analog-only on the classic Nano. This avoids UART sharing and changes to the existing SPI/I2C allocation. A separate MCU-driven status LED was omitted because no general-purpose digital output is free without sharing an existing function.

## Firmware contract — not implemented in this hardware revision

Read A6 with analogRead using the supply-referenced ADC setting. Use thresholds comfortably separated from midscale (for example below one-quarter full scale = pressed, above three-quarters = released); ignore intermediate samples. These thresholds are chosen margins for a rail-to-rail contact input, not precision voltage measurements. Debounce in software: require a stable state for 20 ms (engineering margin over the switch's specified 5 ms maximum bounce). Require release before accepting another press; a held button at boot must not repeatedly start training.

A press requests start/stop, processed only between completed free/nudged measurement pairs. On stop, return both DACs to calibrated free-phase commands before returning input control to the switches. Do not erase learned weights. Preserve programming/serial access. Report the mode and progress over serial; the prediction LEDs do not indicate training status. Save/restore weights and clear startup validity must be implemented in the eventual demo firmware. No complete MCU training firmware exists in this package.

Poll the button outside sensitive equilibrium-sampling windows. Test held-at-boot, contact bounce, repeated presses and stop during training. Confirm analog settling and classification with the button pressed/released as part of prototype validation.

## Assembly note

B3U-1000P is not washable. PCBWay must confirm a compatible no-clean assembly process or fit SW3 after wet cleaning. Do not approve a substitute without checking footprint, height, actuation and contact ratings. Counts per board: 124 SMD parts, 7 through-hole parts, 16 copper test points and 4 mounting holes (151 footprints total).

## Sources

- [Arduino classic Nano pinout](https://docs.arduino.cc/resources/pinouts/A000005-full-pinout.pdf): A6 is ADC6; no digital GPIO assignment.
- [Omron B3U datasheet](https://omronfs.omron.com/en_US/ecb/products/pdf/en-b3u.pdf): B3U-1000P top actuation, land pattern, normally-open contact, 5 ms maximum bounce, and non-washable construction.
- [Vishay CRCW datasheet](https://www.vishay.com/docs/20035/dcrcwe3.pdf): resistor series used for the pull-up, matching the existing 2.2k MPN.
