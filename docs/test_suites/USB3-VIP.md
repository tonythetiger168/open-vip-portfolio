# USB3 測試套件（USB3-VIP）

> 由 `tools/gen_test_suite_docs.py` 依 VIP 內容、`func_report.csv` 與 `mutation_report.csv` 自動產生，請勿手動修改。

## 1. 概要

| 項目 | 內容 |
|---|---|
| 類別 | USB |
| 類型 | UVM VIP |
| 功能測試 | 1 個檔案，28 個 check，全部通過 |
| Mutation | 26/30 個 mutant 被偵測（87%） |
| 判定 | **✅ Sufficient**（28 個 check，mutation score 87%） |

## 2. 可執行的功能測試

執行：`python3 tools/run_func_tests.py USB3-VIP`（Icarus Verilog 或 Verilator 5.052）。

### `tb/func_usb3_tb.sv`

結果：**PASS**（iverilog，28 checks）

| # | Check | 類型 |
|---|---|---|
| 1 | RxDetect with no partner | check |
| 2 | far-end receiver detected: Polling | check |
| 3 | TS2 before four TS1 does not complete training | check |
| 4 | one TS2 is not enough | check |
| 5 | 4 TS1 + 2 TS2: link up in U0 | check |
| 6 | U0 entry advertises 4 credits with LCRD | check |
| 7 | good header ACKed with LGOOD | check |
| 8 | header consumes a credit | check |
| 9 | data packet returns the credit with LCRD | check |
| 10 | data packet without a header is not credited | check |
| 11 | four headers use all four credits | check |
| 12 | credit count does not wrap below zero | check |
| 13 | partner LCRDs add credits | check |
| 14 | credit count saturates at 15 | check |
| 15 | credit returned by a data packet also saturates at 15 | check |
| 16 | bad header answered with LBAD | check |
| 17 | bad header enters Recovery | check |
| 18 | one ordered set is not enough to leave Recovery | check |
| 19 | Recovery back to U0 after two ordered sets | check |
| 20 | TS1 in U0 enters Recovery | check |
| 21 | retrained to U0 | check |
| 22 | U0 holds for 250 idle clocks | check |
| 23 | U0 inactivity (256 clocks) enters Recovery | check |
| 24 | Recovery without ordered sets times out to RxDetect | check |
| 25 | partner detected again | check |
| 26 | Polling without training times out to RxDetect | check |
| 27 | trained again | check |
| 28 | reset returns to RxDetect and clears counters | check |

## 3. UVM 測試平台內容

UVM 測試需商用模擬器（VCS / Xcelium / Questa）執行；開源流程只做 elaboration（L1a）。

| 項目 | 數量 | 名稱 |
|---|---|---|
| UVM tests | 10 | `usb_base_test`, `usb_random_regression_test`, `usb_directed_test`, `usb_hs_test`, `usb_ss_test`, `usb_ssp_test`, `usb_ss20_test`, `usb4_test`, `usb_eusb2_test`, `usb_pd_test` |
| Sequences | 12 | `usb_base_sequence`, `usb_normal_seq`, `usb_error_inject_seq`, `usb_reset_seq`, `usb_back_to_back_seq`, `usb_stress_seq`, `usb_corner_seq`, `usb_sof_seq`, `usb_random_sequence`, `usb_regression_sequence`, `usb_directed_regression_sequence`, `usb_sequence_item` |
| SVA（assert / cover property） | 29 / 21 | `assert_p_usb3_pipe_power_down`, `cover_p_usb3_pipe_power_down`, `assert_p_usb3_pipe_rate`, `cover_p_usb3_pipe_rate`, `assert_p_usb3_ltssm_u0`, `cover_p_usb3_ltssm_u0`, `assert_p_usb3_ltssm_recovery`, `cover_p_usb3_ltssm_recovery`, `assert_p_usb3_pipe_txelec`, `cover_p_usb3_pipe_txelec`, `assert_p_usb3_pipe_rxvalid`, `cover_p_usb3_pipe_rxvalid` … |
| Covergroups / coverpoints | 14 / 49 | |

## 4. 充分度判定與缺口

判定：**✅ Sufficient**（28 個 check，mutation score 87%）。

未被偵測的 mutant（測試缺口或等價 mutant）：

- `dut_usb3_smoke_model.sv:57 1'b0 inverted [tx_lc_valid <= 1'b0;]`
- `dut_usb3_smoke_model.sv:85 1'b1 inverted [link_up     <= 1'b1;]`
- `dut_usb3_smoke_model.sv:115 1'b0 inverted [hp_open     <= 1'b0;]`
- `dut_usb3_smoke_model.sv:151 1'b1 inverted [link_up  <= 1'b1;]`

