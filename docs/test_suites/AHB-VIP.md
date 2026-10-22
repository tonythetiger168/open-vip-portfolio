# AHB 測試套件（AHB-VIP）

> 由 `tools/gen_test_suite_docs.py` 依 VIP 內容、`func_report.csv` 與 `mutation_report.csv` 自動產生，請勿手動修改。

## 1. 概要

| 項目 | 內容 |
|---|---|
| 類別 | AMBA |
| 類型 | UVM VIP |
| 功能測試 | 2 個檔案，38 個 check，全部通過 |
| Mutation | 28/28 個 mutant 被偵測（100%） |
| 判定 | **✅ Sufficient**（38 個 check，mutation score 100%） |

## 2. 可執行的功能測試

執行：`python3 tools/run_func_tests.py AHB-VIP`（Icarus Verilog 或 Verilator 5.052）。

### `tb/func_ahb_tb.sv`

結果：**PASS**（iverilog，24 checks）

| # | Check | 類型 |
|---|---|---|
| 1 | reset: HREADYOUT=1, OKAY, HRDATA=0 | check |
| 2 | AXI / stream ports of the shared shell tied off | check |
| 3 | APB ports of the shared shell tied off | check |
| 4 | word 0 reads 0 after power-up | check |
| 5 | word 1023 reads 0 after power-up | check |
| 6 | transfer during reset did not write | check |
| 7 | read of a written byte address returns the written word | XFAIL（模型缺陷） |
| 8 | NONSEQ write reads back | check |
| 9 | SEQ write reads back | check |
| 10 | OKAY response, no wait states | check |
| 11 | HRDATA is 0 outside a read data phase | check |
| 12 | pipelined read after a write returns its own word | check |
| 13 | pipelined write landed | check |
| 14 | IDLE transfers do not write | check |
| 15 | stale HWDATA after the data phase is not written | check |
| 16 | BUSY transfer is ignored | XFAIL（模型缺陷） |
| 17 | error cycle 1: wait state, ERROR, no read data | check |
| 18 | error cycle 2: ERROR completes | check |
| 19 | OKAY again after the error | check |
| 20 | write to the error region has no side effect | check |
| 21 | previous write target untouched by the error transfer | check |
| 22 | error read returns no data | check |
| 23 | reset aborts the data phase | check |
| 24 | 64 random reads match the reference (%0d bad) | check |

### `tb/smoke_func_tb.sv`

結果：**PASS**（iverilog，14 checks）

| # | Check | 類型 |
|---|---|---|
| 1 | write address phase accepted (hreadyout=1) | check |
| 2 | write data phase completed OKAY | check |
| 3 | read data phase OKAY response | check |
| 4 | hreadyout high out of reset | check |
| 5 | hresp OKAY out of reset | check |
| 6 | read data equals written data (NONSEQ) | check |
| 7 | read data equals written data (SEQ) | check |
| 8 | hrdata zero when no read in data phase | check |
| 9 | error region cycle 1: wait state with HRESP=ERROR | check |
| 10 | error region cycle 2: complete with HRESP=ERROR | check |
| 11 | slave recovers to OKAY after error | check |

## 3. UVM 測試平台內容

UVM 測試需商用模擬器（VCS / Xcelium / Questa）執行；開源流程只做 elaboration（L1a）。

| 項目 | 數量 | 名稱 |
|---|---|---|
| UVM tests | 4 | `amba_base_test`, `amba_axi_test`, `amba_ahb_test`, `amba_apb_test` |
| Sequences | 11 | `ahb_base_sequence`, `ahb_single_seq`, `ahb_incr_burst_seq`, `ahb_wrap_burst_seq`, `ahb_back_to_back_seq`, `ahb_error_inject_seq`, `ahb_reset_seq`, `ahb_stress_seq`, `ahb_random_sequence`, `ahb_regression_sequence`, `amba_seq_item` |
| SVA（assert / cover property） | 33 / 16 | `assert_axi_aw`, `assert_axi_wlast`, `assert_axi_bresp`, `assert_ahb_trans`, `assert_apb_en`, `assert_p_ahb_htrans_valid`, `cover_p_ahb_htrans_valid`, `assert_p_ahb_hburst_valid`, `cover_p_ahb_hburst_valid`, `assert_p_ahb_hsize_valid`, `cover_p_ahb_hsize_valid`, `assert_p_ahb_hresp_valid` … |
| Covergroups / coverpoints | 8 / 42 | |

## 4. 充分度判定與缺口

判定：**✅ Sufficient**（38 個 check，mutation score 100%）。

DUT 模型缺陷（XFAIL check，修好模型後會變成 XPASS 提醒移除標記）：

- read of a written byte address returns the written word
- BUSY transfer is ignored

