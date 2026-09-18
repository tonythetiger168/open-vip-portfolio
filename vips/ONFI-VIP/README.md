# ONFI (NAND Flash) UVM VIP — Deepened

Multi-protocol memory/storage UVM environment in which the **ONFI (Open NAND
Flash Interface)** protocol is fully deepened: protocol-accurate driver,
waveform-decoding monitor, closed-loop NAND flash DUT model, end-to-end
scoreboard, tiered SVA compliance checker and a 3-covergroup coverage model.
The 7 sibling protocols (DDR, LPDDR, HBM, UFS, UniPro, eMMC, SD) are present
as **minimal stubs** so the original `memory_env` / `memory_coverage_pkg` /
`memory_test_pkg` structure is preserved end-to-end.

## Protocol overview

ONFI 1.0 asynchronous (legacy) NAND interface. All transfers are host-driven
on an 8-bit bidirectional `io` bus with these control signals:

| Signal | Meaning |
|--------|---------|
| `ce_n` | Chip enable (active low) |
| `cle`  | Command latch enable |
| `ale`  | Address latch enable |
| `we_n` | Write enable — cmd/addr/data-in latched on **rising edge** |
| `re_n` | Read enable — flash drives data while low |
| `wp_n` | Write protect (blocks program/erase; FAIL status) |
| `rb_n` | Ready/Busy# (tWB after confirm, tR/tPROG/tBERS/tRST busy time) |

Supported command set (see `onfi_if.onfi_cmd_t`):
`90h` READ ID · `70h` READ STATUS · `00h`+`30h` PAGE READ ·
`80h`+`10h` PAGE PROGRAM · `60h`+`D0h` BLOCK ERASE · `FFh` RESET ·
`ECh` READ PARAMETER · `EFh` SET FEATURES · `EEh` GET FEATURES ·
multi-plane read/program (`READ_MULTI_PLANE`/`PROGRAM_MULTI_PLANE`).

Row address = 3 cycles: column byte, page byte, block byte.

## Architecture

```
tb_top.sv                       clocks/resets, 9 interface instances,
  onfi_nand_model (DUT)         NAND array model: page buffer, sparse array,
                                status reg (FAIL/RDY/WP), R/B# busy timing
  onfi_compliance_checker (SVA) tiered L1–L4 assertions
  onfi_{protocol,timing,error,data_integrity}_checker (SVA modules)
memory_test_pkg                 memory_base_test, memory_coverage_regression_test,
                                onfi_deep_test
memory_env_pkg                  memory_env + memory_scoreboard (exp/obs compare)
  onfi_agent                    sqr + drv + mon (onfi_pkg)
    onfi_driver                 ONFI bus cycles; mirror model; drv_ap = expected
    onfi_monitor                decodes cmd/addr/data phases; item_collected_port = observed
  {ddr,lpddr,hbm,ufs,unipro,emmc,sd}_agent   stub pass-through agents
memory_coverage_pkg             onfi_coverage (3 CGs) + stub coverage classes
```

Closed loop: `onfi_driver` → ONFI bus → `onfi_nand_model` (DUT) → bus →
`onfi_monitor`. The driver publishes **expected** items (with mirror-model
read data) on `drv_ap`; the monitor publishes **observed** items; the
scoreboard matches them (`n_matches`/`n_mismatches`, `UVM_ERROR` on
mismatch or on expected items never observed).

## Sequence library (`onfi_pkg`)

| Sequence | Purpose |
|----------|---------|
| `onfi_base_seq` | helpers (`send_item`, `mk_item`) |
| `onfi_rw_seq` | randomized read/program/erase mix (`num_trans`) |
| `onfi_program_read_seq` | directed erase→program→status→readback (normal) |
| `onfi_erase_seq` | program→erase→verify 0xFF |
| `onfi_reset_seq` | reset between/during ops |
| `onfi_error_seq` | WP# violation injection → FAIL status expected |
| `onfi_b2b_seq` | back-to-back program/read, no idle gap |
| `onfi_stress_seq` | heavy random traffic (`num_trans`) |
| `onfi_corner_seq` | first/last block & page, 00/FF/A5/5A data, SET+GET features |
| `onfi_cov_cmd_seq` | hits every command type |
| `onfi_regression_seq` | randomized mix of all of the above (`num_iters`) |

## SVA compliance (`env/sva/onfi_compliance_checker.sv`)

- **L1 — signal sanity (4):** IO known at cmd/addr latch, WE#/RE# mutex, CLE/ALE mutex
- **L2 — protocol rules (4):** cmd/addr latch requires CE#, data-in/data-out known
- **L3 — timing/busy rules (4):** busy recovers, confirm→busy (tWB), reset recovery (tRST), RE# cycle ends
- **L4 — ONFI command-sequence rules (5):** 90h→addr, 80h→10h, 60h→D0h, 00h→30h, EFh→feature-addr

Auxiliary checkers in `env/vip/onfi/`: `onfi_protocol_checker` (command
encoding legality), `onfi_timing_checker` (tWB/busy/pulse bounds),
`onfi_error_checker` (X-propagation, WP# glitch, error-injection coverage),
`onfi_data_integrity_checker` (IO known at every latch edge).

## Coverage (`onfi_coverage`, 3 covergroups)

1. `onfi_cfg_cg` — cmd type × block/page/length, crosses `cmd×block`, `cmd×len`
2. `onfi_fsm_cg` — command FSM transition bins (prog→read, erase→read, reset→any, b2b, features, …)
3. `onfi_data_cg` — data corner values, status FAIL/RDY bits, WP#-violation × FAIL cross

Sibling protocols keep single-covergroup collectors (stubs; `coverage_target=0`,
reported but not graded).

## Quick start

```sh
cd <this directory>
./run.sh                                   # xrun, default test
SIMULATOR=vcs TESTNAME=onfi_deep_test SEED=1 ./run.sh
SIMULATOR=vsim TESTNAME=memory_coverage_regression_test ./run.sh
```

Tests: `memory_coverage_regression_test` (all protocols; ONFI runs the full
directed library + regression mix), `onfi_deep_test` (ONFI-only deep
regression), `memory_base_test` (infrastructure smoke).

Expected result: `TEST PASSED`, ONFI coverage report at 100% target,
scoreboard `n_mismatches=0`, tiered SVA report printed by the compliance
checker.
