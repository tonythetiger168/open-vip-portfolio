# USB4 測試套件（USB4-VIP）

> 由 `tools/gen_test_suite_docs.py` 依 VIP 內容、`func_report.csv` 與 `mutation_report.csv` 自動產生，請勿手動修改。

## 1. 概要

| 項目 | 內容 |
|---|---|
| 類別 | USB |
| 類型 | UVM VIP |
| 功能測試 | 1 個檔案，213 個 check，全部通過 |
| Mutation | 25/25 個 mutant 被偵測（100%） |
| 判定 | **✅ Sufficient**（213 個 check，mutation score 100%） |

## 2. 可執行的功能測試

執行：`python3 tools/run_func_tests.py USB4-VIP`（Icarus Verilog 或 Verilator 5.054）。

### `tb/smoke_func_tb.sv`

結果：**PASS**（iverilog，213 checks）

| # | Check | 類型 |
|---|---|---|
| 1 | %s: ordered set lane %0d kind %0d (got %0d, %0d queued) | check |
| 2 | : no packet | check |
| 3 | %s: header %08h (want PDF %0h hop %03h %0d words), %0d words, w0 %08h w1 %08h w2 %08h | check |
| 4 | %s: route %08h word1 %08h (want %08h), CRC %08h (want %08h) | check |
| 5 | %s: data %0d = %08h (want %08h) | check |
| 6 | %s: Notification code %0d (got %08h) | check |
| 7 | %s: nothing sent (%0d packets) | check |
| 8 | in reset: both lanes CLd, nothing sent | check |
| 9 | no lane detected: CLd | check |
| 10 | lane 0 detected: Lock | check |
| 11 | SLOS interrupted: still Lock | check |
| 12 | two SLOS in a row: Training.TS1 | check |
| 13 | TS1 interrupted: still TS1 | check |
| 14 | TS1 without the Gen 3 bit: Gen 2 | check |
| 15 | TS2 interrupted by SLOS: still TS2 | check |
| 16 | two TS2 (a late TS1 between them is tolerated): CL0, one lane | check |
| 17 | one answer per training step | check |
| 18 | lane 1 detected: Lock | check |
| 19 | 62 clocks after the last SLOS: still Lock | check |
| 20 | 64 clocks without progress: training timeout | check |
| 21 | lane still detected: Lock again | check |
| 22 | lane 1 not detected: CLd | check |
| 23 | retransmission counted | check |
| 24 | 6 notifications | check |
| 25 | CRC error counted | check |
| 26 | HEC error counted | check |
| 27 | length errors counted | check |
| 28 | forward counted | check |
| 29 | unknown HopID counted | check |
| 30 | 5th packet with 4 buffers held: overflow | check |
| 31 | Gen 2: no correction | check |
| 32 | CLD ordered set: lane 0 down | check |
| 33 | TS1 with the Gen 3 bit: Gen 3 | check |
| 34 | 2 corrections, nothing lost | check |
| 35 | 3 uncorrectable packets: still CL0 | check |
| 36 | 4th uncorrectable packet: retrain from Lock | check |
| 37 | count restarts at CL0 entry | check |
| 38 | local port without Gen 3: Gen 2 even if the far end has it | check |
| 39 | lane 1 down: width 1 | check |
| 40 | both lanes CL0: bonded, width 2 | check |
| 41 | lane 1 CLD: width 1 | check |
| 42 | bonding disabled: width 1 | check |
| 43 | still CL0 | check |
| 44 | CL_REQ on lane 1: ignored | check |
| 45 | both lanes in CLx | check |
| 46 | no forward in CLx | check |
| 47 | WAKE on lane 0: Training.TS2 | check |
| 48 | both lanes CL0 again | check |
| 49 | lane 0 not detected: CLd, lane 1 stays | check |
| 50 | lane 0 down: nothing received | check |
| 51 | reset clears the adapter | check |
| 52 | every sent packet framed by first / last | check |
| 53 | nothing sent outside CL0 | check |

## 3. UVM 測試平台內容

UVM 測試需商用模擬器（VCS / Xcelium / Questa）執行；開源流程只做 elaboration（L1a）。

| 項目 | 數量 | 名稱 |
|---|---|---|
| UVM tests | 11 | `usb_base_test`, `usb_random_regression_test`, `usb_directed_test`, `usb_hs_test`, `usb_ss_test`, `usb_ssp_test`, `usb_ss20_test`, `usb4_test`, `usb_eusb2_test`, `usb_pd_test`, `usb4_link_test` |
| Sequences | 15 | `usb_base_sequence`, `usb_normal_seq`, `usb_error_inject_seq`, `usb_reset_seq`, `usb_back_to_back_seq`, `usb_stress_seq`, `usb_corner_seq`, `usb_sof_seq`, `usb_random_sequence`, `usb_regression_sequence`, `usb_directed_regression_sequence`, `usb_sequence_item`, `usb4_item`, `usb4_base_seq`, `usb4_regression_seq` |
| SVA（assert / cover property） | 9 / 12 | `LBL`, `c_gen3`, `c_bonded`, `c_clx`, `c_ack`, `c_nak`, `c_retrain`, `c_tmo`, `c_corr`, `c_ovf`, `c_dup`, `c_notif` … |
| Covergroups / coverpoints | 17 / 52 | |

## 4. 充分度判定與缺口

判定：**✅ Sufficient**（213 個 check，mutation score 100%）。

無已知缺口。

