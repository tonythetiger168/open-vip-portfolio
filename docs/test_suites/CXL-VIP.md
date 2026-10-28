# CXL 測試套件（CXL-VIP）

> 由 `tools/gen_test_suite_docs.py` 依 VIP 內容、`func_report.csv` 與 `mutation_report.csv` 自動產生，請勿手動修改。

## 1. 概要

| 項目 | 內容 |
|---|---|
| 類別 | Interconnect |
| 類型 | UVM VIP |
| 功能測試 | 2 個檔案，41 個 check，全部通過 |
| Mutation | 37/37 個 mutant 被偵測（100%） |
| 判定 | **✅ Sufficient**（41 個 check，mutation score 100%） |

## 2. 可執行的功能測試

執行：`python3 tools/run_func_tests.py CXL-VIP`（Icarus Verilog 或 Verilator 5.052）。

### `cxl_mem/tb/func_cxl_mem_tb.sv`

結果：**PASS**（verilator，29 checks）

| # | Check | 類型 |
|---|---|---|
| 1 | MemWr: one Cmp per write, tag and old Meta0-State | check |
| 2 | MemRd: MemData with the written line and Meta0-State | check |
| 3 | completions return out of order, matched by tag | check |
| 4 | MemWrPtl merges by byte enable; poison stored, kept and returned | check |
| 5 | an unpoisoned MemWr clears the poison | check |
| 6 | a read in the same clock as a write to the line sees the write | check |
| 7 | Meta0-State: MemRd / MemInv update it, MemRdData and No-Op do not | check |
| 8 | MemSpecRd: no response, credit returned | check |
| 9 | no error so far | check |
| 10 | MemRdFwd rejected without a response | check |
| 11 | outside the HDM range: poisoned read, write dropped | check |
| 12 | a ninth Req beyond 8 credits: overflow | check |
| 13 | the eight Req within the credits complete | check |
| 14 | every Req credit is returned (the dropped ninth took none) | check |
| 15 | four host NDR credits: four Cmp, two waiting | check |
| 16 | returned NDR credits release the waiting responses | check |
| 17 | every RwD credit is returned | check |
| 18 | a fifth RwD beyond 4 credits: overflow | check |
| 19 | the dropped MemWr did not write; the other four completed | check |
| 20 | no DRS credit: both reads wait | check |
| 21 | one DRS credit: the earliest-due read is sent | check |
| 22 | next credit: the second read | check |
| 23 | no NDR credit: both Cmp wait | check |
| 24 | one NDR credit: the earliest-due Cmp is sent | check |
| 25 | next credit: the second Cmp | check |
| 26 | all %0d NDR and %0d DRS responses as expected | check |
| 27 | reset drops the pending responses and clears the errors | check |
| 28 | RwD with a reserved opcode rejected without a response | check |
| 29 | memory reads zero after reset | check |

### `tb/smoke_func_tb.sv`

結果：**PASS**（verilator，12 checks）

| # | Check | 類型 |
|---|---|---|
| 1 | channel beat during reset is ignored | check |
| 2 | no transfer in progress after reset | check |
| 3 | single-beat transaction counted once | check |
| 4 | single-beat transaction data stored at address | check |
| 5 | channel busy between SOP and EOP | check |
| 6 | multi-beat transaction counted once at EOP | check |
| 7 | channel idle after EOP | check |
| 8 | payload DW0 at addr+0 | check |
| 9 | payload DW1 at addr+4 | check |
| 10 | payload DW2 at addr+8 | check |
| 11 | back-to-back transaction counted | check |
| 12 | later transaction overwrites previous contents | check |

## 3. UVM 測試平台內容

UVM 測試需商用模擬器（VCS / Xcelium / Questa）執行；開源流程只做 elaboration（L1a）。

| 項目 | 數量 | 名稱 |
|---|---|---|
| UVM tests | 5 | `mp_base_test`, `mp_cxl_test`, `mp_error_inject_test`, `mp_power_mgmt_test`, `mp_random_regression_test` |
| Sequences | 10 | `mp_base_sequence`, `mp_back_to_back_sequence`, `mp_stress_sequence`, `mp_corner_case_sequence`, `mp_reset_sequence`, `mp_error_inject_sequence`, `mp_power_mgmt_sequence`, `mp_random_sequence`, `mp_regression_sequence`, `mp_sequence_item` |
| SVA（assert / cover property） | 24 / 21 | `assert_valid_ready`, `assert_sop_eop`, `assert_link_state`, `assert_p_cxl_h2d_valid`, `cover_p_cxl_h2d_valid`, `assert_p_cxl_cache_id`, `cover_p_cxl_cache_id`, `assert_p_cxl_link_state`, `cover_p_cxl_link_state`, `assert_p_cxl_sop_data`, `cover_p_cxl_sop_data`, `assert_p_cxl_no_x_data` … |
| Covergroups / coverpoints | 7 / 20 | |

## 4. 充分度判定與缺口

判定：**✅ Sufficient**（41 個 check，mutation score 100%）。

無已知缺口。

