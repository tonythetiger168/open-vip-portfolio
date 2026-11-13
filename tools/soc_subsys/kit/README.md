# AXI4 Manager Port UVM VIP (AXI4_Manager_Port-UVM-VIP)

Reusable verification kit for the **AXI4 manager ("master") port** of an IP:
32-bit address and data, 4-bit ID, the `m_*` pins of the open-ip-portfolio
SoC subsystem IPs. Every `<P>-UVM-VIP` of the SoC subsystem family ships the
same `common/` directory; this VIP is the kit on its own, with a self-test
that proves the checkers.

## Components (`common/ssv_pkg.sv`)

| Component | What it does |
|---|---|
| `axim_if` | the AXI4 channels (pin names without `m_`), plus a cycle-level checker: `CHK_STABLE_AW/W/AR/B/R` (VALID held until READY, payload stable), `CHK_RESET` (no VALID in reset), `CHK_UNKNOWN` (no X/Z) |
| `axim_subordinate` | memory-backed responder: INCR / WRAP / FIXED, narrow transfers, sparse strobes, W before AW, random READY back-pressure and response latency, gaps between R beats, SLVERR / DECERR regions (errored write beats do not reach memory, errored read beats return 0) |
| `axim_monitor` | rebuilds every burst and checks it against `axim_cfg`: `TXN_ID`, `TXN_SIZE`, `TXN_BURST`, `TXN_LEN`, `TXN_4K`, `TXN_ALIGN`, `TXN_STRB`, `TXN_WLAST`, `TXN_RLAST`, `TXN_OUTSTANDING`, `TXN_WINDOW`, `TXN_RESP_ID`, `TXN_HANG`; prints `LAT <master> <slave> <R\|W> <cycles>` per burst |
| `axim_coverage` | counters per direction, beats, size, burst, response, ID and 4 KB page end; prints `FCOV <group> <point> <bin> <hits>` (0-hit bins included) |
| `axim_agent` | subordinate + monitor + coverage around one `ssv_mem` |
| `ssv_axi_mgr_bfm` | AXI4 manager BFM with one injection per rule (`inject_e`) |
| `ssv_mem` | sparse byte memory: front door for the subordinate, back door for tests, tracks the bytes the IP wrote |
| `ssv_apb_*`, `ssv_env`, `ssv_base_test` | APB4 agent, RAL adapter, env and base test of the subsystem VIPs |

`axim_cfg` holds what the IP promises (defaults = the subsystem contract:
INCR, 4-byte beats, at most 16 beats, full strobes, aligned, one read and one
write outstanding) and how the subordinate behaves.

## Using it on any AXI4 manager

```systemverilog
axim_if axi (.aclk(clk), .aresetn(rst_n));
my_ip dut (.m_awaddr(axi.awaddr), /* ... every m_* pin ... */);
initial uvm_config_db #(virtual axim_if)::set(null, "*", "axim_vif", axi);
```

In the env: create an `axim_agent`, set `agent.cfg` (expected ID, limits,
windows, back-pressure, error regions), preload `agent.mem`, and read results
back from it or from `agent.mon.completed`.

## Self-test

| Test | Checks |
|---|---|
| `axim_func_test` | about 1,000 legal bursts of every shape, a write and a read in flight together, four back-pressure settings, SLVERR / DECERR regions: every read beat against a byte shadow, every response, no checker fires, every burst type / size / ID covered |
| `axim_checker_test` | 13 injected violations (4 KB, length, size, burst, alignment, early / missing WLAST, strobes, window, AWVALID dropped, AWADDR changed, WDATA changed, ARVALID dropped): each caught by its rule and no other, legal bursts in between trip nothing |
| `kit_if_rules_test` | the cycle-level rules of `axim_if` and `ssv_apb_if`, on a second instance of each driven pin by pin: AWVALID and BVALID in reset, WVALID / BVALID / RVALID dropped before READY, PENABLE without PSEL, a two-clock setup phase, PADDR changed in the access phase; each raises its own rule exactly once. X/Z on a VALID (CHK_UNKNOWN) is driven only on 4-state simulators: Verilator is 2-state |

Pass marker: `SB_PASS checks=<n>`. Run:

```
verilator --binary --timing -Wno-fatal -Wno-lint -Wno-style --top-module top_tb \
  +incdir+$UVM_CORE $UVM_CORE/uvm_pkg.sv -f sim/axim_kit.f
./obj_dir/Vtop_tb +UVM_TESTNAME=axim_checker_test
```

## Verilator notes

No clocking blocks: drivers change signals on the falling edge and sample
on the rising edge, monitors sample on the rising edge. The checkers are
procedural (no `--assert` needed) and coverage is counters (Verilator 5.052
does not sample covergroups).

## License

Apache-2.0 (SPDX-License-Identifier: Apache-2.0).
