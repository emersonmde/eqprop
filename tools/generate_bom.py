"""Generate BOMs from the reviewed manifest, including assembly instructions.

Run from any directory. Optional --manufacturing-dir writes a grouped BOM.
Resistor MPN decoding: Vishay datasheets 20035 and 28758 (links in manifest).
"""
import argparse
import csv
import json
from pathlib import Path

FIELDS = ['References', 'Quantity', 'Value', 'Footprint', 'Manufacturer part number',
          'Tolerance / rating', 'Datasheet', 'Assembly notes']


def bom_rows(manifest):
    return [dict(zip(FIELDS, [ref, 1, a['value'], a['fp'], a['mpn'],
            '; '.join(dict.fromkeys(v for v in [a.get('tolerance', ''),
                                               a.get('rating', '')] if v)),
            a['datasheet'], a['assembly_notes']]))
            for ref, a in sorted(manifest.items()) if not ref.startswith('TP')]


def write_bom(path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('w', newline='') as f:
        writer = csv.DictWriter(f, FIELDS, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--manufacturing-dir', type=Path)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    manifest = json.loads((root / 'cad/eqprop-xor/design-manifest.json').read_text())
    rows = bom_rows(manifest)
    for name in ['bom-pcbway.csv']:
        write_bom(root / 'docs' / name, rows)
    if args.manufacturing_dir:
        groups = {}
        for row in rows:
            key = tuple(row[k] for k in FIELDS[2:])
            if key not in groups:
                groups[key] = row.copy()
            else:
                groups[key]['References'] += ', ' + row['References']
                groups[key]['Quantity'] += 1
        write_bom(args.manufacturing_dir / 'bom-pcbway.csv', groups.values())


if __name__ == '__main__':
    main()
