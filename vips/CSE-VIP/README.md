# CSE (MIPI Command/Status Engine) UVM VIP — Deepened

MIPI multi-protocol UVM VIP (CSI-2 / DSI / D-PHY / C-PHY / M-PHY / UniPro /
DigRF / HSI / CSE) in which the **CSE 2.0 command/response channel** is fully
deepened: handshake-accurate driver, bus-decoding monitor, closed-loop CSE
command-processor DUT model, end-to-end scoreboard, tiered SVA compliance
checker and a 3-covergroup coverage model. The 8 sibling protocols retain
their original interfaces and get **minimal checker stubs** so the original
`mipi_env` / Makefile structure is preserved.

## Protocol overview (CSE channel)

CSE is a simple command/response interface on `mipi_vip_if`:

| Signal | Direction | Meaning |
|--------|-----------|---------|
| `cse_valid` | host → target | command valid |
| `cse_ready` | target → host | target accepts command when high with valid |
| `cse_cmd[3:0]` | host → target | command opcode |
| `cse_data[7:0]` | bidirectional | operand (host) / response byte (target, during IRQ) |
| `cse_irq` | target → host | response window (4 cycles), data valid on `cse_data` |

Command set (`cse_cmd_e`): `0` NOP · `1` RD_REG · `2` WR_REG · `3` RD_MEM ·
`4` WR_MEM · `5` GET_STATUS · `6` SOFT_RESET · `7` IRQ_ACK · `8` SET_CFG ·
`9` GET_CFG · `10..15` reserved → error response `0xEE` + sticky ERR status.

Operand byte: `[7:4]` = address (16 registers / 16 memory bytes),
`[3:0]` = write data. Target response latency ≈ 6 cycles after accept.

## Architecture

```
tb/top_tb.sv                  clk/rst, mipi_vip_if instance, config_db, run_test
  mipi_dut (DUT)              CSE command processor: regfile/mem/cfg, sticky ERR,
                              busy + response FSM; generic-lane ready echo
  cse_compliance_checker      tiered SVA L1–L4 (module)
tests/mipi_tests.sv           10 tests; mipi_cse_test runs the deep library
env/mipi_env.sv               mipi_env: agent + cov + sb + 9 protocol checkers
vip/base/mipi_vip_pkg.sv      mipi_txn/seq_item, mipi_driver (CSE handshake + drv_ap),
                              mipi_monitor (decode), mipi_agent, mipi_cov (3 CGs),
                              mipi_sb (exp/obs), CSE sequence library
vip/<proto>/<proto>_protocol_checker.sv   8 stub checkers + deepened cse checker
```

Closed loop: `mipi_driver` → `cse_*` bus → `mipi_dut` → bus → `mipi_monitor`.
Driver publishes **expected** (mirror-model response) on `drv_ap` →
`sb.exp_ap`; monitor publishes **observed** → `sb.obs_ap`; scoreboard counts
`n_matches`/`n_mismatches` and raises `UVM_ERROR` on mismatch or
never-observed expected items.

## Sequence library (`mipi_vip_pkg`)

| Sequence | Purpose |
|----------|---------|
| `cse_base_seq` | helpers (`send_item`, `mk_cse`) |
| `cse_wr_reg_seq` | register write + readback (normal) |
| `cse_rd_seq` | NOP / status / full register read sweep |
| `cse_mem_seq` | memory write + readback sweep |
| `cse_error_seq` | reserved opcodes 10–15 → 0xEE + sticky ERR + reset |
| `cse_reset_seq` | ops → SOFT_RESET → cleared-state verify |
| `cse_b2b_seq` | back-to-back WR/RD, no idle gap |
| `cse_stress_seq` | random legal command mix (`num_trans`) |
| `cse_corner_seq` | first/last addr, 00/FF data, cfg, IRQ_ACK, NOP |
| `cse_regression_seq` | randomized mix of the above (`num_iters`) |

## SVA compliance (`rtl/sva/cse_compliance_checker.sv`)

- **L1 — signal sanity (4):** cmd/operand/control/response known
- **L2 — handshake rules (4):** valid stable while stalled, cmd stable, ready eventually, valid drops after accept
- **L3 — response/IRQ timing (4):** IRQ after accept, IRQ width bounded, no command during response, ready recovers
- **L4 — protocol rules (5):** RD_REG valid response, WR_REG echo, SOFT_RESET→0xA5, reserved→0xEE, GET_CFG response

Plus the UVM `cse_protocol_checker` (runtime checks: no overlapping commands,
IRQ requires outstanding command, 32-cycle response timeout) with its own
command/IRQ/valid covergroup.

## Coverage (`mipi_cov`, 3 covergroups)

1. `cg_mipi` — original MAC/PHY coverage: protocol × packet × VC × lane × mode (crosses `pkt×vc`, `prot×lane`)
2. `cg_cse_cmd` — CSE opcode × operand-address × legal/reserved (crosses `cmd×addr`, `cmd×err`)
3. `cg_cse_resp` — response byte corners (0x00/0xFF/0xEE/0xA5) × write-data × err (cross `resp×err`)

## Quick start

```sh
cd sim && make            # compile (vlogan)  — scripts/Makefile, untouched
cd sim && make run TEST=mipi_cse_test       # run the deepened CSE test
cd sim && make run TEST=mipi_base_test      # infrastructure smoke
```

Other tests (`mipi_csi2_test` … `mipi_hsi_test`) remain smoke tests; their
checkers are stubs. Expected result: `TEST PASSED`,
`n_matches>0, n_mismatches=0`, tiered SVA report, coverage report.
