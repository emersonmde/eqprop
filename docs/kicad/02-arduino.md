# Revision B.1: arduino

Use the native hierarchical schematic. Older wiring instructions do not apply to this revision. See [design](../design.md) and [bring-up](../bring-up.md).

| Reference | Value / MPN | Pin-to-net map |
|---|---|---|
| D_GRN1 | Green low-current 3mm / WP710A10LZGCK | 1=D_GRN1_K, 2=D_GRN1_A |
| R_SW1 | 10k / CRCW080510K0FKEA | 1=MUX_A, 2=SW1_B |
| R_SW2 | 10k / CRCW080510K0FKEA | 1=MUX_B, 2=SW2_B |
| SW1 | SW_SPDT / EG1271A | 1=+5V, 2=SW1_B, 3=GND |
| D_GRN2 | Green low-current 3mm / WP710A10LZGCK | 1=D_GRN2_K, 2=D_GRN2_A |
| U3 | Arduino_Nano_v3.x / A000005 | 4=GND, 5=MUX_A, 6=MUX_B, 7=CS_POT1, 8=CS_POT2, 9=CS_POT3, 10=CS_POT4, 11=CS_POT5, 12=CS_DAC, 13=CS_POT6, 14=SPI_MOSI, 15=SPI_MISO, 16=SPI_SCK, 19=X1, 20=X2, 21=CS_POT7, 22=CS_POT8, 23=I2C_SDA, 24=I2C_SCL, 25=LEARN_BUTTON, 27=+5V, 29=GND |
| SW2 | SW_SPDT / EG1271A | 1=+5V, 2=SW2_B, 3=GND |
| D_PWR1 | Green low-current 3mm / WP710A10LZGCK | 1=GND, 2=D_PWR1_A |

| SW3 | LEARN / STOP / B3U-1000P | 1=LEARN_BUTTON, 2=GND |
| R_BUTTON1 | 2.2k / CRCW08052K20FKEA | 1=+5V, 2=LEARN_BUTTON |

A6 is analog-only. See [button firmware contract](../usability-revision.md).
