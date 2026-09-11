# Classic Nano firmware contract — implementation pending

No Arduino sketch, compiled image or tested flashing command is supplied yet. Start with diagnostics; confirm the installed Nano and bootloader through the programming tool before selecting a target or upload settings. The native schematic and component manifest are authoritative for physical pin numbers.

## Arduino signal map

| Arduino pin | Board function |
|---|---|
| D0 / D1 | UART RX / TX; reserve for programming and serial diagnostics |
| D2 / D3 | MUX_A / MUX_B; input for manual switches, output for training override |
| D4, D5, D6, D7, D8 | CS_POT1 through CS_POT5 |
| D9 | CS_DAC |
| D10 | CS_POT6; keep configured as inactive-high output when SPI master is used |
| D11 / D12 / D13 | MOSI / MISO / SCK |
| A0 / A1 | X1 / X2 analog observation |
| A2 / A3 | CS_POT7 / CS_POT8 |
| A4 / A5 | I2C SDA / SCL |
| A6 | LEARN_BUTTON, active low, external pull-up; analog read only |
| A7 | Unconnected |

ADS1115 ADDR is grounded; channels AIN0..3 measure buffered H1, H2, YP, YN. Confirm protocol addresses, register masks and SPI timing from the manufacturer datasheets linked in design.md before implementing drivers. MCP4251 commands must preserve the ninth data bit for tap 256. Read back taps and verify device/channel-to-weight mapping from the manifest, not just chip enumeration.

## Implementation milestones

1. **Diagnostic firmware:** report identity/version over serial; exercise chip-selects and pot readback; configure ADC and read all channels; command both DAC channels using measured calibration. Check manual-input encoding. Keep CS high before enabling SPI and do not report valid predictions during initialization.
2. **Measurement engine:** implement the startup, active zero-current commands, compliance bounds, sequential DAC update handling, ADC scan and measured settling requirements in bring-up.md. No SPI writes during equilibrium sampling. Record raw ADC codes and calibrated voltages.
3. **Training engine:** port the mathematical convention from sim/eqprop/training.py. Weights are stored as resistance; gradients and updates use conductance. The reference uses free and symmetric nudged equilibria; maintain input and weight state across the complete phase group. Bound nudge commands, reject clipping/unsettled samples and accumulate sub-tap updates before quantizing.
4. **Control and persistence:** use the SW3 debounce/release rules in usability-revision.md. Stop only at phase boundaries, restore calibrated free phase and return switches to manual control. Preserve learned weights on stop. Add explicit save/restore with version/checksum and avoid writing nonvolatile memory on every update. Report mode, validity, errors and progress over serial.
5. **Acceptance:** test tap endpoints and channel map, startup/reset, held button, repeated presses, stop during learning, missing peripherals, power-cycle restore and all four XOR patterns. Compare raw measurements against simulation using actual calibrated tap values. Add firmware tests alongside the implemented code; do not claim completion from this contract.

Keep the first implementation small and observable. Define firmware source/build instructions when a toolchain is selected; no invented build layout or untested upload command is required in advance.
