"""Validate native KiCad design and export a fresh prototype manufacturing set."""
import argparse
import csv
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import xml.etree.ElementTree as ET
import zipfile

from generate_bom import FIELDS, bom_rows, write_bom

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--kicad-cli', default=shutil.which('kicad-cli') or
                        '/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli')
    parser.add_argument('--output', type=Path, default=ROOT / 'build/manufacturing')
    args = parser.parse_args()
    out = args.output.resolve()
    archive = out.parent / 'pcbway-gerbers.zip'
    if out.exists() or archive.exists():
        parser.error('Output directory or Gerber archive already exists; use a fresh destination.')
    subprocess.run([args.kicad_cli, 'version'], check=True, capture_output=True)
    out.mkdir(parents=True)
    cad = ROOT / 'cad/eqprop-xor'
    pcb, sch = str(cad / 'eqprop-xor.kicad_pcb'), str(cad / 'eqprop-xor.kicad_sch')
    manifest = json.loads((cad / 'design-manifest.json').read_text())

    def run(*command):
        result = subprocess.run([args.kicad_cli, *map(str, command)],
                                capture_output=True, text=True)
        with (out / 'export.log').open('a') as log:
            log.write(' '.join(map(str, command)) + '\n' + result.stdout + result.stderr)
        result.check_returncode()

    run('sch', 'erc', '--format', 'json', '-o', out / 'erc.json', sch)
    run('pcb', 'drc', '--format', 'json', '--schematic-parity', '-o', out / 'drc.json', pcb)
    erc = json.loads((out / 'erc.json').read_text())
    drc = json.loads((out / 'drc.json').read_text())
    if any(s['violations'] for s in erc['sheets']) or any(
            drc[k] for k in ['violations', 'unconnected_items', 'schematic_parity']):
        raise RuntimeError('KiCad checks failed; inspect export.log and JSON reports.')
    run('sch', 'export', 'netlist', '--format', 'kicadxml', '-o', out / 'netlist.xml', sch)
    xml = ET.parse(out / 'netlist.xml')
    pins = {(n.get('ref'), n.get('pin')): net.get('name')
            for net in xml.findall('.//nets/net') for n in net.findall('node')}
    expected = {(ref, pin): net for ref, a in manifest.items()
                for pin, net in a['nets'].items() if net}
    # KiCad also exports explicit no-connect pins as singleton nets.
    extras = {key: net for key, net in pins.items() if key not in expected}
    nc_ok = all(manifest.get(ref, {}).get('nets', {}).get(pin) == ''
                and net.startswith('unconnected-')
                and list(pins.values()).count(net) == 1
                for (ref, pin), net in extras.items())
    if not nc_ok or {key: pins.get(key) for key in expected} != expected:
        raise RuntimeError('Exported schematic connections differ from the manifest.')
    components = {c.get('ref'): c for c in xml.findall('.//components/comp')}
    for ref, a in manifest.items():
        c = components[ref]
        fields = {f.get('name'): f.text or '' for f in c.findall('fields/field')}
        if c.findtext('value') != a['value'] or c.findtext('footprint') != a['fp']:
            raise RuntimeError(f'{ref}: schematic value/footprint differs from manifest')
        if not ref.startswith('TP') and fields.get('MPN') != a['mpn']:
            raise RuntimeError(f'{ref}: schematic MPN differs from manifest')
    rows = bom_rows(manifest)
    with (ROOT / 'docs/bom-pcbway.csv').open(newline='') as f:
        saved = list(csv.DictReader(f))
    if saved != [{k: str(v) for k, v in row.items()} for row in rows]:
        raise RuntimeError('Source BOM is stale: run tools/generate_bom.py')
    groups = {}
    for row in rows:
        key = tuple(row[k] for k in FIELDS[2:])
        if key not in groups:
            groups[key] = row.copy()
        else:
            groups[key]['References'] += ', ' + row['References']
            groups[key]['Quantity'] += 1
    write_bom(out / 'bom-pcbway.csv', groups.values())
    run('pcb', 'export', 'gerbers', '--layers',
        'F.Cu,B.Cu,F.Paste,B.Paste,F.Silkscreen,B.Silkscreen,F.Mask,B.Mask,Edge.Cuts',
        '--subtract-soldermask', '-o', str(out / 'gerbers') + '/', pcb)
    run('pcb', 'export', 'drill', '-o', str(out / 'gerbers') + '/', pcb)
    run('pcb', 'export', 'pos', '--format', 'csv', '--units', 'mm', '--smd-only',
        '--exclude-dnp', '-o', out / 'positions-smd.csv', pcb)
    with (out / 'positions-smd.csv').open(newline='') as f:
        positions = list(csv.DictReader(f))
    fitted = {row['References'] for row in rows}
    if len(positions) != 124 or not {p['Ref'] for p in positions} <= fitted:
        raise RuntimeError('Unexpected SMD population; review B.1 release counts.')
    through_hole = {'U3', 'SW1', 'SW2', 'D_GRN1', 'D_GRN2', 'D_PWR1', 'J1'}
    if ({p['Ref'] for p in positions} != fitted - through_hole
            or any(p['Side'] != 'top' for p in positions)):
        raise RuntimeError('SMD/THT population or placement side differs from B.1.')
    if len(fitted) != 131 or len({p['Ref'] for p in positions}) != 124:
        raise RuntimeError('Unexpected or duplicate B.1 component population.')
    run('sch', 'export', 'pdf', '-o', out / 'schematic.pdf', sch)
    for side, layers in [('top', 'F.Fab,F.Silkscreen,Edge.Cuts'),
                         ('bottom', 'B.Silkscreen,Edge.Cuts')]:
        run('pcb', 'export', 'svg', '--layers', layers, '--mode-single',
            '--fit-page-to-board', '--exclude-drawing-sheet',
            *(['--mirror'] if side == 'bottom' else ['--sketch-pads-on-fab-layers']),
            '-o', out / f'assembly-{side}.svg', pcb)
    (out / 'README.md').write_text(
        '# B.1 prototype manufacturing export\n\n'
        '106 x 88 mm; 2 layers; FR-4 1.6 mm; 1 oz; black mask; white silk; ENIG.\n'
        '131 fitted components: 124 top SMD, 7 THT. Global origin, millimeters.\n'
        'SW3 is not washable; confirm assembly cleaning/installation sequence.\n'
        'Confirm Nano/header handling, sourcing, DFM and placement/polarity preview.\n'
        'Upload only the adjacent pcbway-gerbers.zip for the bare PCB quote.\n'
        'BOM, positions and drawings are for assembly. No order is implied.\n')
    hashes = {str(p.relative_to(cad)): hashlib.sha256(p.read_bytes()).hexdigest()
              for p in cad.rglob('*') if p.is_file() and
              (p.suffix in ['.kicad_sch', '.kicad_pcb', '.kicad_pro', '.kicad_dru',
                            '.kicad_sym', '.kicad_mod', '.json'] or p.name.endswith('lib-table'))
              and '-backups' not in str(p) and not p.name.startswith('_autosave-')}
    (out / 'source-hashes.json').write_text(json.dumps(hashes, indent=2) + '\n')
    (out / 'validation-summary.json').write_text(json.dumps({
        'connected_pins': len(expected), 'fitted_parts': len(fitted),
        'smd_positions': len(positions), 'erc_drc_parity_clean': True}, indent=2) + '\n')
    with zipfile.ZipFile(archive, 'w', zipfile.ZIP_DEFLATED) as z:
        for p in sorted((out / 'gerbers').iterdir()):
            if p.is_file():
                z.write(p, p.name)
    with zipfile.ZipFile(archive) as z:
        if z.testzip() is not None:
            raise RuntimeError('Gerber archive failed integrity check')
    (out / 'SHA256SUMS.txt').write_text(''.join(
        hashlib.sha256(p.read_bytes()).hexdigest() + '  ' + str(p.relative_to(out)) + '\n'
        for p in sorted(out.rglob('*')) if p.is_file() and p.name != 'SHA256SUMS.txt'))
    with (out / 'SHA256SUMS.txt').open('a') as f:
        f.write(hashlib.sha256(archive.read_bytes()).hexdigest() + '  ../pcbway-gerbers.zip\n')
    print(f'Validated B.1 export: {out}\nBare-PCB archive: {archive}')


if __name__ == '__main__':
    main()
