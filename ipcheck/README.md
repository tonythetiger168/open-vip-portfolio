# ipcheck: open-ip-portfolio RTL against independent references

open-ip-portfolio's TV / STB / IP-camera plan
(`docs/TV_STB_IPCAM_IMPROVEMENT_PLAN_2026-10-26.md` there) asks for its
camera and display-path IP to be verified by independent VIPs and public
vectors, not by testbenches that share the RTL's own model. This directory
does that for the IPs that exist today:

| IP (open-ip `rtl/`) | Testbench | Expected values come from |
|---|---|---|
| `Crypto___Security_Engine_top.sv` | `crypto_xchk_tb.sv` | Python `hashlib` / `hmac`, FIPS 180-4 examples, RFC 4231 TC1, TC2, TC6 (37 vectors, lengths 0..64 incl. the 55/56/64-byte padding corners) |
| `Ethernet_top.sv` | `eth_xchk_tb.sv` | frames with `zlib.crc32` FCS; padding, inter-frame gap, underrun, DA filter, CRC / length / PHY-error status, VLAN 1522, runts (38 and 63 bytes), PAUSE quanta |
| `CSI_2_top.sv` | `csi2_xchk_tb.sv` | packets with ECC from the CSI-2 parity equations and CRC-16 anchored to the specification's checksum examples; single-bit correction (data and ECC bits), double-bit drop, CRC error, burst cut, virtual channels, line longer than the buffer |
| `HDMI_2_1_top.sv` | `hdmi_xchk_tb.sv` | a TMDS sink: every character re-encoded with the DVI 1.0 algorithm, control / guard / TERC4 tables, VIC 1 timing, the R=x G=y B=x^y source, InfoFrames with BCH ECC and checksums computed by the runner |

`ref/xchk_ref_pkg.sv` holds the SystemVerilog references (CRC-32, CRC-16,
CSI-2 ECC, TMDS encode/decode, TERC4, HDMI BCH, SHA-256, HMAC-SHA-256). It
is checked first against public vectors by `ref_selftest_tb.sv` and ships
in the CSI_2, Ethernet, HDMI and Security VIPs (`ref/`).

## Run

```bash
python3 tools/run_ip_crosscheck.py --ip-dir ../open-ip-portfolio      # all four
python3 tools/run_ip_crosscheck.py --ip-dir ../open-ip-portfolio eth  # one IP
```

`--ip-dir` defaults to `$OPEN_IP_DIR`, then `../open-ip-portfolio`. Icarus
runs crypto / eth / csi2; HDMI (about 8 M clocks: reset to the first VSYNC,
then one full frame) runs on Verilator when it is on `PATH` (10 s) and on
Icarus otherwise (about 4 minutes). Vectors and logs are written to
`build/ipcheck/<ip>/`, results to `ipcheck_report.csv`.

## Status (2026-10-28, open-ip-portfolio main)

All four IPs pass: crypto 113 checks, eth 39, csi2 101, hdmi 18 (each HDMI
check covers a whole frame). Hand-made faults in copies of the RTL were all
caught: TX padding length, runt threshold 64 -> 63, PAUSE quanta scale,
CSI-2 ECC equation, line-buffer length clamp, flag clearing at Frame Start,
HMAC outer length, SHA-256 padding corner (len 56), HDMI back porch, an AVI
InfoFrame byte, the TMDS disparity branch and the XNOR tie rule.

## Not covered yet

Peripherals (I2C / SPI / UART / GPIO) and DDR / LPDDR on the same plan have
no cross-check here. The CSI-2 IP models a 1-bit serial lane rather than
D-PHY, and the HDMI IP is a 1-bit-per-clock TMDS source, so lane-level
(D-PHY / FRL) behaviour is outside what these benches can check.
