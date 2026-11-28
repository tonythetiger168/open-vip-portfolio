# USB-PD 測試套件（USB_PD-VIP）

> 由 `tools/gen_test_suite_docs.py` 依 VIP 內容、`func_report.csv` 與 `mutation_report.csv` 自動產生，請勿手動修改。

## 1. 概要

| 項目 | 內容 |
|---|---|
| 類別 | USB |
| 類型 | UVM VIP |
| 功能測試 | 1 個檔案，264 個 check，全部通過 |
| Mutation | 27/27 個 mutant 被偵測（100%） |
| 判定 | **✅ Sufficient**（264 個 check，mutation score 100%） |

## 2. 可執行的功能測試

執行：`python3 tools/run_func_tests.py USB_PD-VIP`（Icarus Verilog 或 Verilator 5.054）。

### `tb/smoke_func_tb.sv`

結果：**PASS**（iverilog，264 checks）

| # | Check | 類型 |
|---|---|---|
| 1 | %s: no packet from the sink | check |
| 2 | %s: type %0d ndo %0d id %0d (got kind %0d crc %0d hdr %04h obj %08h) | check |
| 3 | %s: Hard Reset ordered set | check |
| 4 | %s: nothing sent (%0d packets) | check |
| 5 | %s: GoodCRC starts 3 clocks after EOP (%0d) | check |
| 6 | : waiting for the response | check |
| 7 | : Transition_Sink | check |
| 8 | %s: explicit contract at %0d mV (pos %0d) | check |
| 9 | in reset: disabled, outputs cleared | check |
| 10 | no VBUS: disabled | check |
| 11 | VBUS: Wait_for_Capabilities at vSafe5V | check |
| 12 | SinkWaitCap: 399 clocks, still waiting | check |
| 13 | SinkWaitCap timeout: Hard Reset 1 (pe %0d hr %0d) | check |
| 14 | Hard Reset lasts 20 clocks | check |
| 15 | then Wait_for_Capabilities | check |
| 16 | second timeout: Hard Reset 2 | check |
| 17 | nHardResetCount reached: Error, no third Hard Reset | check |
| 18 | VBUS removed: disabled | check |
| 19 | VBUS back: Wait_for_Capabilities | check |
| 20 | 3 messages received, none bad, MessageIDCounter 1 | check |
| 21 | Ping: still Ready | check |
| 22 | Sink_Capabilities acknowledged: Ready, MessageIDCounter 2 | check |
| 23 | same MessageID again: duplicate, GoodCRC only | check |
| 24 | bad CRC, invalid symbol, odd nibbles, wrong length, over 34 bytes: dropped (%0d) | check |
| 25 | SOP' and SOP'' are for the cable | check |
| 26 | SOP' with one K-code wrong (3 of 4): still SOP' | check |
| 27 | Cable Reset is not for this port | check |
| 28 | Reject: Ready, 20 V contract kept | check |
| 29 | Wait: Ready | check |
| 30 | after Not_Supported: Ready | check |
| 31 | waiting for GoodCRC of Soft_Reset | check |
| 32 | Soft_Reset sent: waiting for Accept, MessageIDCounter 1 | check |
| 33 | Soft_Reset done: Wait_for_Capabilities, contract dropped | check |
| 34 | Soft_Reset accepted: Wait_for_Capabilities | check |
| 35 | nRetryCount = 2 | check |
| 36 | Request never acknowledged: Hard Reset | check |
| 37 | Hard Reset clears MessageIDCounter and the contract | check |
| 38 | GoodCRC on the 2nd try: MessageIDCounter 1 | check |
| 39 | SenderResponse: 99 clocks | check |
| 40 | no Accept within SenderResponse: Hard Reset | check |
| 41 | PSTransition: still waiting | check |
| 42 | no PS_RDY within PSTransition: Hard Reset | check |
| 43 | Transition_Sink | check |
| 44 | data message with the PS_RDY type code in Transition_Sink: Hard Reset | check |
| 45 | no Accept for the Soft_Reset: Hard Reset | check |
| 46 | Hard Reset received: contract dropped, vSafe5V | check |
| 47 | after Hard Reset: Wait_for_Capabilities, one Hard Reset | check |
| 48 | Soft_Reset never acknowledged: Hard Reset | check |
| 49 | VBUS lost: disabled | check |
| 50 | VBUS back: Wait_for_Capabilities | check |
| 51 | reset clears the port | check |
| 52 | reset with VBUS: Wait_for_Capabilities | check |
| 53 | Reject with no prior contract: Wait_for_Capabilities | check |
| 54 | MessageIDCounter after two Not_Supported | check |
| 55 | Not_Supported failed: Send_Soft_Reset | check |
| 56 | Soft_Reset acknowledged: waiting for Accept | check |
| 57 | Soft_Reset done | check |
| 58 | Accept never acknowledged: Hard Reset | check |
| 59 | every symbol the sink sent was a 4b5b code | check |

## 3. UVM 測試平台內容

UVM 測試需商用模擬器（VCS / Xcelium / Questa）執行；開源流程只做 elaboration（L1a）。

| 項目 | 數量 | 名稱 |
|---|---|---|
| UVM tests | 11 | `usb_base_test`, `usb_random_regression_test`, `usb_directed_test`, `usb_hs_test`, `usb_ss_test`, `usb_ssp_test`, `usb_ss20_test`, `usb4_test`, `usb_eusb2_test`, `usb_pd_test`, `usb_pd_link_test` |
| Sequences | 15 | `usb_base_sequence`, `usb_normal_seq`, `usb_error_inject_seq`, `usb_reset_seq`, `usb_back_to_back_seq`, `usb_stress_seq`, `usb_corner_seq`, `usb_sof_seq`, `usb_random_sequence`, `usb_regression_sequence`, `usb_directed_regression_sequence`, `usb_sequence_item`, `usb_pd_item`, `usb_pd_base_seq`, `usb_pd_regression_seq` |
| SVA（assert / cover property） | 9 / 10 | `LBL`, `c_contract`, `c_hr_sent`, `c_hrst`, `c_err`, `c_retry`, `c_dup`, `c_other_sop`, `c_bad`, `c_mismatch`, `c_vbus_loss`, `assert_mac_valid_ready` … |
| Covergroups / coverpoints | 16 / 51 | |

## 4. 充分度判定與缺口

判定：**✅ Sufficient**（264 個 check，mutation score 100%）。

無已知缺口。

