# Revision B.1 update

B.1 adds a locally routed learn/stop input on Nano A6 and operating labels; the analog design below remains unchanged. See [usability revision](usability-revision.md).

# EqProp XOR — revision B

Revision B.1 is the current prototype design. The native KiCad hierarchy, PCB and `bom-pcbway.csv` supersede the revision A construction notes retained in Git history. Revision A had functional errors that passing a routing DRC could not detect.

## Signal path

Sixteen MCP4251-104E/SL programmable resistances form a complementary-input, two-hidden-node, differential-output network. TLV9064 buffers generate V_LOW and V_HIGH and separate V_MID returns for the two diode activations and current sources. Two TMUX1133PWR devices select the complementary inputs. Four BAT42W diodes implement the hidden-node nonlinearities. U17 buffers H1, H2, YP and YN before the ADS1115; 100 ohm/1 nF filters isolate its switched-capacitor inputs from the buffers.

## Corrections and component decisions

* U4/U5 select pins are 11=A and 10=B; common analog pins are 14=X1 and 15=X2 (and complementary equivalents). The previous schematic interchanged these groups. TMUX1133 uses the verified compatible pin arrangement with much lower on-resistance than CD4053B. [TI TMUX1133](https://www.ti.com/lit/ds/symlink/tmux1133.pdf)
* U1/U2/U17 use TLV9064IDR and U15 uses TLV9062IDR. CMOS input bias and rail-to-rail operation suit the high-impedance analog network. Input offset, drift and reference errors still require calibration. The 1 uF reference capacitors filter divider inputs; large capacitors no longer directly load buffer outputs. [TI TLV906x](https://www.ti.com/lit/ds/symlink/tlv9064.pdf)
* Each programmable weight has a 2.49 kohm, 1% fixed series resistor. With a 5.5 V maximum rail difference and the resistor at its -1% corner, current is below 2.24 mA even without relying on pot resistance. MCP4251 terminal current is limited to 2.5 mA. The nominal 75 ohm wiper and tied W/B terminals are included in the revised model. Device resistance tolerance means taps must be calibrated if absolute conductance is important. [Microchip DS22060B](https://ww1.microchip.com/downloads/aemDocuments/documents/OTH/ProductDocuments/DataSheets/22060b.pdf)
* ADS1115 inputs now see buffered signals rather than directly loading the learning nodes. Readings still require settling after channel switching and changes to input/weight/DAC settings. [TI ADS1115](https://www.ti.com/lit/ds/symlink/ads1115.pdf)
* Precision dividers, the differential amplifier and pump resistor ratios use 0.1%, 25 ppm/K thin-film resistors. Other resistors use common thick-film parts. Precision MPNs specify lead-free TNPW e3, not the similarly named lead-bearing TNPW series. [Vishay TNPW e3](https://www.vishay.com/docs/28758/tnpw_e3.pdf)

## Balanced nudge sources

Each pump uses Rin=1M from DAC to the positive input, Rpos=1M from positive input to load, Rout=1M from amplifier output to load, Rref=10k from V_MID_PUMP to negative input, and Rfb=20k from output to negative input. All five are 0.1%.

The balance condition is `(Rfb/Rref)*Rin = Rpos + Rout`. Including current through both load-connected resistors gives:

`I_load = 2 uA/V * (V_DAC - V_MID_PUMP)`

The previous 10k/10k/10k/10k/1M arrangement was not balanced and substantially loaded the network in its purported free phase. These are equations for the actual five-resistor topology, not a generic four-resistor current-source formula. [TI AN-1515](https://www.ti.com/lit/an/snoa474a/snoa474a.pdf)

For the balanced circuit, `V_amp = 1.5*(V_DAC + V_load) - 2*V_MID_PUMP`. Firmware must enforce output compliance and the DAC's physical output range. A conservative initial operating region is V_DAC within +/-0.5 V of measured V_MID_PUMP, with node voltages near midrail. Calculate bounds from actual supply and load voltage; do not blindly clamp only to DAC codes. Maintain at least 0.15 V estimated output headroom as a bring-up guard, then characterize the real load-dependent swing.

## Classifier

U1C produces `PRED = V_MID_PUMP + YP_BUF - YN_BUF` using four 100k, 0.1% resistors. U18A compares this against a hysteretic threshold derived from a 4.99k/5.62k divider. U18B inverts its logic to drive the complementary indicator. This gives a nominal midpoint near +0.148 V differential at 5 V supply, appropriate for XOR targets 0 and +0.3 V. A zero-difference comparator was inappropriate for those targets.

The 10k input and 2M feedback resistors give approximately 31 mV DC hysteresis at 5 V **including the divider's Thevenin resistance**. The two nominal differential thresholds are approximately +0.132 V and +0.163 V. Values scale with board supply. C31 filters the divider; this also affects switching transients. LEDs use low-current parts with 2.2k classifier series resistors. [TI TLV3202](https://www.ti.com/lit/ds/symlink/tlv3202.pdf)

## Power and assembly

USB-C is a 5 V power input with separate CC pull-downs. F1 is **MF-NSMF025X-2, 1206**, followed by an LM66100DCKR ideal-diode IC and TPS22918 with 10 nF CT for controlled rise time. QOD is intentionally unconnected because the Nano can power the board through its +5V header. Reverse blocking prevents backfeeding the USB-C connector. The PTC protects against sustained faults; it is not an accurate active current limiter or overvoltage protector. The ideal diode avoids a Schottky forward drop, preserving supply margin. Its CE pin is tied to its output for reverse-current protection, with a local 1 uF input capacitor. The fuse, switches and traces still introduce load-dependent voltage drop: the net named +5V is a nominal rail, not a regulated precision 5.000 V supply. Reference voltages and classifier thresholds are ratiometric. [Bourns MF-NSMF](https://www.bourns.com/docs/product-datasheets/mf-nsmf.pdf), [TI LM66100](https://www.ti.com/lit/ds/symlink/lm66100.pdf), [TI TPS22918](https://www.ti.com/lit/ds/symlink/tps22918.pdf)

Use the classic **5 V Arduino Nano A000005**. Other Nano-family boards and unverified clones are not automatically interchangeable. Its module/header, slide switches, LEDs and mechanically anchored USB connector remain through-hole. Analog ICs, pots, signal diodes, resistors and capacitors use surface-mount packages. The BOM is suitable for requesting a PCBWay assembly quote; stock, substitutions, module handling and assembly cost have not been confirmed by PCBWay. Do not substitute op-amps, muxes, diode technology or precision resistor tolerances without repeating the circuit review.

## Layout

The board remains 106 x 88 mm, two copper layers. Four M3 clearance holes were added. Local IC bypassing, ground pours on both layers, and ground stitching provide short return paths. Routing uses 0.25 mm minimum tracks and 0.25 mm general clearance, with 0.6/0.3 mm vias. Only pad-to-pad clearance inside J1 uses the manufacturer land pattern's 0.15 mm spacing. Board copper-edge clearance remains 0.5 mm. Use 1 oz copper for the reviewed spacing. [PCBWay standard capabilities](https://www.pcbway.com/capabilities.html)

See `ee-review.md`, `bring-up.md`, the test reports and the current KiCad project before fabrication. DC simulations and clean ERC/DRC establish specific checks; they do not establish analog stability, ESD compliance, assembly yield or physical learning performance.
