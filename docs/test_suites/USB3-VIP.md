# USB3 測試套件（USB3-VIP）

> 由 `tools/gen_test_suite_docs.py` 依 VIP 內容、`func_report.csv` 與 `mutation_report.csv` 自動產生，請勿手動修改。

## 1. 概要

| 項目 | 內容 |
|---|---|
| 類別 | USB |
| 類型 | UVM VIP |
| 功能測試 | 1 個檔案，107 個 check，全部通過 |
| Mutation | 28/28 個 mutant 被偵測（100%） |
| 判定 | **✅ Sufficient**（107 個 check，mutation score 100%） |

## 2. 可執行的功能測試

執行：`python3 tools/run_func_tests.py USB3-VIP`（Icarus Verilog 或 Verilator 5.054）。

### `tb/smoke_func_tb.sv`

結果：**PASS**（iverilog，107 checks）

| # | Check | 類型 |
|---|---|---|
| 1 | %s (%0d commands) | check |
| 2 | %s: link commands (got %0d, want %0d) | check |
| 3 | %s: one header, HdrSeq %0d, CRC-16 and CRC-5 (got %0d) | check |
| 4 | in reset: RxDetect, outputs cleared | check |
| 5 | no far-end termination: stays in RxDetect | check |
| 6 | far-end termination: Polling.LFPS | check |
| 7 | 3 LFPS bursts are not enough | check |
| 8 | Polling.LFPS waits 128 clocks | check |
| 9 | Polling.LFPS timeout: back to RxDetect | check |
| 10 | 4 bursts, one without SCD2: Polling.Active at Gen1 | check |
| 11 | 7 TS1 stay in Polling.Active | check |
| 12 | 8 TS1/TS2: Polling.Configuration | check |
| 13 | TS1 does not count in Polling.Configuration | check |
| 14 | 7 TS2 stay in Polling.Configuration | check |
| 15 | 8 TS2: U0 | check |
| 16 | no header without a credit; 4 free buffers | check |
| 17 | the header used the credit | check |
| 18 | LGOOD outstanding for 4 clocks: still U0 | check |
| 19 | LGOOD_3 for header 0: Recovery | check |
| 20 | Recovery.Active 8 TS + Recovery.Configuration 8 TS2: U0 | check |
| 21 | LGOOD_0 acknowledges it | check |
| 22 | repeated LGOOD of the last acknowledged header is ignored | check |
| 23 | a good header takes a buffer | check |
| 24 | buffer still busy 3 clocks later | check |
| 25 | freed 4 clocks after it arrived | check |
| 26 | the response waits for a credit | check |
| 27 | CRC-16 error: no buffer | check |
| 28 | headers after LBAD are dropped until LRTY | check |
| 29 | TP for this device counted | check |
| 30 | TP for another address not counted | check |
| 31 | link command with a bad CRC-5 ignored | check |
| 32 | ITP timestamp latched | check |
| 33 | DPP: CRC-32 and length match the DPH | check |
| 34 | DPP with a bad CRC-32 | check |
| 35 | DPP length differs from the DPH | check |
| 36 | DPP without a DPH | check |
| 37 | 4 headers in 4 clocks: no buffer free yet | check |
| 38 | 5th header takes the buffer freed in the same clock | check |
| 39 | header with no free buffer: Recovery | check |
| 40 | app_busy: the 2 buffers stay taken | check |
| 41 | HdrSeq out of order: Recovery | check |
| 42 | LCRD out of order: Recovery | check |
| 43 | 4 credits | check |
| 44 | a 5th credit: Recovery | check |
| 45 | LBAD: the credit comes back, LRTY first | check |
| 46 | 62 clocks without LGOOD: still U0 | check |
| 47 | 64 clocks without LGOOD: Recovery | check |
| 48 | the advertisement acknowledged it: nothing resent | check |
| 49 | Set Link Function and U2 Inactivity Timeout LMPs | check |
| 50 | LPMA: U1 | check |
| 51 | U1 for 47 clocks | check |
| 52 | U2 inactivity timeout 2: U2 after (2 + 1) x 16 clocks | check |
| 53 | LFPS exits U2 through Recovery | check |
| 54 | LGO_U3, LAU, LPMA: U3 | check |
| 55 | U3 does not time out | check |
| 56 | LAU without LPMA for 31 clocks: U0 | check |
| 57 | no LPMA 32 clocks after LAU: Recovery | check |
| 58 | LGO_U0 is not a request | check |
| 59 | LPMA without LAU is ignored | check |
| 60 | a power-management command other than LPMA does not enter Ux | check |
| 61 | Recovery ends the DPP: a later DPP word has no DPH | check |
| 62 | and neither has its CRC word | check |
| 63 | LGOOD beyond the headers sent: Recovery | check |
| 64 | TS1 in U0: Recovery | check |
| 65 | TS1 with Hot Reset: Hot Reset | check |
| 66 | TS2 with Hot Reset still set | check |
| 67 | TS2 without Hot Reset: U0 | check |
| 68 | Recovery.Active waits 128 clocks | check |
| 69 | Recovery timeout: RxDetect | check |
| 70 | every burst with SCD2: Gen2 | check |
| 71 | a credit in the first U0 clock sends the header in that clock | check |
| 72 | Gen2: 1-bit block header corrected, 2-bit and wrong-kind blocks dropped (%0d %0d %0d st%0d free%0d) | check |
| 73 | TS1 in a data block: dropped | check |
| 74 | TS1 with a 1-bit control header: corrected, Recovery | check |
| 75 | Gen2: a DPP word in a dropped block spoils the DPP | check |
| 76 | Gen2: a corrected block keeps the DPP | check |
| 77 | Gen2: a dropped DPP word spoils it even when length and CRC fit the rest | check |
| 78 | reset clears the link | check |

## 3. UVM 測試平台內容

UVM 測試需商用模擬器（VCS / Xcelium / Questa）執行；開源流程只做 elaboration（L1a）。

| 項目 | 數量 | 名稱 |
|---|---|---|
| UVM tests | 11 | `usb_base_test`, `usb_random_regression_test`, `usb_directed_test`, `usb_hs_test`, `usb_ss_test`, `usb_ssp_test`, `usb_ss20_test`, `usb4_test`, `usb_eusb2_test`, `usb_pd_test`, `usb3_link_test` |
| Sequences | 15 | `usb_base_sequence`, `usb_normal_seq`, `usb_error_inject_seq`, `usb_reset_seq`, `usb_back_to_back_seq`, `usb_stress_seq`, `usb_corner_seq`, `usb_sof_seq`, `usb_random_sequence`, `usb_regression_sequence`, `usb_directed_regression_sequence`, `usb_sequence_item`, `usb3_item`, `usb3_base_seq`, `usb3_regression_seq` |
| SVA（assert / cover property） | 9 / 12 | `LBL`, `c_u0_gen1`, `c_u0_gen2`, `c_u1_u2`, `c_u3`, `c_hrst`, `c_lbad`, `c_lrty`, `c_lau`, `c_lxu`, `c_hp_sent`, `c_blk_fix` … |
| Covergroups / coverpoints | 17 / 57 | |

## 4. 充分度判定與缺口

判定：**✅ Sufficient**（107 個 check，mutation score 100%）。

無已知缺口。

