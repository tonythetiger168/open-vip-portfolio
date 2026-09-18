# Icarus Verilog DUT Smoke Test Harness

Batch smoke tests for the functional DUT (pure RTL) models inside the 87
SystemVerilog UVM VIPs. UVM testbenches cannot be compiled by Icarus, so the
DUT modules are extracted and tested standalone.

## Usage

    bash run_smoke.sh              # all 87 VIPs (parallel, xargs -P 3)
    bash run_smoke.sh AHB-VIP      # single VIP (name or full path)

Output lines: `SMOKE_PASS|SMOKE_FAIL|SMOKE_SKIP <VIP> -- <per-module detail>`.
Summary: `smoke_report.csv` (vip,result,detail). Per-VIP log: `<VIP>/smoke.log`.

## How it works

1. `flatten.py` locates DUT modules (`*_dut`/`*_model` in `tb/top_tb.sv`,
   `top/top_tb.sv`, `tb_top.sv`, `*_model.sv`), parses the corresponding
   `*_if.sv` interface signal declarations, and rewrites interface ports
   (`vif.sig`) into flat `input/output/inout logic` ports (direction inferred
   from DUT usage; `z`-driven buses become `inout`; unpacked arrays are packed;
   interface parameters substituted). Unreliable transforms (interface
   pass-through to submodules, unknown enum widths) -> SKIP.
2. `smoke_run.py` auto-generates `tb_smoke_<mod>.sv` (clock gen, reset
   sequence, deterministic `$random` stimulus, 1500 cycles), compiles with
   `iverilog -g2012`, runs `vvp`. Outputs are monitored with `$isunknown`
   after reset warmup: any X/Z -> SMOKE_FAIL, else SMOKE_PASS (toggle count
   recorded). Packages needed by a DUT are auto-sanitized (UVM classes and
   unsupported functions stripped) and imported; compile failures caused by
   genuine Icarus limitations (queues, associative arrays, `break`/`continue`,
   `inside`, enum casts, `iff` event control) are reported as SKIP.

## Layout

    flatten.py        interface-port flattener
    smoke_run.py      tb generator + compile/run/classify
    run_smoke.sh      entry script (see Usage)
    smoke_report.csv  per-VIP results
    <VIP>/            dut_<mod>.sv, tb_smoke_<mod>.sv, smoke.log, row.csv
