# eUSB2 測試套件（eUSB2-VIP）

> 由 `tools/gen_test_suite_docs.py` 依 VIP 內容、`func_report.csv` 與 `mutation_report.csv` 自動產生，請勿手動修改。

## 1. 概要

| 項目 | 內容 |
|---|---|
| 類別 | USB |
| 類型 | UVM VIP |
| 功能測試 | 1 個檔案，25 個 check，全部通過 |
| Mutation | 26/30 個 mutant 被偵測（87%） |
| 判定 | **✅ Sufficient**（25 個 check，mutation score 87%） |

## 2. 可執行的功能測試

執行：`python3 tools/run_func_tests.py eUSB2-VIP`（Icarus Verilog 或 Verilator 5.052）。

### `tb/func_eusb2_tb.sv`

結果：**PASS**（iverilog，25 checks）

| # | Check | 類型 |
|---|---|---|
| 1 | reset: non-driving, FS transceiver and termination | check |
| 2 | attached FS idle: normal mode, FS transceiver | check |
| 3 | LS requested: LS transceiver | check |
| 4 | reset request without SE0 is ignored | check |
| 5 | FS bus reset returns to idle without chirp | check |
| 6 | SE0 bus reset | check |
| 7 | HS device answers the reset with chirp K | check |
| 8 | HS selected after host K-J-K-J-K-J | XFAIL（模型缺陷） |
| 9 | model counted five changes after the first host chirp | check |
| 10 | HS selected after a seventh host chirp | check |
| 11 | HS transceiver and HS termination | check |
| 12 | bus reset from HS restarts the chirp | check |
| 13 | each host chirp counts once regardless of its length | check |
| 14 | incomplete chirp times out to FS | check |
| 15 | chirp K after reset | check |
| 16 | device still chirping after 250 clocks | check |
| 17 | no host chirp: FS fallback | check |
| 18 | HS again | check |
| 19 | suspend in HS: non-driving | check |
| 20 | stays suspended on idle J | check |
| 21 | K resume returns to HS | check |
| 22 | suspend at FS | check |
| 23 | resume_req returns to FS idle | check |
| 24 | bus reset wakes a suspended link | check |
| 25 | reset returns to non-driving FS | check |

## 3. UVM 測試平台內容

UVM 測試需商用模擬器（VCS / Xcelium / Questa）執行；開源流程只做 elaboration（L1a）。

| 項目 | 數量 | 名稱 |
|---|---|---|
| UVM tests | 10 | `usb_base_test`, `usb_random_regression_test`, `usb_directed_test`, `usb_hs_test`, `usb_ss_test`, `usb_ssp_test`, `usb_ss20_test`, `usb4_test`, `usb_eusb2_test`, `usb_pd_test` |
| Sequences | 12 | `usb_base_sequence`, `usb_normal_seq`, `usb_error_inject_seq`, `usb_reset_seq`, `usb_back_to_back_seq`, `usb_stress_seq`, `usb_corner_seq`, `usb_sof_seq`, `usb_random_sequence`, `usb_regression_sequence`, `usb_directed_regression_sequence`, `usb_sequence_item` |
| SVA（assert / cover property） | 25 / 17 | `assert_p_eusb2_valid`, `cover_p_eusb2_valid`, `assert_p_eusb2_power_state`, `cover_p_eusb2_power_state`, `assert_p_eusb2_role`, `cover_p_eusb2_role`, `assert_p_eusb2_sop_eop`, `cover_p_eusb2_sop_eop`, `assert_p_eusb2_no_x`, `cover_p_eusb2_no_x`, `assert_p_eusb2_link_up`, `cover_p_eusb2_link_up` … |
| Covergroups / coverpoints | 14 / 49 | |

## 4. 充分度判定與缺口

判定：**✅ Sufficient**（25 個 check，mutation score 87%）。

未被偵測的 mutant（測試缺口或等價 mutant）：

- `dut_eusb2_smoke_model.sv:91 1'b1 inverted [chirp_active <= 1'b1;]`
- `dut_eusb2_smoke_model.sv:114 1'b1 inverted [chirp_active <= 1'b1;]`
- `dut_eusb2_smoke_model.sv:121 1'b1 inverted [hs_mode      <= 1'b1;]`
- `dut_eusb2_smoke_model.sv:124 1'b0 inverted [term_select  <= 1'b0;]`

DUT 模型缺陷（XFAIL check，修好模型後會變成 XPASS 提醒移除標記）：

- HS selected after host K-J-K-J-K-J

