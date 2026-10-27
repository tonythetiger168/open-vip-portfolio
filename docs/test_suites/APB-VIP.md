# APB 測試套件（APB-VIP）

> 由 `tools/gen_test_suite_docs.py` 依 VIP 內容、`func_report.csv` 與 `mutation_report.csv` 自動產生，請勿手動修改。

## 1. 概要

| 項目 | 內容 |
|---|---|
| 類別 | AMBA |
| 類型 | UVM VIP |
| 功能測試 | 2 個檔案，23 個 check，全部通過 |
| Mutation | 15/15 個 mutant 被偵測（100%） |
| 判定 | **✅ Sufficient**（23 個 check，mutation score 100%） |

## 2. 可執行的功能測試

執行：`python3 tools/run_func_tests.py APB-VIP`（Icarus Verilog 或 Verilator 5.052）。

### `tb/func_apb_tb.sv`

結果：**PASS**（iverilog，12 checks）

| # | Check | 類型 |
|---|---|---|
| 1 | idle bus: PREADY, PSLVERR low, PRDATA 0 | check |
| 2 | registers 0 and 63 read 0 before any write | check |
| 3 | write: no wait state, PSLVERR low | check |
| 4 | read: no wait state, PSLVERR low, data | check |
| 5 | PADDR[7:4] = Fh: exactly two wait states on a write | check |
| 6 | two wait states on a read, data correct | check |
| 7 | PADDR[31:24] = EEh: PSLVERR in the access phase | check |
| 8 | PSLVERR write leaves the register unchanged | check |
| 9 | 400 random transfers with PSTRB match the reference registers | check |
| 10 | PSLVERR only for EEh addresses, wait states only for Fh | check |
| 11 | PREADY, PSLVERR low and PRDATA 0 in every setup phase | check |
| 12 | reset clears the registers written before it | check |

### `tb/smoke_func_tb.sv`

結果：**PASS**（iverilog，11 checks）

| # | Check | 類型 |
|---|---|---|
| 1 | pready low when idle (no psel) | check |
| 2 | normal region write has zero wait states | check |
| 3 | read-back equals written data | check |
| 4 | normal region read has zero wait states | check |
| 5 | pstrb updates only enabled byte lanes | check |
| 6 | wait region write inserts 2 wait states | check |
| 7 | wait region read inserts 2 wait states | check |
| 8 | wait region read-back data correct | check |
| 9 | error region read raises pslverr | check |
| 10 | error region access still completes | check |
| 11 | error region write is suppressed | check |

## 3. UVM 測試平台內容

UVM RAL test（`amba_ral_test`：hw_reset / bit_bash / mirror 等）在 Verilator 上以 `python3 tools/run_uvm_tests.py APB-VIP` 執行（見 [docs/RAL.md](../RAL.md)）；其餘 UVM 測試需商用模擬器（VCS / Xcelium / Questa），開源流程只做 elaboration（L1a）。

| 項目 | 數量 | 名稱 |
|---|---|---|
| UVM tests | 5 | `amba_base_test`, `amba_axi_test`, `amba_apb_test`, `amba_apb_err_test`, `amba_ral_test` |
| Sequences | 11 | `apb_base_sequence`, `apb_write_seq`, `apb_read_seq`, `apb_back_to_back_seq`, `apb_wait_state_seq`, `apb_error_inject_seq`, `apb_reset_seq`, `apb_stress_seq`, `apb_random_sequence`, `apb_regression_sequence`, `amba_seq_item` |
| SVA（assert / cover property） | 31 / 14 | `assert_axi_aw`, `assert_axi_wlast`, `assert_axi_bresp`, `assert_ahb_trans`, `assert_apb_en`, `assert_p_apb_psel_setup`, `cover_p_apb_psel_setup`, `assert_p_apb_penable_1cycle`, `cover_p_apb_penable_1cycle`, `assert_p_apb_pwrite_stable`, `cover_p_apb_pwrite_stable`, `assert_p_apb_paddr_stable` … |
| Covergroups / coverpoints | 8 / 41 | |

## 4. 充分度判定與缺口

判定：**✅ Sufficient**（23 個 check，mutation score 100%）。

無已知缺口。

