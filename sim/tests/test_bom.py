"""Assembly release must order every fitted part exactly once."""
import csv
import json
from pathlib import Path
import pytest

ROOT = Path(__file__).resolve().parents[2]


@pytest.mark.parametrize('name', ['bom-pcbway.csv'])
def test_bom_matches_fitted_manifest(name):
    manifest = json.loads((ROOT / 'cad/eqprop-xor/design-manifest.json').read_text())
    expected = {ref: a for ref, a in manifest.items() if not ref.startswith('TP')}
    seen = []
    for row in csv.DictReader((ROOT / 'docs' / name).open()):
        refs = [s.strip() for s in row['References'].split(',')]
        assert len(refs) == int(row['Quantity'])
        for ref in refs:
            assert ref in expected
            a = expected[ref]
            assert row['Manufacturer part number'] == a['mpn']
            assert row['Footprint'] == a['fp']
            assert row['Value'] == a['value']
            assert row['Assembly notes'] == a['assembly_notes']
        seen.extend(refs)
    assert len(seen) == len(set(seen)), 'Duplicate component reference in BOM'
    assert set(seen) == set(expected)
