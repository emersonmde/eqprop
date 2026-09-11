# PCBWay prototype fabrication and assembly

## Generate a package from this repository

Run the simulation suite from README.md, then `python tools/export_manufacturing.py`. It runs KiCad ERC/DRC/parity, checks the exported netlist and BOM/placement population against the manifest, and creates `build/manufacturing/` plus `build/pcbway-gerbers.zip`. The directory contains Gerbers/drill, grouped BOM, top SMD positions, schematic PDF, assembly drawings, check reports and hashes. It must be regenerated after design changes. Source BOM updates use `python tools/generate_bom.py`.

The script refuses an existing destination to prevent mixing releases. Move a package you need to retain elsewhere, or explicitly remove disposable build output before exporting again. When ordering, retain the exact uploaded package and hash list with the order record; do not silently regenerate it under the same order.

## Quote settings and upload sequence

Use the following reviewed preferences; verify actual available options and prices on PCBWay when quoting:

| Setting | Intended selection |
|---|---|
| Board | 106 × 88 mm; two layers |
| Material / thickness | FR-4, 1.6 mm |
| Copper | 1 oz |
| Solder mask | Black, both sides |
| Silkscreen | White, both sides |
| Finish | ENIG |
| Quantity | Last discussed: five boards, two assembled; confirm at order |
| Assembly | Turnkey preferred, including seven through-hole components |

Upload `pcbway-gerbers.zip` to the PCB fabrication quote, not the full source repository. For assembly provide the grouped BOM, positions-smd.csv, assembly-top.svg and schematic.pdf. The bottom guide drawing helps confirm the back silkscreen. Positions are in millimeters using the same KiCad global origin as fabrication exports; all 124 SMD parts are on top.

Review PCBWay's inferred size, layers, holes and silkscreen. Compare its placement/polarity preview with the assembly drawing, particularly IC pin 1, diodes/LEDs, USB connector and Nano orientation. The BOM has exact preferred MPNs, not confirmed stock. Review every substitution and update CAD/manifest/BOM together if accepted.

## Assembly questions to resolve

- B3U-1000P SW3 is not washable: confirm a compatible process or installation after wet cleaning.
- Confirm the classic 5 V A000005 Nano/module and its header supply/installation; do not substitute another Nano family member.
- Confirm assembly of the anchored USB connector, slide switches, LEDs and module in the through-hole operation.
- Retain precision resistor tolerances, mux/op-amp selection, Schottky diode technology and specified footprints.
- Confirm DFM exceptions are limited to the reviewed connector land pattern; do not approve global clearance reductions.

No order is placed yet. Review final sourcing, DFM, quantities, shipping and total price before authorizing payment/order. After ordering, add an order record under docs/bench/ with order ID, date, board revision, Git commit and uploaded file hashes. Current website behavior/pricing must be checked live.
