# HBM5 UVM VIP

**Protocol:** HBM5 (High Bandwidth Memory, 5th generation)
**License:** Apache-2.0

## 1. Protocol Overview

HBM5 is a 3D-stacked high-bandwidth DRAM. The VIP models one pseudo-channel command/address interface with JEDEC-style DRAM commands (ACT/RD/WR/PRE/REF), bank-group/bank addressing and stack-aware signaling (stack_id, speed_grade).

The command/address bus encodes DRAM commands on `cs_n/act_n/ras_n/cas_n/we_n`:

| Command | cs_n | act_n | ras_n | cas_n | we_n | Address bus |
|---------|------|-------|-------|-------|------|-------------|
| ACT     | 0    | 0     | -     | -     | -    | row         |
| RD      | 0    | 1     | 1     | 0     | 1    | column      |
| WR      | 0    | 1     | 1     | 0     | 0    | column      |
| PRE     | 0    | 1     | 0     | 1     | 0    | bank        |
| REF     | 0    | 1     | 0     | 0     | 1    | -           |
| NOP/DES | 1    | -     | -     | -     | -    | -           |

Timing parameters (cycles): tRCD=6, tRP=6, tRAS=16,
tCL=12, tCWL=10, tFAW=12, tRFC=20.

## 2. Architecture

```
tb/tb_top.sv                 testbench top: clk/reset, hbm5_if, DRAM memory model,
                             SVA checker instantiation (closed loop)
rtl/hbm5_if.sv                interface (CA bus + DQ + clocking block)
sequences/hbm5_sequence.sv    transaction + sequence library (below)
vip/hbm5/hbm5_driver.sv        command driver (ACT/RD/WR/PRE/REF + timing)
vip/hbm5/hbm5_monitor.sv       command/address bus decoder -> analysis port
vip/hbm5/hbm5_agent.sv         sequencer + driver + monitor
vip/hbm5/hbm5_scoreboard.sv    end-to-end expected-vs-observed comparison
vip/hbm5/hbm5_coverage.sv      functional coverage (3 covergroups, crosses)
vip/hbm5/hbm5_*_checker.sv     legacy L1/L2/L3 SVA checkers (module-based)
sva/hbm5_compliance_checker.sv consolidated L1-L4 compliance checker
env/hbm5_env.sv               environment (agent + scoreboard + coverage)
tests/hbm5_test.sv            base / directed / stress tests
```

Scoreboard flow: driver publishes expected transactions on `drv_ap`, monitor
publishes bus-decoded transactions on `ap`; the scoreboard compares them
in order and counts `n_matches`/`n_mismatches` (mismatch -> `UVM_ERROR`).

The `tb/tb_top.sv` DRAM memory model tracks bank/row state, stores write data
in a sparse `{bg,ba,row,col}` array, returns it on reads after tCL, and
counts refreshes -- closing the end-to-end data loop.

## 3. Sequence Library

| Sequence | Purpose |
|----------|---------|
| `hbm5_base_sequence`      | randomized baseline traffic |
| `hbm5_rw_round_seq`       | ACT->RD/WR->PRE round helper |
| `hbm5_write_seq`          | directed write rounds |
| `hbm5_read_seq`           | directed read rounds |
| `hbm5_refresh_seq`        | refresh traffic |
| `hbm5_bank_conflict_seq`  | same-bank ACT/PRE turnaround (tRP/tRCD pressure) |
| `hbm5_back_to_back_seq`   | inter-bank back-to-back accesses |
| `hbm5_page_hit_seq`       | corner: multiple accesses to one open row |
| `hbm5_page_miss_seq`      | corner: every access forces PRE+ACT |
| `hbm5_stress_seq`         | long randomized command mix |
| `hbm5_regression_seq`     | weighted mix of all directed sequences |

## 4. SVA Checkers (L1-L4)

Legacy tiered checkers (module-based, in `vip/hbm5/`):
- `hbm5_protocol_checker` (L1: basic compliance)
- `hbm5_timing_checker` (L2: timing windows)
- `hbm5_data_integrity_checker` (L2/L3: data rules)
- `hbm5_error_checker` (L3: error conditions)

Consolidated `sva/hbm5_compliance_checker.sv`:
- **L1 (3):** clock/command-bus/address sanity
- **L2 (3):** ACT encoding, bank-group range, CKE gating
- **L3 (2):** reset deselect, post-refresh quiet window
- **L4 (6):** tRCD (ACT->CAS), tRAS (ACT->PRE), tFAW (<=4 ACT/window),
  RD/WR only to open bank, no ACT to open bank, refresh interval (tREFI)

## 5. Functional Coverage

- `cg_cmd`        : command distribution x bank group / bank address (crosses)
- `cg_bank_state` : bank state transitions (IDLE/ACTIVE) x command (cross)
- `cg_addr`       : row/column regions, page hit/miss x burst length (cross)

## 6. Quick Start

```bash
cd hbm5_vip
make comp                                 # compile (VCS)
make sim                                  # run base test
make regress                              # directed regression test
make -C scripts SIMULATOR=vcs TEST=hbm5_directed_test   # portable flow
```

Tests: `hbm5_base_test` (default), `hbm5_directed_test`, `hbm5_stress_test`.
