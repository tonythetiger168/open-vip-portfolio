# DRAM timing model (soc/dram_timing)

DRAM channel timing model with named speed presets, for the memory slaves of
a SoC bench. It answers one question for an AXI (or any) memory responder:
when may each beat of this burst go out, given the banks, rows, bus and
refresh state of the DRAM channel behind it. Storage stays in the
responder's own memory model.

The preset names are the ones a socgen spec carries in `memories[].timing`:

| Preset | Family | Device clock | RL / WL | Burst | Banks | Zero-load read, hit / closed bank |
|---|---|---|---|---|---|---|
| `ddr4-2400` | DDR4 x16 | 1200 MHz | CL16 / CWL12 | BL8, 16 B | 8 (2 BG) | 36.7 / 50.4 ns |
| `ddr4-3200` | DDR4 x16 | 1600 MHz | CL22 / CWL16 | BL8, 16 B | 8 (2 BG) | 36.3 / 50.0 ns |
| `lpddr4-3200` | LPDDR4 x16 channel | 1600 MHz | 28 / 14 nCK | BL16, 32 B | 8 | 42.5 / 60.5 ns |
| `lpddr4x-4266` | LPDDR4X x16 channel | 2133 MHz | 36 / 18 nCK | BL16, 32 B | 8 | 40.6 / 58.6 ns |
| `lpddr5-6400` | LPDDR5 x16 channel | 800 MHz CK | 17 / 9 nCK | BL16, 32 B | 16 (4 BG) | 43.8 / 61.8 ns |
| `lpddr5x-8533` | LPDDR5X x16 channel | 1067 MHz CK | 23 / 12 nCK | BL16, 32 B | 16 (4 BG) | 43.4 / 61.4 ns |

Zero-load latency is from the request at the slave port to the first read
data, with the default 20 ns controller + PHY pipeline. At a 500 MHz port
`lpddr4-3200`'s closed-bank read is 31 cycles, which is what the IP camera
specs' `access_cycles: 30` approximates.

Timing values are representative of the JEDEC speed bins (JESD79-4,
JESD209-4, JESD209-5) for an 8 Gb x16 device, not a vendor datasheet. The
LPDDR5 numbers are the same as the phone SoC bench's `lpddr5_pkg`, whose
channel model this package generalises.

## What is modelled

- One open row per bank, 2 KB page, open-page (default) or closed-page.
- Per burst atom: page hit, miss or conflict with tRCD, tRP, tRAS, tRRD,
  tFAW, tWR, tRTP, tWTR, read-to-write turnaround, tCCD, RL / WL and the
  burst time on the data bus.
- Refresh: all-bank (tREFI / tRFCab) for every family; per-bank (tRFCpb,
  the banks in turn) for LPDDR4 and LPDDR5. Channels have their refresh
  phase staggered by `channel`.
- Requests are served in arrival order (no FR-FCFS); posted or non-posted
  write responses.
- Address map: channel-select bits squeezed out (`chan_lsb`, `chan_bits`),
  then column, bank (bank group on top), row.

## Files

| File | Content |
|---|---|
| `src/dram_timing_pkg.sv` | `dram_timing_cfg` (presets, geometry, mapping) and `dram_timing_model` (bank / bus / refresh state) |
| `tests/dram_timing_tb.sv` | self-checking test, 35 checks |
| `run.sh` | builds and runs the test with Verilator 5 |

No UVM or bus package is needed, so the classes drop into a UVM slave
driver, a socgen memory model or a plain testbench.

## Use

```systemverilog
import dram_timing_pkg::*;

dram_timing_cfg   c = dram_timing_cfg::preset("lpddr4-3200");   // null if unknown
dram_timing_model m;
c.channel   = ch;           // refresh stagger
c.chan_bits = 1;            // two controller ports interleaved ...
c.chan_lsb  = 12;           // ... on 4 KB
c.tck_port  = 2.0;          // slave port clock, ns
m = new(c);

// a read burst arriving now: beat i may leave at av[i]
real av[], done;
m.plan($realtime, 0, araddr, arlen + 1, 1 << arsize, av, done);
foreach (av[i]) begin
  repeat (m.cycles_until($realtime, av[i])) @(posedge aclk);
  // drive R beat i
end

// a write burst once its data is in: B at write_ack()
m.plan($realtime, 1, awaddr, awlen + 1, 1 << awsize, av, done);
repeat (m.cycles_until($realtime, m.write_ack($realtime, done))) @(posedge aclk);
// drive B
```

In a UVM bench the same calls go in the slave driver's read-start /
write-done hooks, the way `lpddr5_slave_driver` in the phone bench does.
`m.n_page[]`, `m.n_ref_stall`, `m.hit_rate()` and `last_page` /
`last_bank` / `last_stalled` feed coverage and the latency report.

## Run

```
bash run.sh        # FUNC_PASS checks=35, then the preset latency table
```
