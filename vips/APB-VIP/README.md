# APB — APB4 UVM VIP

Open-source UVM verification IP for **AMBA APB4** (peripheral bus), sharing
the common `amba_vip_if` / `amba_vip_pkg` skeleton with the AHB and AXI VIPs.

## Protocol overview

APB4 is a two-cycle non-pipelined bus: a SETUP cycle (`PSEL=1, PENABLE=0`)
followed by ACCESS cycles (`PSEL=1, PENABLE=1`) that complete when the slave
drives `PREADY=1`. Slaves may insert wait states and signal errors with
`PSLVERR` (valid only when `PSEL & PENABLE & PREADY`). Writes use `PSTRB`
byte enables.

## Architecture

| Path | Description |
|------|-------------|
| `rtl/amba_vip_if.sv` | AXI4+AHB5+APB4 interface, `drv_cb`/`mon_cb` clocking blocks, modports, inline SVA + covergroup |
| `vip/base/amba_vip_pkg.sv` | `amba_txn`/`amba_seq_item`, `amba_cov`, end-to-end `amba_sb` scoreboard; includes APB UVC + SVA checker |
| `vip/apb/apb_driver.svh` | APB4 master driver: SETUP→ACCESS progression, PREADY wait states, PSLVERR capture, PSTRB generation, back-to-back bursts |
| `vip/apb/apb_monitor.svh` | APB4 monitor: decodes completed transfers, reassembles consecutive words into burst items |
| `vip/apb/apb_agent.svh` / `apb_sequencer.svh` | Active agent (sequencer + driver + monitor) |
| `vip/apb/apb_sequences.svh` | Directed sequence library (see below) |
| `vip/apb/apb_coverage.svh` | Functional coverage (3 covergroups + crosses) |
| `vip/apb/apb_protocol_checker.sv` | Class-based protocol checker (properties + `cg_apb`) |
| `rtl/sva/apb_compliance_checker.sv` | Tiered SVA compliance checker (L1/L2/L3/L4) |
| `env/amba_env.sv` | Environment: agent, scoreboard, coverage, checkers, analysis connections |
| `tests/amba_tests.sv` | `amba_base_test` / `amba_axi_test` / `amba_ahb_test` / `amba_apb_test` |
| `tb/top_tb.sv` | Testbench top + functional APB4 slave DUT (64×32-bit register bank, wait-state and error regions) |
| `scripts/` | Makefile + coverage-driven regression (line/fsm/toggle/SVA, 100% goal) |

## Sequence library

| Sequence | Purpose |
|----------|---------|
| `apb_base_sequence` | Random APB4 transactions |
| `apb_write_seq` | Directed write bursts |
| `apb_read_seq` | Directed read bursts (1–8 words) |
| `apb_back_to_back_seq` | Zero-gap back-to-back single transfers |
| `apb_wait_state_seq` | Accesses to wait-state region (`paddr[7:4]==4'hF`) |
| `apb_error_inject_seq` | PSLVERR error region (`0xEE??_????`) |
| `apb_reset_seq` | Transfer right after reset release |
| `apb_stress_seq` | 100 random bursts |
| `apb_regression_sequence` | Weighted mix of all directed sequences |

## SVA compliance (rtl/sva/apb_compliance_checker.sv)

- **L1 Basic (4)**: PSEL→PENABLE, PENABLE timing, PWRITE/PADDR stability
- **L2 Full protocol (2)**: PWDATA stable on write, PREADY response
- **L3 Advanced (0)**: reserved
- **L4 APB4-specific (4)**: PENABLE requires PSEL, PSLVERR only at access completion, control stable during wait states, PENABLE deasserts after transfer

## Functional coverage (vip/apb/apb_coverage.svh)

- `cg_protocol`: write × prot × resp, burst length bins + crosses
- `cg_fsm`: PSEL/PENABLE state + transition bins (idle→setup→access, back-to-back, wait states)
- `cg_data`: data pattern corners (all-0/all-1/0xAA…/0x55…) × write cross

## Quick start

```bash
cd scripts
make all                       # single run (VCS default)
TEST=amba_apb_test make all
./coverage_regression.sh       # full regression + 100% coverage gate
SIMULATOR=questa ./coverage_regression.sh
```

## Deepened Features (v1.6.0)

- **APB4 master driver**: SETUP/ACCESS state machine, PREADY wait-state handling, PSLVERR capture, back-to-back word bursts
- **Transfer-decoding monitor**: reassembles consecutive completed transfers into burst transactions on an analysis port
- **End-to-end scoreboard**: driver-issued (expected) vs monitor-decoded (observed) compare with `n_matches`/`n_mismatches` and `UVM_ERROR` on mismatch
- **Functional DUT model**: APB4 slave register bank with wait-state region, PSLVERR region and PSTRB byte-enable masking
- **Directed sequence library**: 9 sequences (write / read / back-to-back / wait-state / error / reset / stress / regression)
- **SVA L4**: 4 APB4-specific rules
- **Functional coverage**: 3 covergroups with cross coverage

License: Apache-2.0
