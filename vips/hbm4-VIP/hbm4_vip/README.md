# HBM4 UVM VIP

**Protocol Level:** Complex
**Checkers:** 4 UVM components (Protocol L1, Data Integrity L2, Timing L2, Error L3) + module-based SVA compliance checker (L1-L4)
**License:** Apache-2.0

## Protocol Overview
HBM4 stacked DRAM: 2048-bit interface, doubled pseudo-channels vs HBM3, stack_id up to 16Hi.

The VIP drives and monitors a DDR-style command/address bus
(`cs_n/act_n/ras_n/cas_n/we_n` + `{bg,ba}` bank + `addr` row/column):

| Command | cs_n | act_n | ras_n | cas_n | we_n | Address |
|---------|------|-------|-------|-------|------|---------|
| ACT     | 0    | 0     | -     | -     | -    | row     |
| RD      | 0    | 1     | 1     | 0     | 1    | column  |
| WR      | 0    | 1     | 1     | 0     | 0    | column  |
| PRE     | 0    | 1     | 0     | 1     | 0    | -       |
| REF     | 0    | 1     | 0     | 0     | 1    | -       |
| NOP     | 0    | 1     | 1     | 1     | 1    | -       |

Core timing parameters (cycles): tRCD=10, tRP=10, tRAS=14, tCL=10, tCWL=2, tRFC=48, tREFI=3900.

## Architecture
```
hbm4_vip/
|-- rtl/hbm4_if.sv                    # signal interface (+ clocking block)
|-- sequences/hbm4_sequence.sv        # transaction + directed sequence library
|-- vip/hbm4/
|   |-- hbm4_driver.sv                # protocol driver (cmd encoding, timing, DQ)
|   |-- hbm4_monitor.sv               # bus monitor (command/DQ decode -> analysis port)
|   |-- hbm4_agent.sv                 # sequencer + driver + monitor
|   |-- hbm4_coverage.sv              # 3 covergroups with crosses
|   |-- hbm4_compliance_checker.sv    # SVA module, L1-L4 (instanced in tb_top)
|   |-- hbm4_protocol_checker.sv      # L1 component (procedural sampling)
|   |-- hbm4_timing_checker.sv        # L2 component (tRCD/tRP/tRAS measurement)
|   |-- hbm4_data_integrity_checker.sv# L2 component (DQ/DBI/BL sampling)
|   |-- hbm4_error_checker.sv         # L3 component (temp/refresh/DFE monitoring)
|-- env/hbm4_env.sv                   # env + end-to-end scoreboard
|-- tests/hbm4_test.sv                # base/write/read/stress tests
|-- tb/tb_top.sv                     # TB top + DRAM memory-array functional model
|-- Makefile
```

Closed loop: sequences -> driver -> `hbm4_if` -> `hbm4_mem_model` (bank/row/col
storage in tb_top) drives read data back -> monitor decodes -> scoreboard
compares expected (driver) vs observed (monitor) end-to-end.

## Sequence Library
| Sequence | Purpose |
|----------|---------|
| `hbm4_base_sequence` | legacy fully-random items (API compatibility) |
| `hbm4_write_seq` | normal write flow: ACT, WR burst, PRE |
| `hbm4_read_seq` | normal read flow: ACT, RD burst, PRE |
| `hbm4_refresh_seq` | traffic punctuated by REF (tRFC apart) |
| `hbm4_bank_conflict_seq` | same bank, alternating rows (page misses) |
| `hbm4_back_to_back_seq` | one ACT, long alternating RD/WR stream (page hits) |
| `hbm4_stress_seq` | long protocol-legal random stream (bank-state model) |
| `hbm4_corner_seq` | all-zero/all-one row/col, boundary banks/stacks |
| `hbm4_random_sequence` | 50 random items |
| `hbm4_regression_sequence` | weighted mix of all directed sequences |

Tests: `hbm4_base_test` (regression seq), `hbm4_write_test`, `hbm4_read_test`, `hbm4_stress_test`.

## SVA Compliance Checker (vip/hbm4/hbm4_compliance_checker.sv)
- **L1 signal sanity (4):** command/address known when selected, bank group/address encoding bounds.
- **L2 timing & data integrity (10):** tRCD/tRP windows, burst length, data valid with DQS, DBI/WCK settings.
- **L3 error handling (8):** power-management state, refresh interval, over-temperature, DFE/bandwidth/latency bounds.
- **L4 HBM4-specific (10):** ACT/RD-WR/PRE bank-state legality (3), tRCD/tRP/tRAS timing rules (3), refresh pulse width, CKE gating, family rules (pseudo-channel stability + stack select), refresh-interval + ACT->col->PRE covers.

## Functional Coverage (vip/hbm4/hbm4_coverage.sv)
- `cg_command`    : command distribution x bank cross (`cx_cmd_bank`)
- `cg_bank_state` : bank state transitions (ACT=>RD/WR, RD/WR=>PRE, PRE/REF=>ACT, RD<=>WR)
- `cg_addr`       : row/col/stack address patterns with `cx_row_col` cross

## Quick Start
```bash
make comp                                   # compile (VCS + UVM 1.2)
make sim                                    # run default test
make regress                                # run regression test
./simv +UVM_TESTNAME=hbm4_stress_test        # run a directed test
```
