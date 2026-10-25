# CSE 測試套件（CSE-VIP）

> 由 `tools/gen_test_suite_docs.py` 依 VIP 內容、`func_report.csv` 與 `mutation_report.csv` 自動產生，請勿手動修改。

## 1. 概要

| 項目 | 內容 |
|---|---|
| 類別 | MIPI |
| 類型 | UVM VIP |
| 功能測試 | 1 個檔案，34 個 check，全部通過 |
| Mutation | 25/25 個 mutant 被偵測（100%） |
| 判定 | **✅ Sufficient**（34 個 check，mutation score 100%） |

## 2. 可執行的功能測試

執行：`python3 tools/run_func_tests.py CSE-VIP`（Icarus Verilog 或 Verilator 5.052）。

### `tb/func_cse_tb.sv`

結果：**PASS**（iverilog，34 checks）

| # | Check | 類型 |
|---|---|---|
| 1 | reset: not ready, no irq, bus released | check |
| 2 | reset: side-band acknowledges low | check |
| 3 | ready in IDLE after reset | check |
| 4 | NOP returns 00 | check |
| 5 | response starts 5 clocks after the command (got %0d) | check |
| 6 | irq held 5 clocks with a stable response byte (got %0d) | check |
| 7 | WR_REG echoes the written nibble | check |
| 8 | RD_REG returns register 3 | check |
| 9 | RD_REG returns register 7 | check |
| 10 | unwritten register reads 00 | check |
| 11 | WR_MEM echoes the written nibble | check |
| 12 | RD_MEM returns memory word 3 | check |
| 13 | memory write does not touch the register file | check |
| 14 | SET_CFG echoes the value | check |
| 15 | GET_CFG reads it back | check |
| 16 | STATUS: ready, no error | check |
| 17 | command 7 returns 00 without error | check |
| 18 | illegal command returns EE | check |
| 19 | STATUS reports the sticky error | check |
| 20 | lowest illegal command (10) returns EE | check |
| 21 | RESET returns A5 | check |
| 22 | RESET clears the sticky error | check |
| 23 | RESET clears the register file | check |
| 24 | RESET clears the memory | check |
| 25 | RESET clears the configuration | check |
| 26 | command 10 alone sets the sticky error | check |
| 27 | ready drops once a command is accepted | check |
| 28 | operand changes while busy are ignored | check |
| 29 | target drives cse_data only while cse_irq is high | check |
| 30 | side-band requests acknowledged | check |
| 31 | acknowledges drop | check |
| 32 | in response window before reset | check |
| 33 | reset ends the response and releases the bus | check |
| 34 | reset clears the register file | check |

## 3. UVM 測試平台內容

UVM 測試需商用模擬器（VCS / Xcelium / Questa）執行；開源流程只做 elaboration（L1a）。

| 項目 | 數量 | 名稱 |
|---|---|---|
| UVM tests | 10 | `mipi_base_test`, `mipi_csi2_test`, `mipi_dsi_test`, `mipi_dphy_test`, `mipi_cphy_test`, `mipi_mphy_test`, `mipi_unipro_test`, `mipi_digrf_test`, `mipi_hsi_test`, `mipi_cse_test` |
| Sequences | 11 | `mipi_seq_item`, `cse_base_seq`, `cse_wr_reg_seq`, `cse_rd_seq`, `cse_mem_seq`, `cse_error_seq`, `cse_reset_seq`, `cse_b2b_seq`, `cse_stress_seq`, `cse_corner_seq`, `cse_regression_seq` |
| SVA（assert / cover property） | 24 / 17 | `assert_dphy_hs`, `assert_cphy_sym`, `assert_mphy_gear`, `assert_unipro_tc`, `assert_digrf`, `assert_hsi_wake`, `assert_cse_cmd`, `assert_l1_cmd_known`, `cover_l1_cmd_known`, `assert_l1_data_known`, `cover_l1_data_known`, `assert_l1_ctrl_known` … |
| Covergroups / coverpoints | 5 / 22 | |

## 4. 充分度判定與缺口

判定：**✅ Sufficient**（34 個 check，mutation score 100%）。

無已知缺口。

