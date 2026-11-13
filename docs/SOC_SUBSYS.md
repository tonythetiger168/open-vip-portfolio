# SoC subsystem VIPs

Fourteen UVM VIPs for the phone SoC subsystem IPs of
[open-ip-portfolio](https://github.com/tonythetiger168/open-ip-portfolio): one
per AXI4-manager IP plus the shared AXI4 manager-port kit.

| VIP | IP | AXI ID | What the scoreboard models |
|-----|----|--------|-----------------------------|
| `AXI4_Manager_Port-UVM-VIP` | every AXI4-manager IP | - | the port contract itself (self-test: legal traffic, 13 injected transaction violations, and every cycle-level AXI / APB checker rule tripped pin by pin) |
| `CPU_Cluster-UVM-VIP` | CPU_Cluster | 0 | WRITE pattern, CHECK (mismatches, first fail, MISMATCH irq), COPY |
| `GPU-UVM-VIP` | GPU | 1 | 2D ops on pixel lines up to 8K |
| `NPU-UVM-VIP` | NPU | 2 | convolution |
| `ISP-UVM-VIP` | ISP | 3 | test pattern and sensor stream, black level, gain, clipping, STAT_SUM |
| `Video_Codec-UVM-VIP` | Video_Codec | 5 | DPCM encode / decode round trip, ZEROS, CHECKSUM |
| `Display_Controller-UVM-VIP` | Display_Controller | 4 | scan-out order, hsync / vsync, FRAME_CRC, UNDERRUNS against a panel model |
| `Audio_DSP-UVM-VIP` | Audio_DSP | 8 | gain, mix, mute, saturation, peak |
| `Modem-UVM-VIP` | Modem | 6 | LFSR scrambler, CRC-32 |
| `Sensor_Hub-UVM-VIP` | Sensor_Hub | 9 | 2^k averaging, packing, WAKE threshold, FIFO drops |
| `SMMU-UVM-VIP` | SMMU | 15 (downstream) | translation, TLB refill / round robin, permission faults, invalidation |
| `DMA-UVM-VIP` | DMA | 7 | copy / fill on 4 channels, round-robin arbitration |
| `Interrupt_Controller-UVM-VIP` | Interrupt_Controller | 10 | PENDING / CLAIM / cpu_irq every clock, event-log records (priority, merge, timestamps) |
| `Timer_WDT-UVM-VIP` | Timer_WDT | 11 | clock-exact timer, watchdog bark / bite, timestamp ring |

The AXI IDs above come from each IP's spec (`scripts/apb/specs/<IP>.json`,
`axi_master.id`); the base test reads them from there, so a change in the IP
shows up as a `TXN_ID` error rather than a silent pass.

## What is in a zip

```
<IP>-UVM-VIP/
  common/       ssv_pkg: APB4 agent + RAL adapter, AXI4 subordinate / monitor /
                coverage, env, base test; axim_if and ssv_apb_if with
                cycle-level protocol checkers
  rtl/          snapshot of the IP's RTL (SNAPSHOT.txt names the open-ip commit)
  <ip>/         generated RAL (offsets from open-ip's gen_apb.py), pins_if,
                package with the reference model and tests
  tb/top_tb.sv  <IP>_apb wired to the agents
  sim/<ip>.f    Verilator filelist; sim/testlist.txt "<test> <seeds> [plusargs]"
  README.md, docs/TEST_PLAN.md
```

## Running

```bash
unzip vips/DMA-UVM-VIP.zip -d work && cd work/DMA-UVM-VIP
verilator --binary --timing --top-module top_tb \
  +incdir+$UVM_CORE/src $UVM_CORE/src/uvm_pkg.sv -f sim/dma.f
./obj_dir/Vtop_tb +UVM_TESTNAME=dma_copy_test +verilator+seed+1
```

or, for every VIP and seed in the testlists: `python3 tools/run_uvm_tests.py`.
Tested with Verilator 5.052 and Accellera uvm-core 2020.3.1.

A passing run prints `SB_PASS checks=<n>` (`RAL_PASS` for the register test)
and `LAT <master> <slave> <R|W> <cycles>` for every AXI burst. It also prints
`FCOV <group> <point> <bin> <hits>` for every declared bin, including bins
with 0 hits, in two groups:

- `axim`: the AXI port, with bins for direction, beats, size, burst,
  response, ID and 4 KB page end. Only bins that the IP's contract can
  produce are declared: its own AXI ID, INCR, 4-byte beats, the directions
  the spec allows, 1 to max_burst beats (1 for the single-record Timer_WDT
  and Interrupt_Controller), and OKAY / SLVERR / DECERR. The register test
  makes no AXI traffic, so it prints none of these bins.
- `<ip>` (for example `dma`, `smmu`, `isp`): the IP's own features, declared
  in `tools/soc_subsys/ip/<ip>_tests.svh` with `fcov_bins()` and counted with
  `fcov()`. Job-based IPs also get `job_len` and `job_end` bins.

Merged over the seeds in `sim/testlist.txt`, every declared bin of every
bench is hit (100 %).

## The AXI4 manager-port contract

Every subsystem IP drives the same port (open-ip `soc_ss_axi_engine`): INCR
bursts, AxSIZE 2, 1..16 beats, WSTRB 4'hF, no 4 KB crossing, one read and one
write burst outstanding. The monitor checks each rule by name (`TXN_ID`,
`TXN_SIZE`, `TXN_BURST`, `TXN_LEN`, `TXN_4K`, `TXN_ALIGN`, `TXN_WINDOW`,
`TXN_STRB`, `TXN_WLAST`, `TXN_OUTSTANDING`, `TXN_RESP_ID`, `TXN_RLAST`,
`TXN_HANG`) plus the interface's cycle-level stability / reset / X checks.
The windows rule confines each job's reads to SRC and writes to DST.

The subordinate adds back-pressure, latency and error regions. An errored
read beat returns 0 and an errored write beat is not committed, so the
scoreboards predict error jobs word for word.

## Refreshing from open-ip-portfolio

```bash
OIP_DIR=../open-ip-portfolio python3 tools/gen_soc_subsys_vips.py --all --pack
python3 tools/soc_subsys_index.py      # CSV rows + README section
```

The hand-written parts are `tools/soc_subsys/common/` and
`tools/soc_subsys/ip/<ip>_tests.svh` (reference model, tests and the
`// testlist:` lines); everything else is generated.
