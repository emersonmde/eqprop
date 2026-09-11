# EqProp XOR — revision B.1 engineering review

The revised **prototype** is routed and passes the automated electrical/design-rule checks. The original routed board was not functionally ready: the mux pin assignments and nudge-current circuit required correction. This revision is saved without a Git commit.

## B.1 usability update

See [usability revision](usability-revision.md). Adds SW3 on Nano A6 and R_BUTTON1, aligns the prediction LEDs, moves one LED resistor locally, adds operating labels and a back-side circuit guide, and records black mask / white silk / ENIG. The original analog topology and component values are unchanged.

## Changes resolved

| Area | Finding and resolution |
|---|---|
| Input selection | Corrected control/common pin interchange on U4/U5; changed to TMUX1133PWR with substantially lower switch resistance. |
| Nudge current | Rebalanced the five-resistor Howland topology to 2 uA/V. Verified both channels against SPICE using the actual component/pin manifest. |
| Analog loading | Replaced bipolar-input amplifiers with TLV906x; added four local measurement buffers and 100 ohm/1 nF ADC isolation filters. |
| Reference stability | Moved large reference capacitors to divider inputs, added local IC bypassing, and used 0.1% reference-divider resistors. |
| Weight protection | Changed all fixed series resistors to 2.49k, 1%; corrected the 257-position digital-pot/wiper model. |
| Output indicator | Added a buffered differential stage and hysteretic comparator around the actual XOR decision boundary. Selected low-current LEDs. |
| USB power | Added a 1206 PTC, LM66100 ideal-diode reverse blocking, TPS22918 controlled startup, and appropriate local capacitance. |
| Physical layout | Replaced DIP packages with SMD ICs/pots, arranged analog sections, routed both layers, stitched ground including previously isolated back-copper regions, added four mounting holes and test/operating labels. |
| Documentation / assembly | Rebuilt the native hierarchy, reconciled every assembly part with its footprint/MPN, updated simulation and firmware interface notes, and archived obsolete construction instructions. |

## Verified results

* KiCad DRC: **0 violations, 0 unrouted connections, 0 schematic/PCB mismatches**.
* KiCad ERC: **0 violations**, without blanket suppression of rule categories.
* Exported schematic netlist: **500 connected pins checked across 147 electrical symbols; 0 mismatches** against the intended manifest.
* Simulation suite: **47 passed**. The pump regression exercises 18 SPICE cases across both channels, DAC=2/2.5/3 V and load=2.2/2.5/2.8 V; current error stays below 1 nA in the finite-gain DC model.
* Analytical pump resistor-corner check: all 32 combinations of five 0.1% resistor extremes were evaluated over the same voltage sweep; worst modeled current error is approximately 2.91 nA.
* Nominal training plus final weight quantization preserves XOR classification at 4.4, 4.7 and 5.0 V in the model, using beta=1e-6 A/V. This is continuous training followed by quantization, not proof of a physical quantized-update training loop.

| Modeled supply | Quantized predictions: 00, 01, 10, 11 (V) |
|---|---|
| 4.4 V | 0.0522, 0.2544, 0.2658, 0.0638 |
| 4.7 V | 0.0492, 0.2480, 0.2616, 0.0632 |
| 5.0 V | 0.0465, 0.2497, 0.2603, 0.0603 |

The board is 106 x 88 mm with two copper layers, 151 footprints (131 populated components, 16 copper test points and four mounting holes), 347 vias including 151 ground vias. The increased via count includes deliberate ground stitching and the added SMD circuitry; this revision does not claim fewer vias than the original board.

## Files and manufacturing settings

Open `cad/eqprop-xor/eqprop-xor.kicad_pro`. Keep its local symbol/footprint libraries and `.kicad_dru` file together. Generate `build/manufacturing/` with `tools/export_manufacturing.py` for Gerbers, Excellon drill, top SMD positions, assembly drawing and schematic PDF. The position file contains 124 SMD parts; seven through-hole items need a separate assembly operation. Coordinates are the matching KiCad global origin in millimeters. Inspect the assembler's imported orientations and polarity marks before accepting its assembly preview.

Use 1.6 mm FR-4, two layers, 1 oz copper, solder mask on both sides, and the provided paste apertures. The reviewed rules use 0.25 mm routing clearance/trace minimum, 0.6/0.3 mm vias and 0.5 mm copper-edge clearance. J1 alone has a documented 0.15 mm internal pad-spacing rule matching its vendor footprint. [PCBWay capabilities](https://www.pcbway.com/capabilities.html)

`bom-pcbway.csv` has exact preferred MPNs; no PCBWay stock or substitution approval is implied. The Nano is the classic 5 V A000005 module. Keep switches, LEDs and the mechanically anchored connector as specified. Through-hole components should be installed after SMD reflow unless the assembler confirms another supported process.

## Interpretation of checks and remaining physical work

**Do not carry the old firmware constants into this board.** The pump transresistance is now 500 kohm, free-phase DAC voltage must track measured V_MID_PUMP, and all current commands need compliance limits. See [bring-up and firmware requirements](bring-up.md).

DC models do not prove amplifier stability, noise, leakage at temperature, startup sequencing, ADC settling, component spread, or learning on physical hardware. The per-branch mux resistance in the Python solver is an approximation; the full analog SPICE generator models shared mux outputs. Its amplifier model is a generic DC approximation, not a validated TLV906x vendor macro-model. The 0.15 V headroom in the bring-up notes is a conservative guard to characterize, not a guaranteed output-swing specification.

Before a larger batch, measure free-phase residual current, pump compliance and polarity, supply startup/backfeed, reference and measurement-buffer stability, conversion settling, and all four trained XOR patterns. PCBWay still needs to confirm part sourcing, module handling, assembly preview and DFM acceptance. No order was placed and no files were sent to PCBWay.

The project-local LM66100 symbol explicitly models the unused status pin as its datasheet-required grounded termination. Its passive pin type avoids a false ERC conflict between an open-drain output and the ground power flag; it must not be reused when ST is used as a logic output. [TI LM66100 pin table](https://www.ti.com/lit/ds/symlink/lm66100.pdf)

## Current handoff

See [project state](project-state.md) for fabrication, firmware and bench work. The pre-commit review fixed duplicate BOM counting, resistor metadata, stalled solver acceptance and schematic readability, and clarified startup/calibration. The later repository cleanup removed duplicate historical documents and added reproducible manufacturing export. Copper and preferred components are unchanged. The old schematic/PCB checks establish only the specific properties listed above; no physical demo performance is claimed.
