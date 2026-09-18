# LPDDR7 UVM VIP

**Protocol:** LPDDR7 low-power DDR (command/address + DQ/DQS data, bank/row/column)
**Total SVAs:** 22 (L1=4, L2=10, L3=8) in vip/lpddr7 class checkers + 5 L4 protocol rules in sva/
**Checkers:** 4 (Protocol, Data Integrity, Timing, Error) + module SVA compliance checker
**License:** Apache-2.0

## Protocol Overview

The VIP models a host memory controller driving an LPDDR7 device:

- **Commands** on `{cs_n, act_n, ras_n, cas_n, we_n}`: NOP / ACT / RD / WR / PRE / REF
- **Addressing:** bank group `bg[2:0]`, bank `ba[1:0]`, row on `addr` (ACT), column on `addr[9:0]` (RD/WR)
- **Timing concepts:** tRCD (ACT→RD/WR), tRP (PRE→ACT), tRAS (ACT→PRE), tCL (RD→data)
- **Data:** 64-bit `dq` bus, 2-beat representative burst, write data from driver, read data from DUT after tCL

## Directory Structure
```
lpddr7_vip/
|-- rtl/lpddr7_if.sv                  # interface (cmd/addr, dq, timing params)
|-- rtl/lpddr7_mem_model.sv           # functional DRAM DUT model (pure RTL)
|-- vip/lpddr7/
|   |-- lpddr7_driver.sv              # command-encoding driver
|   |-- lpddr7_monitor.sv             # waveform-decoding monitor
|   |-- lpddr7_agent.sv               # sequencer + agent
|   |-- lpddr7_protocol_checker.sv    # L1 SVA (4)
|   |-- lpddr7_data_integrity_checker.sv # L2 SVA (8)
|   |-- lpddr7_timing_checker.sv      # L2 timing SVA
|   |-- lpddr7_error_checker.sv       # L3 SVA (6)
|-- coverage/lpddr7_coverage.sv       # 3 covergroups (protocol/FSM/data + crosses)
|-- env/lpddr7_env.sv                 # env + end-to-end scoreboard
|-- sequences/lpddr7_sequence.sv      # transaction + directed sequences
|-- sva/lpddr7_compliance_checker.sv  # L4 protocol-specific SVA (5)
|-- tests/lpddr7_test.sv              # base / rw / b2b / error / regression tests
|-- tb/tb_top.sv                       # testbench top (DUT closed loop)
|-- Makefile
```

## Sequence Library
| Sequence | Purpose |
|----------|---------|
| `lpddr7_base_sequence` | constrained-random mix (normal) |
| `lpddr7_write_seq` | ACT+WR write bursts |
| `lpddr7_read_seq` | ACT+RD read bursts |
| `lpddr7_back_to_back_seq` | same-bank row-hit/row-miss stress |
| `lpddr7_pre_ref_seq` | PRE + REF maintenance |
| `lpddr7_error_seq` | RD/WR without ACT (error injection) |
| `lpddr7_reset_seq` | access right after reset release |
| `lpddr7_corner_seq` | BL16 + address extremes |
| `lpddr7_stress_seq` | dense random traffic |
| `lpddr7_regression_sequence` | weighted mix of all of the above |

## SVA (L1-L4)
- **L1 (4):** command/address valid, bank ranges — `lpddr7_protocol_checker.sv`
- **L2 (8):** burst length, tRCD/tRP windows, WCK ratio, DMI/DBI/CRC/ODT — data-integrity + timing checkers
- **L3 (6):** PM state, refresh interval, VrefCA/WCK2CK training, temperature — `lpddr7_error_checker.sv`
- **L4 (5):** ACT address known, RD/WR preceded by ACT, no ACT→ACT without PRE, WR data known, REF after PRE — `sva/lpddr7_compliance_checker.sv`

## Functional Coverage
- `cg_protocol`: cmd x bg x ba, cmd x burst-length, row ranges
- `cg_fsm`: ACT→RD / ACT→WR / RD|WR→PRE / PRE→ACT / PRE→REF transition bins
- `cg_data`: write-data corners (0x00/0xFF/0xAA/0x55) x beat cross

## Quick Start
```bash
make comp                        # single-run compile (VCS)
make sim                         # run
make regress                     # regression test
cd scripts && ./coverage_regression.sh   # coverage-driven regression (100% goal)
```

## Deepened Features (v1.6.0)
- Real command-encoding driver (ACT/RD/WR/PRE/REF, bank/row/col, tRCD/tRP/tRAS/tCL)
- Waveform-decoding monitor publishing reconstructed transactions
- End-to-end scoreboard (driver-expected vs monitor-observed, n_matches/n_mismatches)
- Functional DRAM DUT model with open-row tracking and read-data return
- 10-sequence directed library (normal/error/reset/back-to-back/stress/corner)
- L4 protocol-specific SVA rules + 3 functional covergroups with crosses
