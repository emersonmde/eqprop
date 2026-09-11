# Revision B: measurement output

Use the native hierarchical schematic. Older wiring instructions do not apply to this revision. See [design](../design.md) and [bring-up](../bring-up.md).

| Reference | Value / MPN | Pin-to-net map |
|---|---|---|
| TP3 | TestPoint / PCB copper feature (no component) | 1=V_MID_H1 |
| TP1 | TestPoint / PCB copper feature (no component) | 1=V_LOW |
| R_LED_G1 | 2.2k / CRCW08052K20FKEA | 1=D_GRN1_A, 2=+5V |
| TP11 | TestPoint / PCB copper feature (no component) | 1=YN |
| TP9 | TestPoint / PCB copper feature (no component) | 1=DAC_OUTB |
| C17 | 100nF / C0805C104K5RACTU | 1=+5V, 2=GND |
| R20 | 4.7k / CRCW08054K70FKEA | 1=+5V, 2=I2C_SDA |
| TP10 | TestPoint / PCB copper feature (no component) | 1=YP |
| C11 | 1nF / C0805C102J5GACTU | 1=H2_ADC, 2=GND |
| C10 | 1nF / C0805C102J5GACTU | 1=H1_ADC, 2=GND |
| TP8 | TestPoint / PCB copper feature (no component) | 1=DAC_OUTA |
| TP6 | TestPoint / PCB copper feature (no component) | 1=H1 |
| C7 | 100nF / C0805C104K5RACTU | 1=+5V, 2=GND |
| C5 | 100nF / C0805C104K5RACTU | 1=+5V, 2=GND |
| R_LED_R1 | 2.2k / CRCW08052K20FKEA | 1=D_GRN2_A, 2=+5V |
| TP5 | TestPoint / PCB copper feature (no component) | 1=V_MID_PUMP |
| U16 | ADS1115IDGSR / ADS1115IDGSR | 1=GND, 3=GND, 4=H1_ADC, 5=H2_ADC, 6=YP_ADC, 7=YN_ADC, 8=+5V, 9=I2C_SDA, 10=I2C_SCL |
| R21 | 4.7k / CRCW08054K70FKEA | 1=+5V, 2=I2C_SCL |
| TP7 | TestPoint / PCB copper feature (no component) | 1=H2 |
| TP4 | TestPoint / PCB copper feature (no component) | 1=V_MID_H2 |
| TP2 | TestPoint / PCB copper feature (no component) | 1=V_HIGH |
| U17 | TLV9064IDR / TLV9064IDR | 1=H1_BUF, 2=H1_BUF, 3=H1, 4=+5V, 5=H2, 6=H2_BUF, 7=H2_BUF, 8=YP_BUF, 9=YP_BUF, 10=YP, 11=GND, 12=YN, 13=YN_BUF, 14=YN_BUF |
| R_ADC1 | 100 / CRCW0805100RFKEA | 1=H1_BUF, 2=H1_ADC |
| R_ADC2 | 100 / CRCW0805100RFKEA | 1=H2_BUF, 2=H2_ADC |
| R_ADC3 | 100 / CRCW0805100RFKEA | 1=YP_BUF, 2=YP_ADC |
| C27 | 1nF / C0805C102J5GACTU | 1=YP_ADC, 2=GND |
| R_ADC4 | 100 / CRCW0805100RFKEA | 1=YN_BUF, 2=YN_ADC |
| C28 | 1nF / C0805C102J5GACTU | 1=YN_ADC, 2=GND |
| R_D1 | 100k / TNPW0805100KBEEA | 1=YP_BUF, 2=PRED_PLUS |
| R_D2 | 100k / TNPW0805100KBEEA | 1=V_MID_PUMP, 2=PRED_PLUS |
| R_D3 | 100k / TNPW0805100KBEEA | 1=YN_BUF, 2=PRED_MINUS |
| R_D4 | 100k / TNPW0805100KBEEA | 1=PRED, 2=PRED_MINUS |
| R_TH1 | 4.99k / TNPW08054K99BEEA | 1=+5V, 2=THRESHOLD |
| R_TH2 | 5.62k / TNPW08055K62BEEA | 1=THRESHOLD, 2=GND |
| U18 | TLV3202AIDR / TLV3202AIDR | 1=D_GRN1_K, 2=PRED, 3=THRESHOLD_HYS, 4=GND, 5=V_MID_PUMP, 6=D_GRN1_K, 7=D_GRN2_K, 8=+5V |
| TP12 | TestPoint / PCB copper feature (no component) | 1=GND |
| TP13 | TestPoint / PCB copper feature (no component) | 1=+5V |
| TP14 | TestPoint / PCB copper feature (no component) | 1=GND |
| TP15 | TestPoint / PCB copper feature (no component) | 1=PRED |
| TP16 | TestPoint / PCB copper feature (no component) | 1=THRESHOLD |
| R_HYS1 | 10k / CRCW080510K0FKEA | 1=THRESHOLD, 2=THRESHOLD_HYS |
| R_HYS2 | 2M / CRCW08052M00FKEA | 1=D_GRN1_K, 2=THRESHOLD_HYS |
| C31 | 100nF / C0805C104K5RACTU | 1=THRESHOLD, 2=GND |
