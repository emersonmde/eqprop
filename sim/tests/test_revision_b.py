"""SPICE regression for both pumps, using actual KiCad revision component values."""
import json, itertools
from pathlib import Path
import pytest
from eqprop.spice import run_ngspice, ngspice_available

@pytest.mark.skipif(not ngspice_available(), reason="ngspice required")
def test_pump_current_is_independent_of_load_voltage():
    j=json.loads((Path(__file__).resolve().parents[2] / 'cad/eqprop-xor/design-manifest.json').read_text())
    def value(s):
     for suffix,mult in [('M',1e6),('k',1e3)]:
      if s.endswith(suffix):return float(s[:-1])*mult
     return float(s)
    rows=[]
    for channel,refs,pins,load,dac in [('A',['R_H1','R_H2','R_H3','R_H4','R_SET_A1'],['3','2','1'],'YP','DAC_OUTA'),('B',['R_H5','R_H6','R_H7','R_H8','R_SET_B1'],['5','6','7'],'YN','DAC_OUTB')]:
     names={n:f'n{i}' for i,n in enumerate(sorted({n for r in refs for n in j[r]['nets'].values()}))}
     for vd,vl in itertools.product([2,2.5,3],[2.2,2.5,2.8]):
      lines=['* Revision B pump circuit from schematic manifest']
      lines += [f'V_DAC {names[dac]} 0 {vd}',f'V_REF {names["V_MID_PUMP"]} 0 2.5',f'V_LOAD {names[load]} 0 {vl}']
      for r in refs:lines.append(f'{r} {names[j[r]["nets"]["1"]]} {names[j[r]["nets"]["2"]]} {value(j[r]["value"])}')
      vp,vm,vo=[names[j['U15']['nets'][p]] for p in pins]
      lines += [f'EAMP {vo} 0 {vp} {vm} 100000','.op',f'.save i(V_LOAD) v({vo})','.end']
      result=run_ngspice('\n'.join(lines));assert result is not None
      current=result['i(v_load)'];expected=2e-6*(vd-2.5);assert abs(current-expected)<1e-9
      assert .15<result[f'v({vo})']<4.85
      rows.append(dict(channel=channel,dac=vd,load=vl,current_uA=current*1e6,expected_uA=expected*1e6,amp_output=result[f'v({vo})']))
