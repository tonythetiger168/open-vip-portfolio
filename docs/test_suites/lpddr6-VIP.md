# lpddr6 測試套件（lpddr6-VIP）

> 由 `tools/gen_test_suite_docs.py` 依 VIP 內容、`func_report.csv` 與 `mutation_report.csv` 自動產生，請勿手動修改。

## 1. 概要

| 項目 | 內容 |
|---|---|
| 類別 | - |
| 類型 | UVM VIP |
| 功能測試 | 1 個檔案，26 個 check，全部通過 |
| Mutation | 24/24 個 mutant 被偵測（100%） |
| 判定 | **✅ Sufficient**（26 個 check，mutation score 100%） |

## 2. 可執行的功能測試

執行：`python3 tools/run_func_tests.py lpddr6-VIP`（Icarus Verilog 或 Verilator 5.052）。

### `lpddr6_vip/tb/func_mem_tb.sv`

結果：**PASS**（iverilog，26 checks）

模型合約與範圍（摘自測試檔頭）：

```text
func_mem_tb.sv -- self-checking functional test for the LPDDR6 memory model
(lpddr6_mem_model). Run: python3 tools/run_func_tests.py lpddr6-VIP

Model contract (from tb_top.sv):
   16 banks = {bg[1:0], ba}. ACT opens a row; WR/RD are BL2 (columns c, c+1).
   Write beats are sampled 1 and 2 clocks after the command. Read beat 0 is
   driven tCL clocks after the command (tCL=0 selects the default CL=6),
   beat 1 a clock later, then dq is released. A read of a closed bank returns
   DEAD_* markers, an unwritten column BAD0_* markers. PRE closes one bank,
   PREA (ras_n=0,cas_n=0,we_n=1) and reset close all banks.
The model indexes storage with row[5:0]/col[5:0]; the test keeps addresses
inside that window (aliasing above it is a documented model limitation).
```

| # | Check | 類型 |
|---|---|---|
| 1 | dq released during reset | check |
| 2 | dq released after reset | check |
| 3 | read of a closed bank returns the closed-bank marker | check |
| 4 | unwritten columns return the unwritten marker | check |
| 5 | unwritten bank 0 / row 0 / column 0 returns the unwritten marker | check |
| 6 | BL2 write then read returns both beats in order | check |
| 7 | dq not driven before CL | check |
| 8 | dq released after the second beat | check |
| 9 | read latency follows tCL=10 | check |
| 10 | tCL=0 falls back to default CL=6 | check |
| 11 | minimum latency tCL=1 | check |
| 12 | second write overwrites the first | check |
| 13 | bank {bg=2,ba=3} holds its own data | check |
| 14 | bank 0 unaffected by bank 11 write | check |
| 15 | another row of the same bank does not alias | check |
| 16 | PRE closes the addressed bank | check |
| 17 | PRE leaves other banks open | check |
| 18 | re-ACT of the row restores access to retained data | check |
| 19 | PREA closes bank 0 | check |
| 20 | PREA closes bank 11 | check |
| 21 | selected NOP does not close banks | check |
| 22 | write with CS_n high is ignored | check |
| 23 | dq released in reset | check |
| 24 | reset closes open rows | check |
| 25 | reset closes every bank (bank 11) | check |
| 26 | array contents survive reset | check |

## 3. UVM 測試平台內容

UVM 測試需商用模擬器（VCS / Xcelium / Questa）執行；開源流程只做 elaboration（L1a）。

| 項目 | 數量 | 名稱 |
|---|---|---|
| UVM tests | 5 | `lpddr6_base_test`, `lpddr6_rw_test`, `lpddr6_back_to_back_test`, `lpddr6_error_test`, `lpddr6_regression_test` |
| Sequences | 11 | `lpddr6_transaction`, `lpddr6_base_sequence`, `lpddr6_write_seq`, `lpddr6_read_seq`, `lpddr6_back_to_back_seq`, `lpddr6_pre_ref_seq`, `lpddr6_error_seq`, `lpddr6_reset_seq`, `lpddr6_corner_seq`, `lpddr6_stress_seq`, `lpddr6_regression_sequence` |
| SVA（assert / cover property） | 39 / 37 | `a_lp6_l1_cmd_known`, `c_lp6_l1_cmd_known`, `a_lp6_l1_addr_known`, `c_lp6_l1_addr_known`, `a_lp6_l1_bank_known`, `c_lp6_l1_bank_known`, `a_lp6_l1_reset_idle`, `c_lp6_l1_reset_idle`, `a_lp6_l2_pre_after_act`, `c_lp6_l2_pre_after_act`, `a_lp6_l2_idle_after_pre`, `c_lp6_l2_idle_after_pre` … |
| Covergroups / coverpoints | 3 / 8 | |

## 4. 充分度判定與缺口

判定：**✅ Sufficient**（26 個 check，mutation score 100%）。

模型未實作的功能（不在測試範圍）：

- the test keeps addresses inside that window (aliasing above it is a documented model limitation).

