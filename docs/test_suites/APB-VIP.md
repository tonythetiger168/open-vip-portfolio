# APB 測試套件（APB-VIP）

> 由 `tools/gen_test_suite_docs.py` 依 VIP 內容、`func_report.csv` 與 `mutation_report.csv` 自動產生，請勿手動修改。

## 1. 概要

| 項目 | 內容 |
|---|---|
| 類別 | AMBA |
| 類型 | UVM VIP |
| 功能測試 | 1 個檔案，792 個 check，全部通過 |
| Mutation | 24/24 個 mutant 被偵測（100%） |
| 判定 | **✅ Sufficient**（792 個 check，mutation score 100%） |

## 2. 可執行的功能測試

執行：`python3 tools/run_func_tests.py APB-VIP`（Icarus Verilog 或 Verilator 5.054）。

### `tb/smoke_func_tb.sv`

結果：**PASS**（iverilog，792 checks）

| # | Check | 類型 |
|---|---|---|
| 1 | PREADY never came | check |
| 2 | %s: PSLVERR %0d, expected %0d | check |
| 3 | %s: PBUSER echoes PAUSER[3:0] | check |
| 4 | %s: PRDATA %h / PRUSER %h, expected %h / %h | check |
| 5 | %s: %0d wait states, expected %0d | check |
| 6 | in reset: no PREADY, PSLVERR or PRDATA | check |
| 7 | write | check |
| 8 | read-back of every register | check |
| 9 | random wait states 0/1/2: %0d/%0d/%0d, longest %0d | check |
| 10 | partial-strobe write | check |
| 11 | read-back after partial strobe | check |
| 12 | wait region write | check |
| 13 | wait region read | check |
| 14 | back-to-back write 1 | check |
| 15 | back-to-back write 2 | check |
| 16 | back-to-back read 1 | check |
| 17 | back-to-back read 2 | check |
| 18 | back-to-back wait region | check |
| 19 | error-region write | check |
| 20 | error-region read: zero data | check |
| 21 | register behind the error region untouched | check |
| 22 | secure register write, PPROT %0d | check |
| 23 | secure register read, PPROT %0d | check |
| 24 | secure register read-back (secure) | check |
| 25 | non-secure write above the secure registers | check |
| 26 | non-secure write below the secure registers | check |
| 27 | non-secure read above | check |
| 28 | non-secure read below | check |
| 29 | write with check signal %0d wrong | check |
| 30 | read with check signal %0d wrong | check |
| 31 | read: write-data checks ignored | check |
| 32 | back-to-back, good parity | check |
| 33 | back-to-back, PADDRCHK wrong | check |
| 34 | back-to-back read 1 | check |
| 35 | back-to-back read 2 | check |
| 36 | 7 idle clocks: still awake | check |
| 37 | 8 idle clocks: asleep, one more wait | check |
| 38 | asleep, PWAKEUP 1 clock early | check |
| 39 | asleep, PWAKEUP 3 clocks early | check |
| 40 | asleep, write | check |
| 41 | asleep, read-back | check |
| 42 | PWAKEUP held high: awake | check |
| 43 | asleep, normal register: one more wait | check |
| 44 | after reset: awake, register 0 | check |
| 45 | after reset: register and PRUSER 0 | check |
| 46 | PREADYCHK / PSLVERRCHK / PRDATACHK odd parity on %0d clocks (%0d bad) | check |

## 3. UVM 測試平台內容

UVM RAL test（`amba_ral_test`：hw_reset / bit_bash / mirror 等）在 Verilator 上以 `python3 tools/run_uvm_tests.py APB-VIP` 執行（見 [docs/RAL.md](../RAL.md)）；其餘 UVM 測試需商用模擬器（VCS / Xcelium / Questa），開源流程只做 elaboration（L1a）。

| 項目 | 數量 | 名稱 |
|---|---|---|
| UVM tests | 7 | `amba_base_test`, `amba_axi_test`, `amba_apb_test`, `amba_apb_err_test`, `amba_ral_test`, `amba_apb_strb_test`, `amba_apb_cov_test` |
| Sequences | 13 | `apb_base_sequence`, `apb_write_seq`, `apb_read_seq`, `apb_back_to_back_seq`, `apb_wait_state_seq`, `apb_error_inject_seq`, `apb_reset_seq`, `apb_stress_seq`, `apb_partial_write_seq`, `apb_cov_sweep_seq`, `apb_random_sequence`, `apb_regression_sequence`, `amba_seq_item` |
| SVA（assert / cover property） | 36 / 19 | `assert_axi_aw`, `assert_axi_wlast`, `assert_axi_bresp`, `assert_ahb_trans`, `assert_apb_en`, `assert_p_apb_psel_setup`, `cover_p_apb_psel_setup`, `assert_p_apb_penable_1cycle`, `cover_p_apb_penable_1cycle`, `assert_p_apb_pwrite_stable`, `cover_p_apb_pwrite_stable`, `assert_p_apb_paddr_stable` … |
| Covergroups / coverpoints | 11 / 49 | |

## 4. 充分度判定與缺口

判定：**✅ Sufficient**（792 個 check，mutation score 100%）。

無已知缺口。

