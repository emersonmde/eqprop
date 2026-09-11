# Revision B: nudge system

Use the native hierarchical schematic. Older wiring instructions do not apply to this revision. See [design](../design.md) and [bring-up](../bring-up.md).

| Reference | Value / MPN | Pin-to-net map |
|---|---|---|
| R_H1 | 1M / TNPW08051M00BEEA | 1=DAC_OUTA, 2=U15A_P |
| R_H6 | 10k / TNPW080510K0BEEA | 1=V_MID_PUMP, 2=U15B_N |
| R_H5 | 1M / TNPW08051M00BEEA | 1=DAC_OUTB, 2=U15B_P |
| R15 | 10k / CRCW080510K0FKEA | 1=+5V, 2=CS_DAC |
| R_H3 | 20k / TNPW080520K0BEEA | 1=R_H3_1, 2=U15A_N |
| U15 | TLV9062IDR / TLV9062IDR | 1=R_H3_1, 2=U15A_N, 3=U15A_P, 4=GND, 5=U15B_P, 6=U15B_N, 7=R_H7_1, 8=+5V |
| R_H4 | 1M / TNPW08051M00BEEA | 1=R_H3_1, 2=YP |
| C15 | 100nF / C0805C104K5RACTU | 1=+5V, 2=GND |
| C14 | 100nF / C0805C104K5RACTU | 1=+5V, 2=GND |
| R_H2 | 10k / TNPW080510K0BEEA | 1=V_MID_PUMP, 2=U15A_N |
| R_H7 | 20k / TNPW080520K0BEEA | 1=R_H7_1, 2=U15B_N |
| U14 | MCP4822-E/SN / MCP4822-E/SN | 1=+5V, 2=CS_DAC, 3=SPI_SCK, 4=SPI_MOSI, 5=GND, 6=DAC_OUTB, 7=GND, 8=DAC_OUTA |
| R_SET_B1 | 1M / TNPW08051M00BEEA | 1=YN, 2=U15B_P |
| R_SET_A1 | 1M / TNPW08051M00BEEA | 1=U15A_P, 2=YP |
| R_H8 | 1M / TNPW08051M00BEEA | 1=R_H7_1, 2=YN |
| C16 | 100nF / C0805C104K5RACTU | 1=+5V, 2=GND |
