# CSI-2 - MIPI CSI-2 UVM VIP

Open-source UVM verification IP for **MIPI CSI-2** (deepened, v1.6.0).
Part of the MIPI VIP family (CSI-2 / DSI / D-PHY / C-PHY / M-PHY / UniPro /
DigRFv4 / HSI / CSE 2.0) sharing one MAC+PHY interface and UVM package; this
instance is specialized with `MIPI_CSI2` protocol behavior.

## Protocol overview

MIPI CSI-2 camera serial interface: packetized image data over D-PHY/C-PHY lanes. Packets carry a 32-bit header (data identifier = VC+DT, word count, ECC) and a CRC-16 footer. Short packets (FS/FE/LS/LE) are header-only; long packets carry pixel payload (RAW6-14, RGB565/666/888, YUV422).

## Architecture

| Path | Description |
|------|-------------|
| `rtl/mipi_vip_if.sv` | MAC+PHY interface (data/valid/sop/eop/pkt_type/vc/wc/ecc/crc, D-PHY/C-PHY/M-PHY/UniPro lanes, lane FSM state, protocol status signals, embedded assertions + interface covergroup) |
| `vip/base/mipi_vip_pkg.sv` | UVM package: `mipi_txn` (ECC/CRC compute + compare), driver, monitor, agent, 3-covergroup functional coverage, end-to-end scoreboard, sequence library |
| `vip/<proto>/<proto>_protocol_checker.sv` | 9 protocol checkers (the CSI-2 checker is deepened with waveform re-computation) |
| `rtl/sva/csi_2_compliance_checker.sv` | Tiered SVA compliance checker: L1 basic / L2 full protocol / L3 advanced / **L4 protocol-specific** |
| `env/mipi_env.sv` | Environment: agent + scoreboard + coverage + 9 checkers |
| `tests/mipi_tests.sv` | base / directed / error / reset / stress / regression tests |
| `tb/top_tb.sv` | Testbench top + functional DUT model: camera sensor sink (ECC/CRC re-computation) (closed loop) |
| `scripts/` | Makefile + coverage-driven regression (line/fsm/toggle/SVA, 100% goal) |

## Closed loop

VIP driver serializes packets onto the MAC bus (header with ECC, payload,
CRC-16 footer) with CSI-2 PHY signaling. The `mipi_dut` model handshakes,
decodes the packet, re-computes ECC/CRC-16 and drives `ecc_ok`/`crc_ok` status
back. The monitor reconstructs transactions from the waveform; the scoreboard
compares expected (driver) vs observed (monitor) end-to-end.

## Directed sequence library

| Sequence | Purpose |
|----------|---------|
| `mipi_normal_seq` | normal frame traffic (FS / long packets / FE, HS mode) |
| `mipi_error_seq` | error injection (corrupted ECC / CRC, must be flagged) |
| `mipi_reset_seq` | transfer immediately after reset release |
| `mipi_back_to_back_seq` | minimum inter-packet gap |
| `mipi_stress_seq` | long bursts (WC 512-4095), 100 transactions |
| `mipi_corner_seq` | min/max word count, ULPS entry, NULL/BLANK/EMBEDDED short packets, LP mode |
| `mipi_regression_sequence` | weighted mix of all of the above |

Tests: `mipi_csi2_test`, `mipi_csi2_error_test`, `mipi_csi2_reset_test`,
`mipi_csi2_stress_test`, `mipi_csi2_regression_test` (plus legacy
`mipi_<proto>_test` smoke tests).

## SVA compliance levels

- **L1 Basic Compliance (4)**: data type encoding, VC 0-3, WC range, ECC valid
- **L2 Full Protocol (4)**: CRC on EOP, SOP-before-EOP, no-X on valid, lane active
- **L3 Advanced Features (4)**: ULPS entry, escape mode, HS request, calibration
- **L4 Protocol-Specific (4)**: long-packet WC>0, short packet header-only, FS/FE pairing, payload in HS mode

## Functional coverage

- `mipi_cov::cg_mipi` - protocol config: packet type x VC, protocol x lane count, mode x word count crosses
- `mipi_cov::cg_fsm` - lane FSM states + transition sequences (HS entry/exit, ULPS)
- `mipi_cov::cg_data` - data pattern corners (all-0/all-1) x ECC/CRC error flags
- `mipi_vip_if::cg_mipi_if` - interface-level packet/VC/mode bins

## Quick start

```bash
cd scripts
make all TEST=mipi_csi2_test SEED=12345          # single run (VCS default)
make all TEST=mipi_csi2_regression_test          # full sequence mix
./coverage_regression.sh                          # regression + 100% coverage gate
SIMULATOR=questa ./coverage_regression.sh
```

License: Apache-2.0
