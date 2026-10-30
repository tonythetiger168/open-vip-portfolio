# ipcheck: open-ip-portfolio RTL against independent references

open-ip-portfolio's TV / STB / IP-camera plan
(`docs/TV_STB_IPCAM_IMPROVEMENT_PLAN_2026-10-26.md` there) asks for its
camera, display-path, peripheral and memory IP to be verified by independent
VIPs and public vectors, not by testbenches that share the RTL's own model.
This directory does that for the IPs that exist today. The peripherals are
checked through their APB wrappers, so the documented register map is part
of what is verified:

| IP (open-ip `rtl/`) | Testbench | Expected values come from |
|---|---|---|
| `Crypto___Security_Engine_top.sv` | `crypto_xchk_tb.sv` | Python `hashlib` / `hmac`, FIPS 180-4 examples, RFC 4231 TC1, TC2, TC6 (37 vectors, lengths 0..64 incl. the 55/56/64-byte padding corners) |
| `Ethernet_top.sv` | `eth_xchk_tb.sv` | frames with `zlib.crc32` FCS; padding, inter-frame gap, underrun, DA filter, CRC / length / PHY-error status, VLAN 1522, runts (38 and 63 bytes), PAUSE quanta |
| `CSI_2_top.sv` | `csi2_xchk_tb.sv` | packets with ECC from the CSI-2 parity equations and CRC-16 anchored to the specification's checksum examples; single-bit correction (data and ECC bits), double-bit drop, CRC error, burst cut, virtual channels, line longer than the buffer |
| `HDMI_2_1_top.sv` | `hdmi_xchk_tb.sv` | a TMDS sink: every character re-encoded with the DVI 1.0 algorithm, control / guard / TERC4 tables, VIC 1 timing, the R=x G=y B=x^y source, InfoFrames with BCH ECC and checksums computed by the runner |
| `UART_apb.sv` + `UART_top.sv` | `uart_xchk_tb.sv` | the register map in open-ip `docs/ip/UART.md`; an 8N1 line receiver sampling bit centres at the nominal baud and timing every edge (2 % limit), a line driver at -2.5 .. +2.5 % baud, back-to-back frames, framing error, break, start-bit glitch, loopback |
| `SPI_apb.sv` + `SPI_top.sv` | `spi_xchk_tb.sv` | `docs/ip/SPI.md`; a mode-0 controller (MSB first, MISO setup before each SCLK rise), SCLK at the documented minimum and slower, three bytes under one CSn, a frame cut by CSn, SCLK with CSn high |
| `I2C_apb.sv` + `I2C_top.sv` | `i2c_xchk_tb.sv` | `docs/ip/I2C.md`; an I2C-bus (UM10204) controller on an open-drain bus with pull-up, START / repeated START / STOP, ACK and NACK, other addresses, STOP inside a byte, and a monitor that fails on any target SDA change while SCL is high |
| `GPIO_apb.sv` + `GPIO_top.sv` | `gpio_xchk_tb.sv` | `docs/ip/GPIO.md`; a board model driving or floating each pin, every pin checked as 0 / 1 / Z (X is contention), level HIGH interrupt |
| `PWM_apb.sv` + `PWM_top.sv` | `pwm_xchk_tb.sv` | `docs/ip/PWM.md`; the waveform computed from the documented rule and compared clock by clock over four periods for 16 PERIOD / DUTY settings (0 %, 100 %, D > P, P = 1, P = 2, random), complement output, PERIOD 0 |
| `I2S_apb.sv` + `I2S_top.sv` | `i2s_xchk_tb.sv` | `docs/ip/I2S.md`; an I2S bus master from the Philips I2S specification (WS changes on the BCLK falling edge, MSB one BCLK after it), 16-bit slots as a continuous stream (each LSB in the first bit of the next slot) and 32-bit slots with padding, BCLK at the documented minimum and slower, FRAME interrupt on every WS edge |
| `SD_apb.sv` + `SD_top.sv` | `sd_xchk_tb.sv` (`+define+SC`: standard capacity) | `docs/ip/SD.md`; an SD memory card from the SD Physical Layer Simplified Specification: command frames with CRC7, R1 / R2 (CID CRC7) / R3 / R6 / R7, the identification order and arguments, CMD24 / CMD17 blocks with CRC16 on each DAT line, CRC status token and busy, block or byte addresses by CCS, N_CR = 64, and eight injected card faults the host has to report on IRQ_STATUS.ERR and recover from |
| `eMMC_apb.sv` + `eMMC_top.sv` | `emmc_xchk_tb.sv` | `docs/ip/eMMC.md`; an e\*MMC device from JEDEC JESD84: command frames with CRC7, R1 (CURRENT_STATE) / R2 (CID CRC7) / R3 (OCR busy, sector mode), the idle / ready / ident / stby / tran states, CMD1 voltage window and access mode, the host-assigned RCA, CMD24 / CMD17 sectors on DAT0 with CRC16, CRC status token and busy, DAT[7:1] released, N_CR = 64, three identification faults (each restarts at CMD0) and eight transfer faults the host has to report on IRQ_STATUS.ERR and recover from |
| `USB_apb.sv` + `USB_top.sv` | `usb_xchk_tb.sv` | `docs/ip/USB.md`; a USB 2.0 full-speed host: NRZI, bit stuffing, SYNC, PID, CRC5 / CRC16 in textbook form anchored to two known packets (SETUP 2D 00 10, GET_DESCRIPTOR data CRC DD 94), the host bit rate at +0.25 % and -0.25 %, a line receiver timing every J / K / SE0 interval (bit times, EOP SE0 160 .. 175 ns, inter-packet delay 2 .. 6.5 bits), chapter 9 enumeration (bus reset, GET_DESCRIPTOR, SET_ADDRESS, GET / SET_CONFIGURATION), DATA0 / DATA1 toggles, a lost ACK, a duplicated OUT, NAK, protocol STALL, other addresses, SOF, and CRC5 / CRC16 / bit-stuffing errors on IRQ_STATUS.RXERR |
| `DDR4_Lite_top.sv` | `ddr_xchk_tb.sv` | `docs/ip/DDR4_Lite.md` front-end; `ddr_pin_mon.sv` on the DRAM pins: the JESD79-4 command truth table, tRCD / tRP / tRC / tRAS / tRRD / tWR / tWTR / tRFC, REF only with every bank precharged, RD / WR only to an open row, burst latency CL / CWL, 8 beats with one DQS toggle each, read bursts against a shadow array filled from the write bursts, refresh interval |
| `LPDDR5X_Lite_top.sv` | `ddr_xchk_tb.sv` (`+define+LPDDR`) | as DDR4_Lite with 8 banks, per-bank REF and tRFCpb, REFRESH of one bank, the two FSP mode-register sets, WCK running only through writes |

`ref/xchk_ref_pkg.sv` holds the SystemVerilog references (CRC-32, CRC-16,
CSI-2 ECC, TMDS encode/decode, TERC4, HDMI BCH, SHA-256, HMAC-SHA-256). It
is checked first against public vectors by `ref_selftest_tb.sv` and ships
in the CSI_2, Ethernet, HDMI and Security VIPs (`ref/`).

## Run

```bash
python3 tools/run_ip_crosscheck.py --ip-dir ../open-ip-portfolio      # all of them
python3 tools/run_ip_crosscheck.py --ip-dir ../open-ip-portfolio eth  # one IP
```

`--ip-dir` defaults to `$OPEN_IP_DIR`, then `../open-ip-portfolio`. Icarus
runs every IP but HDMI; HDMI (about 8 M clocks: reset to the first VSYNC,
then one full frame) runs on Verilator when it is on `PATH` (10 s) and on
Icarus otherwise (about 4 minutes). Vectors and logs are written to
`build/ipcheck/<ip>/`, results to `ipcheck_report.csv`.

## Status (2026-10-30, open-ip-portfolio main 39b0622)

All fifteen IPs pass (sixteen runs): crypto 113 checks, eth 39, csi2 101,
hdmi 18 (each HDMI check covers a whole frame), uart 35, spi 21, i2c 32,
gpio 22, pwm 17, i2s 15, sd 38 (high capacity) and sd_sc 38 (standard
capacity), emmc 41, usb 73, ddr4 18, lpddr5x 24 (the DDR checks each cover the whole run: about 30 000
clocks, 600 random line operations and 30 refreshes).

Hand-made faults in copies of the RTL were all caught: TX padding length,
runt threshold 64 -> 63, PAUSE quanta scale, CSI-2 ECC equation, line-buffer
length clamp, flag clearing at Frame Start, HMAC outer length, SHA-256
padding corner (len 56), HDMI back porch, an AVI InfoFrame byte, the TMDS
disparity branch and the XNOR tie rule; for the peripherals and DDR (30 of
30): UART baud 3 % slow, missing stop bit, framing check removed; SPI MISO
LSB first, MOSI sampled on the falling edge; I2C address LSB ignored, ACK
driven on the SCL rise; a GPIO pin driven with OE 0; PWM duty one clock long,
PERIOD_END in the first clock; DDR4 tRCD one clock short, CL one clock
early, PREA sent as PRE of bank 0, tWR not enforced; LPDDR5X tRFCpb halved,
one bank never refreshed; I2S FRAME only on the right channel, TX left /
right swapped; SD DAT1 CRC16 computed over DAT0, a negative CRC status
token accepted, ACMD41 polled without CMD55; eMMC CRC16 polynomial 0x1023,
OUT_OF_RANGE ignored, CMD1 without sector mode, a negative CRC status token
accepted; USB CRC16 polynomial, the response one bit time after the EOP
start, the EP1 toggle not advanced, an EOP SE0 of one bit time, stuffing
after seven ones.

### Notes (pin-level, reported but not failed)

- SPI: MISO is driven while CSn is high. On a bus with several targets it
  has to be released (high impedance) when the target is not selected.
- DDR4_Lite / LPDDR5X_Lite: an ACT drives RAS_n / CAS_n / WE_n high. In
  JESD79-4 these pins are row address bits A16..A14 while ACT_n is low, so
  a DDR4 device would open row 0x1C000 + row; they should be 0 for rows
  below 2^14.
- DDR4_Lite / LPDDR5X_Lite: RD / WR drive A12 (BC_n) low, which is a BC4
  burst chop when MR0 selects on-the-fly burst length; the bursts are 8
  beats, so A12 should be high.
- DDR4_Lite / LPDDR5X_Lite: an MRW changes CL / CWL inside the controller
  without an MRS command on the pins, so a separate DRAM device would keep
  its old latency. (The array lives inside the model, so the data returned
  is still right.)
- I2S: at the documented minimum of two clocks per BCLK phase SDOUT changes
  less than one clock before the BCLK rise (474 of 1728 bits), so the
  receiver gets no setup margin; at three clocks per phase it is stable.
- SD: the host looks for the response start bit only from the fourth clock
  after the command's end bit. The SD Physical Layer specification lets a
  card answer from N_CR = 2 clocks on, so a card that answers at N_CR = 2
  or 3 fails identification (the bench answers at 4 after probing 2).
- SD: identification runs at the full sd_clk (PCLK / 4, 12.5 MHz here); the
  specification limits identification mode to 400 kHz.
- SD: the host changes CMD and DAT on the sd_clk rising edge, the edge the
  card samples on in default speed, so there is no hold time.
- eMMC: CMD24 / CMD17 are sent right after CMD3, in stand-by state, with
  no CMD7 (SELECT_CARD). A JESD84 device does not answer them there, so the
  host never completes a transfer with a real device; the bench answers
  and counts it.
- eMMC: the host looks for the response start bit only from the fourth
  clock after the end bit; a device answering at N_CR = 2 or 3 (JESD84
  allows 2) never completes identification.
- eMMC: read data and programming busy share the 64-clock response
  timeout. A device's read access time and write busy are milliseconds, so
  read data 100 clocks after the response or a busy of 1000 clocks is
  reported as an error.
- eMMC: the wrapper has no CLK output; the bus runs on PCLK, which the
  board has to route to the device, and identification then runs at
  50 MHz instead of at most 400 kHz. `emmc_rst_n` is an input that resets
  the host, while JESD84 RST_n is a host output to the device.
- USB: GET_DESCRIPTOR(CONFIGURATION) and GET_STATUS are answered with
  STALL. Without a configuration descriptor a USB host cannot enumerate
  the device or learn that EP1 is an interrupt IN endpoint, and chapter
  9.4.5 requires GET_STATUS in the address and configured states.
- LPDDR5X_Lite: the LPDDR5 CA bus is shown as DDR4-style pins (documented
  in the IP), so the pin rules checked are the DDR4 ones.

## Not covered yet

The eMMC bench runs the documented 32-byte blocks in 1-bit mode, and
the USB bench drives the bus at the logic level (no analog PHY,
low-speed or high-speed chirp). The CSI-2
IP models a 1-bit serial lane rather than D-PHY, and the HDMI IP is a
1-bit-per-clock TMDS source, so lane-level (D-PHY / FRL) behaviour is
outside what these benches can check. The DDR checks are pin-level only:
there is no PHY, training or real DRAM device behind the controllers.
