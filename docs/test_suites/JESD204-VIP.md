# JESD204C 測試套件（JESD204-VIP）

> 由 `tools/gen_test_suite_docs.py` 依 VIP 內容、`func_report.csv` 與 `mutation_report.csv` 自動產生，請勿手動修改。

## 1. 概要

| 項目 | 內容 |
|---|---|
| 類別 | SerDes |
| 類型 | UVM VIP |
| 功能測試 | 1 個檔案，15 個 check，全部通過 |
| Mutation | 27/30 個 mutant 被偵測（90%） |
| 判定 | **✅ Sufficient**（15 個 check，mutation score 90%） |

## 2. 可執行的功能測試

執行：`python3 tools/run_func_tests.py JESD204-VIP`（Icarus Verilog 或 Verilator 5.052）。

### `tb/func_jesd204_tb.sv`

結果：**PASS**（iverilog，15 checks）

模型合約與範圍（摘自測試檔頭）：

```text
func_jesd204_tb.sv -- self-checking functional test for the JESD204B ADC
transmitter model (jesd204_adc_dut, flattened by smoke/flatten.py).
Run: python3 tools/run_func_tests.py JESD204-VIP

Model contract (from jesd204_defs.sv), one 32-bit lane word per clock,
lane_k marking control characters:
   RESET (zeros) -> SYNC~ low: CGS /K/ = BCBCBCBC -> SYNC~ high: ILAS of
   4 multiframes x 4 words: /R/ (1C), d1, d2, /A/ (7C); in the second
   multiframe d1 = /Q/ (9C) and d2 = config {DID A5, 01, 0001}, else 0.
   Then user data: a ramp from 0 with lane_k low. SYNC~ low during data
   re-enters CGS; SYNC~ high replays ILAS and restarts the ramp.
   inj_ilas_err (sampled at ILAS entry) swaps multiframes 1 and 2.
```

| # | Check | 類型 |
|---|---|---|
| 1 | reset: lane idle (zeros, no K) | check |
| 2 | no CGS before SYNC~ is asserted | check |
| 3 | SYNC~ low: continuous /K/ (K28.5) code group sync | check |
| 4 | ILAS /R/ follows one /K/ after SYNC~ release | check |
| 5 | ILAS: 4 multiframes /R/ .. /A/, /Q/ + config in the second | check |
| 6 | user data: ramp from 0, lane_k low | check |
| 7 | SYNC~ low during data: back to /K/ | check |
| 8 | re-sync replays ILAS and restarts the ramp at 0 | check |
| 9 | inj_ilas_err: /Q/ + config moved to the third multiframe | check |
| 10 | injection is per ILAS: next ILAS is correct | check |
| 11 | 200 further ramp words, consecutive | check |
| 12 | one-clock SYNC~ pulse triggers a full re-initialisation | check |
| 13 | reset clears the lane | check |
| 14 | after reset: idle until SYNC~ | check |
| 15 | inj_ilas_err also applies to the first ILAS after CGS | check |

## 3. UVM 測試平台內容

UVM 測試需商用模擬器（VCS / Xcelium / Questa）執行；開源流程只做 elaboration（L1a）。

| 項目 | 數量 | 名稱 |
|---|---|---|
| UVM tests | 3 | `jesd204_base_test`, `jesd204_random_test`, `jesd204_regression_test` |
| Sequences | 11 | `jesd204_base_sequence`, `jesd204_link_startup_seq`, `jesd204_cgs_seq`, `jesd204_ilas_seq`, `jesd204_user_data_seq`, `jesd204_resync_seq`, `jesd204_error_inject_seq`, `jesd204_reset_seq`, `jesd204_random_sequence`, `jesd204_regression_sequence`, `jesd204_transaction` |
| SVA（assert / cover property） | 19 / 2 | `a_jesd204_l1_clk`, `a_jesd204_l1_rst`, `a_jesd204_l1_state`, `a_jesd204_l1_valid`, `a_jesd204_trans_reset`, `a_jesd204_trans_cgs`, `a_jesd204_trans_ilas`, `a_jesd204_trans_user`, `a_jesd204_trans_sync_re`, `a_jesd204_l3_reset_idle`, `a_jesd204_l3_sync_k`, `a_jesd204_l3_full_cycle` … |
| Covergroups / coverpoints | 3 / 8 | |

## 4. 充分度判定與缺口

判定：**✅ Sufficient**（15 個 check，mutation score 90%）。

未被偵測的 mutant（測試缺口或等價 mutant）：

- `dut_jesd204_adc_dut.sv:29 2 -> 3 [1: return 2;]`
- `dut_jesd204_adc_dut.sv:43 0 -> 1 [mf_cnt         <= 0;]`
- `dut_jesd204_adc_dut.sv:46 1'b0 inverted [ilas_swap      <= 1'b0;]`

