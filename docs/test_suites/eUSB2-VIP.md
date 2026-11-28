# eUSB2 測試套件（eUSB2-VIP）

> 由 `tools/gen_test_suite_docs.py` 依 VIP 內容、`func_report.csv` 與 `mutation_report.csv` 自動產生，請勿手動修改。

## 1. 概要

| 項目 | 內容 |
|---|---|
| 類別 | USB |
| 類型 | UVM VIP |
| 功能測試 | 1 個檔案，88 個 check，全部通過 |
| Mutation | 29/29 個 mutant 被偵測（100%） |
| 判定 | **✅ Sufficient**（88 個 check，mutation score 100%） |

## 2. 可執行的功能測試

執行：`python3 tools/run_func_tests.py eUSB2-VIP`（Icarus Verilog 或 Verilator 5.054）。

### `tb/smoke_func_tb.sv`

結果：**PASS**（iverilog，88 checks）

| # | Check | 類型 |
|---|---|---|
| 1 | native: SE0 for 16 clocks -> RESET | check |
| 2 | RESET lasts 8 clocks, then CHIRP | check |
| 3 | device chirp K, then HS_WAIT | check |
| 4 | chirp K ends | check |
| 5 | 3 host K-J pairs: L0 at HS | check |
| 6 | in reset: DISC, nothing sent | check |
| 7 | after rst_n: DISC, CTRL = lpm_en | check |
| 8 | J without attach: DISC | check |
| 9 | 3 clocks of J: not yet attached | check |
| 10 | J for 4 clocks with attach: ATTACHED | check |
| 11 | ATTACHED: packets and LPM ignored before reset | check |
| 12 | attach low: DISC, counted | check |
| 13 | re-attach | check |
| 14 | 15 clocks of SE0: no reset yet | check |
| 15 | one reset | check |
| 16 | packets every 21 clocks keep L0 | check |
| 17 | 23 idle clocks: L0 | check |
| 18 | 24 idle clocks: L2 (HS kept) | check |
| 19 | native mode: SE1 is not a control message | check |
| 20 | 3 clocks of K: no resume | check |
| 21 | K for 4 clocks: RESUME | check |
| 22 | L2 resume lasts 8 clocks | check |
| 23 | back to L0 at HS | check |
| 24 | LPM while busy: NYET, stay L0 | check |
| 25 | LPM answer is one clock | check |
| 26 | LPM: ACK, L1 | check |
| 27 | L1 does not time out to L2 | check |
| 28 | remote wake allowed by the LPM token: RWAKE | check |
| 29 | device K for 6 clocks, then L0 | check |
| 30 | wake K ends | check |
| 31 | second LPM: L1 | check |
| 32 | remote wake not allowed by this LPM: stays L1 | check |
| 33 | host K: RESUME | check |
| 34 | L1 resume with BESL 5: 14 clocks | check |
| 35 | L0 after 4 + 2 * BESL clocks | check |
| 36 | idle: L2 again | check |
| 37 | remote wake not enabled: stays L2 | check |
| 38 | DEVICE_REMOTE_WAKEUP set: RWAKE from L2 | check |
| 39 | L0 after the wake | check |
| 40 | SE0 in L1: reset, HS cleared | check |
| 41 | no HS capability: L0 at FS without a chirp | check |
| 42 | no host chirp: still waiting after 47 clocks | check |
| 43 | 48 clocks without a host chirp: L0 at FS | check |
| 44 | 1-clock K/J levels: FS | check |
| 45 | reset counted | check |
| 46 | SE0 held through RESET into L0: no second reset | check |
| 47 | disconnect in L0: DISC | check |
| 48 | repeater mode: attach | check |
| 49 | repeater mode: SE0 is not a reset | check |
| 50 | CM.RESET not decoded before its 4-clock end gap | check |
| 51 | CM.RESET: RESET | check |
| 52 | repeater: HS after the chirp | check |
| 53 | CM.SUSPEND: L2 | check |
| 54 | repeater mode: K does not resume | check |
| 55 | CM.RESUME: RESUME | check |
| 56 | L0 | check |
| 57 | CM.RESUME in L0: bad control message | check |
| 58 | 6 pulses: unknown control message | check |
| 59 | long SE1 pulses count once each: CM.SUSPEND | check |
| 60 | resumed | check |
| 61 | RAP read ID: 0xE2 | check |
| 62 | RAP answer is one clock | check |
| 63 | RAP read STATUS: {hs, L0} | check |
| 64 | write to the read-only ID: rejected | check |
| 65 | write to STATUS: rejected | check |
| 66 | address 9: rejected | check |
| 67 | scratch register write / read | check |
| 68 | tuning register keeps 6 bits | check |
| 69 | access 8 clocks after CM.RAP: dropped | check |
| 70 | access without CM.RAP: ignored | check |
| 71 | CTRL write keeps 3 bits | check |
| 72 | LPM disabled: STALL | check |
| 73 | CTRL = lpm_en \| rwake_en | check |
| 74 | CTRL.rwake_en: remote wake from L2 | check |
| 75 | LPM ACK: L1 | check |
| 76 | CM.RESUME from L1 | check |
| 77 | BESL 0: 4 clocks | check |
| 78 | CM.RESET | check |
| 79 | CM.SUSPEND during RESET: bad control message | check |
| 80 | CTRL.hs_dis: L0 at FS without a chirp | check |
| 81 | CM.RESET from L1 | check |
| 82 | registers survive a bus reset | check |
| 83 | rst_n clears everything | check |

## 3. UVM 測試平台內容

UVM 測試需商用模擬器（VCS / Xcelium / Questa）執行；開源流程只做 elaboration（L1a）。

| 項目 | 數量 | 名稱 |
|---|---|---|
| UVM tests | 11 | `usb_base_test`, `usb_random_regression_test`, `usb_directed_test`, `usb_hs_test`, `usb_ss_test`, `usb_ssp_test`, `usb_ss20_test`, `usb4_test`, `usb_eusb2_test`, `usb_pd_test`, `eusb2_link_test` |
| Sequences | 15 | `usb_base_sequence`, `usb_normal_seq`, `usb_error_inject_seq`, `usb_reset_seq`, `usb_back_to_back_seq`, `usb_stress_seq`, `usb_corner_seq`, `usb_sof_seq`, `usb_random_sequence`, `usb_regression_sequence`, `usb_directed_regression_sequence`, `usb_sequence_item`, `eusb2_item`, `eusb2_base_seq`, `eusb2_regression_seq` |
| SVA（assert / cover property） | 9 / 12 | `LBL`, `c_hs`, `c_fs`, `c_l1`, `c_l2`, `c_l1_wake`, `c_l2_wake`, `c_nyet`, `c_stall`, `c_rap_ok`, `c_rap_bad`, `c_cm_bad` … |
| Covergroups / coverpoints | 18 / 55 | |

## 4. 充分度判定與缺口

判定：**✅ Sufficient**（88 個 check，mutation score 100%）。

無已知缺口。

