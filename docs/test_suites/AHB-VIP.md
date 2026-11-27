# AHB 測試套件（AHB-VIP）

> 由 `tools/gen_test_suite_docs.py` 依 VIP 內容、`func_report.csv` 與 `mutation_report.csv` 自動產生，請勿手動修改。

## 1. 概要

| 項目 | 內容 |
|---|---|
| 類別 | AMBA |
| 類型 | UVM VIP |
| 功能測試 | 1 個檔案，222 個 check，全部通過 |
| Mutation | 26/26 個 mutant 被偵測（100%） |
| 判定 | **✅ Sufficient**（222 個 check，mutation score 100%） |

## 2. 可執行的功能測試

執行：`python3 tools/run_func_tests.py AHB-VIP`（Icarus Verilog 或 Verilator 5.054）。

### `tb/smoke_func_tb.sv`

結果：**PASS**（iverilog，222 checks）

| # | Check | 類型 |
|---|---|---|
| 1 | %s: ERROR on beat %0d, burst stopped after %0d beats (expected beat %0d) | check |
| 2 | %s: two-cycle ERROR response (%0d low cycles with ERROR) | check |
| 3 | %s: ERROR beat returns zero data | check |
| 4 | %s: %0d of %0d beats OKAY | check |
| 5 | %s: read lanes match the reference memory | check |
| 6 | %s: HEXOKAY %0d, expected %0d | check |
| 7 | in reset: HREADYOUT high, OKAY, no read data, no EXOKAY | check |
| 8 | HREADYOUT high and HRESP OKAY out of reset | check |
| 9 | no read data or EXOKAY with the bus idle | check |
| 10 | BUSY cycles inside bursts ignored by the slave (%0d) | check |
| 11 | wait states of 1 and 2 cycles (%0d, longest %0d) | check |
| 12 | slave back to OKAY after the ERROR bursts | check |
| 13 | reset again: HREADYOUT high, OKAY, no read data, no EXOKAY | check |

## 3. UVM 測試平台內容

UVM RAL test（`amba_ral_test`：hw_reset / bit_bash / mirror 等）在 Verilator 上以 `python3 tools/run_uvm_tests.py AHB-VIP` 執行（見 [docs/RAL.md](../RAL.md)）；其餘 UVM 測試需商用模擬器（VCS / Xcelium / Questa），開源流程只做 elaboration（L1a）。

| 項目 | 數量 | 名稱 |
|---|---|---|
| UVM tests | 6 | `amba_base_test`, `amba_axi_test`, `amba_ahb_test`, `amba_apb_test`, `amba_ral_test`, `amba_ahb_cov_test` |
| Sequences | 12 | `ahb_base_sequence`, `ahb_single_seq`, `ahb_incr_burst_seq`, `ahb_wrap_burst_seq`, `ahb_back_to_back_seq`, `ahb_error_inject_seq`, `ahb_reset_seq`, `ahb_stress_seq`, `ahb_cov_sweep_seq`, `ahb_random_sequence`, `ahb_regression_sequence`, `amba_seq_item` |
| SVA（assert / cover property） | 40 / 21 | `assert_axi_aw`, `assert_axi_wlast`, `assert_axi_bresp`, `assert_ahb_trans`, `assert_apb_en`, `assert_p_ahb_htrans_valid`, `cover_p_ahb_htrans_valid`, `assert_p_ahb_hburst_valid`, `cover_p_ahb_hburst_valid`, `assert_p_ahb_hsize_valid`, `cover_p_ahb_hsize_valid`, `assert_p_ahb_hresp_valid` … |
| Covergroups / coverpoints | 11 / 56 | |

## 4. 充分度判定與缺口

判定：**✅ Sufficient**（222 個 check，mutation score 100%）。

無已知缺口。

