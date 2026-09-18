# AXI — AXI4 UVM VIP

Open-source UVM verification IP for **AMBA AXI4**, sharing the common
`amba_vip_if` / `amba_vip_pkg` skeleton with the AHB and APB VIPs.

## Protocol overview

AXI4 uses five independent handshake channels: AW/W/B for writes and AR/R
for reads. Bursts (`AWLEN/ARLEN` + 1 beats) support INCR / WRAP / FIXED
addressing with `AxSIZE` beat size; `WLAST`/`RLAST` mark the final beat.
Responses (`BRESP`/`RRESP`) report OKAY / EXOKAY / SLVERR / DECERR.

## Architecture

| Path | Description |
|------|-------------|
| `rtl/amba_vip_if.sv` | AXI4+AHB5+APB4 interface, `drv_cb`/`mon_cb` clocking blocks, modports, inline SVA + covergroup |
| `vip/base/amba_vip_pkg.sv` | `amba_txn`/`amba_seq_item`, `amba_cov`, end-to-end `amba_sb` scoreboard; includes AXI UVC + SVA checker |
| `vip/axi/axi_driver.svh` | AXI4 master driver: AW/W/B and AR/R handshakes, INCR/WRAP/FIXED bursts, WLAST, BRESP/RRESP capture |
| `vip/axi/axi_monitor.svh` | AXI4 monitor: tracks all 5 channels, reconstructs bursts (close on B / RLAST) |
| `vip/axi/axi_agent.svh` / `axi_sequencer.svh` | Active agent (sequencer + driver + monitor) |
| `vip/axi/axi_sequences.svh` | Directed sequence library (see below) |
| `vip/axi/axi_coverage.svh` | Functional coverage (3 covergroups + crosses) |
| `vip/axi/axi_protocol_checker.sv` | Class-based protocol checker (properties + `cg_axi`) |
| `rtl/sva/axi_compliance_checker.sv` | Tiered SVA compliance checker (L1/L2/L3/L4) |
| `env/amba_env.sv` | Environment: agent, scoreboard, coverage, checkers, analysis connections |
| `tests/amba_tests.sv` | `amba_base_test` / `amba_axi_test` / `amba_ahb_test` / `amba_apb_test` |
| `tb/top_tb.sv` | Testbench top + functional AXI4 slave DUT (memory, SLVERR region `0xEE00_0000`) |
| `scripts/` | Makefile + coverage-driven regression (line/fsm/toggle/SVA, 100% goal) |

## Sequence library

| Sequence | Purpose |
|----------|---------|
| `axi_base_sequence` | Random AXI4 transactions (8-byte beats, aligned) |
| `axi_single_seq` | Single-beat directed transfers |
| `axi_incr_burst_seq` | INCR 4/8/16-beat bursts (aligned) |
| `axi_wrap_burst_seq` | WRAP 2/4/8/16 cache-line corner case |
| `axi_back_to_back_seq` | Zero-delay back-to-back transfers |
| `axi_error_inject_seq` | SLVERR region accesses (`0xEE??_????`) |
| `axi_reset_seq` | Transfer right after reset release |
| `axi_stress_seq` | 100 long random bursts |
| `axi_regression_sequence` | Weighted mix of all directed sequences |

## SVA compliance (rtl/sva/axi_compliance_checker.sv)

- **L1 Basic (4)**: AWVALID/WVALID/ARVALID/RVALID stability until ready
- **L2 Full protocol (4)**: burst legality, WLAST, B/R response rules
- **L3 Advanced (4)**: ID ordering, WSTRB contiguity, exclusive access, AWCACHE
- **L4 AXI4-specific (4)**: AW payload stable until AWREADY, WLAST vs AWLEN context, BVALID only after WLAST handshake, R payload stable until RREADY

## Functional coverage (vip/axi/axi_coverage.svh)

- `cg_protocol`: write × burst × size × len, response bins + crosses
- `cg_fsm`: channel handshake flow bins (idle→AW→W→B / idle→AR→R, back-to-back)
- `cg_data`: data pattern corners (all-0/all-1/0xAA…/0x55…) × write cross

## Quick start

```bash
cd scripts
make all                       # single run (VCS default)
TEST=amba_ahb_test make all
./coverage_regression.sh       # full regression + 100% coverage gate
SIMULATOR=questa ./coverage_regression.sh
```

## Deepened Features (v1.6.0)

- **AXI4 master driver**: full 5-channel handshake, burst address generation (INCR/WRAP/FIXED), WLAST/RLAST handling, BRESP/RRESP capture
- **Channel-tracking monitor**: reconstructs write/read bursts from handshakes, closes on B / RLAST, publishes transactions
- **End-to-end scoreboard**: driver-issued (expected) vs monitor-decoded (observed) compare with `n_matches`/`n_mismatches` and `UVM_ERROR` on mismatch
- **Functional DUT model**: AXI4 slave memory with SLVERR region closing the driver→DUT→monitor loop
- **Directed sequence library**: 9 sequences (single / incr / wrap / back-to-back / error / reset / stress / regression)
- **SVA L4**: 4 AXI4-specific rules
- **Functional coverage**: 3 covergroups with cross coverage

License: Apache-2.0
