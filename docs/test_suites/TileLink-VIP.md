# TileLink (TL-UL/TL-UH) 測試套件（TileLink-VIP）

> 由 `tools/gen_test_suite_docs.py` 依 VIP 內容、`func_report.csv` 與 `mutation_report.csv` 自動產生，請勿手動修改。

## 1. 概要

| 項目 | 內容 |
|---|---|
| 類別 | Interconnect |
| 類型 | UVM VIP |
| 功能測試 | 1 個檔案，2079 個 check，全部通過 |
| Mutation | 10/10 個 mutant 被偵測（100%） |
| 判定 | **✅ Sufficient**（2079 個 check，mutation score 100%） |

## 2. 可執行的功能測試

執行：`python3 tools/run_func_tests.py TileLink-VIP`（Icarus Verilog 或 Verilator 5.054）。

### `tb/smoke_func_tb.sv`

結果：**PASS**（iverilog，2079 checks）

| # | Check | 類型 |
|---|---|---|
| 1 | op %0d size %0d @%h: D opcode %0d size %0d denied %0d corrupt %0d | check |
| 2 | op %0d size %0d: %0d D beats | check |
| 3 | op %0d param %0d size %0d @%h: data matches the reference | check |
| 4 | D beat on idle source %0d | check |
| 5 | all operations completed | check |
| 6 | in reset: a_ready and d_valid low | check |
| 7 | in reset: D fields are zero | check |
| 8 | 4 operations in flight (max %0d) | check |
| 9 | operations complete out of order (%0d) | check |
| 10 | the device holds a_ready low while it holds 4 operations | check |
| 11 | D payload held while d_ready is low (%0d stalls, %0d bad) | check |
| 12 | a_ready stays low with 4 queued and D stalled (%0d) | check |
| 13 | reset again: a_ready and d_valid low | check |
| 14 | reset again: D fields are zero | check |
| 15 | %0d operations completed | check |
| 16 | a_ready follows the device LFSR (%0d edges, %0d bad) | check |
| 17 | responses start at the predicted edge (%0d edges, %0d bad) | check |

## 3. UVM 測試平台內容

UVM 測試需商用模擬器（VCS / Xcelium / Questa）執行；開源流程只做 elaboration（L1a）。

| 項目 | 數量 | 名稱 |
|---|---|---|
| UVM tests | 5 | `tilelink_base_test`, `tilelink_random_test`, `tilelink_regression_test`, `tilelink_ral_test`, `tilelink_cov_test` |
| Sequences | 12 | `tilelink_base_sequence`, `tilelink_put_get_seq`, `tilelink_partial_seq`, `tilelink_atomic_seq`, `tilelink_outstanding_seq`, `tilelink_denied_seq`, `tilelink_intent_seq`, `tilelink_corrupt_seq`, `tilelink_cov_sweep_seq`, `tilelink_random_sequence`, `tilelink_regression_sequence`, `tilelink_transaction` |
| SVA（assert / cover property） | 22 / 10 | `a_tl_l1_valid_known`, `a_tl_l1_a_known`, `a_tl_l1_d_known`, `a_tl_l1_reset`, `a_tl_l2_a_hold`, `a_tl_l2_a_stable`, `a_tl_l2_d_hold`, `a_tl_l2_d_stable`, `a_tl_l3_opcode`, `a_tl_l3_param`, `a_tl_l3_align`, `a_tl_l3_mask` … |
| Covergroups / coverpoints | 3 / 17 | |

## 4. 充分度判定與缺口

判定：**✅ Sufficient**（2079 個 check，mutation score 100%）。

無已知缺口。

