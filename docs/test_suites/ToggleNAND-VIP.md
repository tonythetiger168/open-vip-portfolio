# Toggle Mode NAND 測試套件（ToggleNAND-VIP）

> 由 `tools/gen_test_suite_docs.py` 依 VIP 內容、`func_report.csv` 與 `mutation_report.csv` 自動產生，請勿手動修改。

## 1. 概要

| 項目 | 內容 |
|---|---|
| 類別 | Storage |
| 類型 | UVM VIP |
| 功能測試 | 1 個檔案，32 個 check，全部通過 |
| Mutation | 10/12 個 mutant 被偵測（83%） |
| 判定 | **✅ Sufficient**（32 個 check，mutation score 83%） |

## 2. 可執行的功能測試

執行：`python3 tools/run_func_tests.py ToggleNAND-VIP`（Icarus Verilog 或 Verilator 5.052）。

### `tb/func_tnand_tb.sv`

結果：**PASS**（verilator，32 checks）

模型合約與範圍（摘自測試檔頭）：

```text
func_tnand_tb.sv -- self-checking functional test for the Toggle-mode NAND
model (tnand_nand_model, flattened by smoke/flatten.py).
Run: python3 tools/run_func_tests.py ToggleNAND-VIP

Model contract (from tnand_defs.sv and tnand_driver.svh):
   commands / 5 address bytes latched on WE# rising (CLE / ALE), address
   bytes sent LSB first as the VIP driver does; program data captured on
   DQS rising with host_dq_oe; read data on each RE# low pulse with DQS
   high. 80h-10h program (busy 16 clk), 00h-30h read (busy 8), 60h-D0h
   erase of the 32-byte page (busy 24). 70h status: [6] ready, [0] fail
   (READ/PROG/ERASE while busy, or an undefined opcode); FFh reset aborts.

Model defects recorded as XFAIL: the address register shifts each byte in
at the bottom, so the first (column LSB) byte becomes the MSB; data
programmed at the start of a page cannot be read at a column offset, and
erase misses bytes programmed at a non-zero column. Data are single data
rate (one byte per DQS / RE# cycle), and in status mode the NAND drives
DQ whenever CE# is low, also while the host drives a command. The status
concatenation is 7 bits wide, so READY lands in bit 5 instead of bit 6;
the other checks accept either bit (st_ok).
```

| # | Check | 類型 |
|---|---|---|
| 1 | reset: ready, DQ / DQS not driven | check |
| 2 | READ STATUS 70h: ready, no fail | check |
| 3 | status READY flag in bit 6 (40h) | XFAIL（模型缺陷） |
| 4 | program 80h-10h: R/B# low for 16 clocks | check |
| 5 | status after program: ready, pass | check |
| 6 | read 00h-30h: R/B# low for 8 clocks | check |
| 7 | read returns the 16 programmed bytes | check |
| 8 | bytes past the programmed data read FFh | check |
| 9 | NAND drives DQS high with every read byte | check |
| 10 | DQ / DQS released after RE# rises | check |
| 11 | full 32-byte page programmed and read back | check |
| 12 | other page unaffected | check |
| 13 | erase 60h-D0h: R/B# low for 24 clocks | check |
| 14 | erased page reads FFh | check |
| 15 | erase leaves the next page intact | check |
| 16 | read at column 5 returns bytes 5..8 of the page | XFAIL（模型缺陷） |
| 17 | erase clears data programmed at a non-zero column | XFAIL（模型缺陷） |
| 18 | DQS before the 5th address byte or without host_dq_oe is ignored | check |
| 19 | byte captured on the DQS rising edge | check |
| 20 | byte captured on the DQS falling edge (DDR) | XFAIL（模型缺陷） |
| 21 | busy after program confirm | check |
| 22 | READ latched while busy sets the fail bit | check |
| 23 | the program in progress still completes | check |
| 24 | next READ clears the fail bit | check |
| 25 | undefined opcode sets the fail bit | check |
| 26 | RESET (FFh) ends the busy period | check |
| 27 | status after RESET: ready, no fail | check |
| 28 | 30h after RESET (no 00h + address) does not start a read | check |
| 29 | 10h without 80h does not start a program | check |
| 30 | program aborted by RESET is not committed | check |
| 31 | NAND does not drive DQ while the host drives a command | XFAIL（模型缺陷） |
| 32 | reset pin: ready, DQ released | check |

## 3. UVM 測試平台內容

UVM 測試需商用模擬器（VCS / Xcelium / Questa）執行；開源流程只做 elaboration（L1a）。

| 項目 | 數量 | 名稱 |
|---|---|---|
| UVM tests | 3 | `tnand_base_test`, `tnand_random_test`, `tnand_regression_test` |
| Sequences | 11 | `tnand_base_sequence`, `tnand_read_seq`, `tnand_program_seq`, `tnand_erase_seq`, `tnand_status_seq`, `tnand_busy_violation_seq`, `tnand_illegal_cmd_seq`, `tnand_reset_seq`, `tnand_random_sequence`, `tnand_regression_sequence`, `tnand_transaction` |
| SVA（assert / cover property） | 21 / 2 | `a_tnand_l1_clk`, `a_tnand_l1_rst`, `a_tnand_l1_state`, `a_tnand_l1_valid`, `a_tnand_trans_idle`, `a_tnand_trans_cmd_latch`, `a_tnand_trans_addr_latch`, `a_tnand_trans_data_write`, `a_tnand_trans_data_read`, `a_tnand_trans_status_read`, `a_tnand_l3_reset_idle`, `a_tnand_l3_no_stuck` … |
| Covergroups / coverpoints | 3 / 10 | |

## 4. 充分度判定與缺口

判定：**✅ Sufficient**（32 個 check，mutation score 83%）。

未被偵測的 mutant（測試缺口或等價 mutant）：

- `dut_tnand_nand_model.sv:109 1'b1 inverted [we_n_d <= 1'b1; re_n_d <= 1'b1; dqs_d <= 1'b0;]`
- `dut_tnand_nand_model.sv:147 == flipped [re_n_d == 1'b1 && vif_re_n == 1'b0) begin]`

DUT 模型缺陷（XFAIL check，修好模型後會變成 XPASS 提醒移除標記）：

- status READY flag in bit 6 (40h)
- read at column 5 returns bytes 5..8 of the page
- erase clears data programmed at a non-zero column
- byte captured on the DQS falling edge (DDR)
- NAND does not drive DQ while the host drives a command

