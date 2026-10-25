# USB-PD 測試套件（USB_PD-VIP）

> 由 `tools/gen_test_suite_docs.py` 依 VIP 內容、`func_report.csv` 與 `mutation_report.csv` 自動產生，請勿手動修改。

## 1. 概要

| 項目 | 內容 |
|---|---|
| 類別 | USB |
| 類型 | UVM VIP |
| 功能測試 | 1 個檔案，29 個 check，全部通過 |
| Mutation | 27/30 個 mutant 被偵測（90%） |
| 判定 | **✅ Sufficient**（29 個 check，mutation score 90%） |

## 2. 可執行的功能測試

執行：`python3 tools/run_func_tests.py USB_PD-VIP`（Icarus Verilog 或 Verilator 5.052）。

### `tb/func_usb_pd_tb.sv`

結果：**PASS**（iverilog，29 checks）

| # | Check | 類型 |
|---|---|---|
| 1 | unattached: idle, vSafe5V | check |
| 2 | Source_Capabilities ignored without VBUS | check |
| 3 | VBUS present: waiting for Source_Capabilities | check |
| 4 | Source_Capabilities answered with a Request for PDO 2 | check |
| 5 | Accept before GoodCRC is ignored | check |
| 6 | GoodCRC completes the Request | check |
| 7 | PS_RDY before Accept is ignored | check |
| 8 | Accept: waiting for PS_RDY, no contract yet, VBUS unchanged | check |
| 9 | PS_RDY: explicit contract at 9 V | check |
| 10 | GotoMin drops to vSafe5V and waits for PS_RDY | check |
| 11 | PS_RDY after GotoMin re-establishes the contract | check |
| 12 | new capabilities during a contract restart negotiation, contract kept | check |
| 13 | Source_Capabilities during a contract are answered with a Request for PDO 4 | check |
| 14 | VBUS unchanged while the Request is pending | check |
| 15 | Reject: back to waiting, reject_count++ | check |
| 16 | rejected request leaves VBUS at the previous level, contract kept | check |
| 17 | GotoMin answering a Request counts as a reject | check |
| 18 | Request still waiting for GoodCRC after 250 clocks | check |
| 19 | missing GoodCRC times out back to capabilities | check |
| 20 | missing Accept times out | check |
| 21 | missing PS_RDY times out | check |
| 22 | waiting for capabilities has no timeout exit | check |
| 23 | contract at 15 V | check |
| 24 | Hard Reset drops the contract to vSafe5V | check |
| 25 | contract again | check |
| 26 | VBUS loss drops the contract | check |
| 27 | no negotiation while detached | check |
| 28 | detach while a Request is pending withdraws it | check |
| 29 | reset clears contract and counters | check |

## 3. UVM 測試平台內容

UVM 測試需商用模擬器（VCS / Xcelium / Questa）執行；開源流程只做 elaboration（L1a）。

| 項目 | 數量 | 名稱 |
|---|---|---|
| UVM tests | 10 | `usb_base_test`, `usb_random_regression_test`, `usb_directed_test`, `usb_hs_test`, `usb_ss_test`, `usb_ssp_test`, `usb_ss20_test`, `usb4_test`, `usb_eusb2_test`, `usb_pd_test` |
| Sequences | 12 | `usb_base_sequence`, `usb_normal_seq`, `usb_error_inject_seq`, `usb_reset_seq`, `usb_back_to_back_seq`, `usb_stress_seq`, `usb_corner_seq`, `usb_sof_seq`, `usb_random_sequence`, `usb_regression_sequence`, `usb_directed_regression_sequence`, `usb_sequence_item` |
| SVA（assert / cover property） | 27 / 19 | `assert_p_usbpd_sop_valid`, `cover_p_usbpd_sop_valid`, `assert_p_usbpd_message_id`, `cover_p_usbpd_message_id`, `assert_p_usbpd_crc32`, `cover_p_usbpd_crc32`, `assert_p_usbpd_role`, `cover_p_usbpd_role`, `assert_p_usbpd_power_contract`, `cover_p_usbpd_power_contract`, `assert_p_usbpd_hard_reset`, `cover_p_usbpd_hard_reset` … |
| Covergroups / coverpoints | 14 / 49 | |

## 4. 充分度判定與缺口

判定：**✅ Sufficient**（29 個 check，mutation score 90%）。

未被偵測的 mutant（測試缺口或等價 mutant）：

- `dut_usb_pd_smoke_model.sv:52 && flipped [wire msg_ps_rdy  = msg_valid && (msg_type == PD_PS_RDY);]`
- `dut_usb_pd_smoke_model.sv:61 1'b0 inverted [req_valid       <= 1'b0;]`
- `dut_usb_pd_smoke_model.sv:82 1'b0 inverted [req_valid <= 1'b0;]`

