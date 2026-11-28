# USB2 測試套件（USB2-VIP）

> 由 `tools/gen_test_suite_docs.py` 依 VIP 內容、`func_report.csv` 與 `mutation_report.csv` 自動產生，請勿手動修改。

## 1. 概要

| 項目 | 內容 |
|---|---|
| 類別 | USB |
| 類型 | UVM VIP |
| 功能測試 | 1 個檔案，230 個 check，全部通過 |
| Mutation | 29/29 個 mutant 被偵測（100%） |
| 判定 | **✅ Sufficient**（230 個 check，mutation score 100%） |

## 2. 可執行的功能測試

執行：`python3 tools/run_func_tests.py USB2-VIP`（Icarus Verilog 或 Verilator 5.054）。

### `tb/smoke_func_tb.sv`

結果：**PASS**（iverilog，230 checks）

| # | Check | 類型 |
|---|---|---|
| 1 | reset detected after 16 clocks of SE0 | check |
| 2 | device chirp K for 8 clocks | check |
| 3 | 3 host K-J pairs -> HS | check |
| 4 | : status ZLP DATA1 | check |
| 5 | enumerated: CONFIGURED | check |
| 6 | in reset: no answer, FS | check |
| 7 | after rst_n: FS, DEFAULT, address 0 | check |
| 8 | after rst_n: idle, counters 0 | check |
| 9 | 15 clocks of SE0: no reset yet | check |
| 10 | 16th clock: bus reset, FS (no hs_cap) | check |
| 11 | SE0 held on after the reset: no second reset | check |
| 12 | J then SE0 16 clocks: second reset | check |
| 13 | FS SOF: frame 5 | check |
| 14 | FS SOF: next frame, no miss | check |
| 15 | FS: repeated frame number -> sof_miss | check |
| 16 | FS: skipped frames -> sof_miss | check |
| 17 | babble counted | check |
| 18 | FS bulk IN: app length clamped to 64 | check |
| 19 | 23 idle clocks: still FS | check |
| 20 | 24 idle J clocks: suspend | check |
| 21 | 2-clock K: no resume | check |
| 22 | K >= 4 clocks then J: resume at FS, still CONFIGURED | check |
| 23 | reset returns the device to DEFAULT / address 0 | check |
| 24 | HS idle with SE0 -> reset, new chirp | check |
| 25 | no host chirp within 48 clocks: FS | check |
| 26 | 1-clock K/J levels: FS fallback | check |
| 27 | only 1.5 K-J pairs: FS fallback | check |
| 28 | address not applied before the status stage | check |
| 29 | status IN: ZLP DATA1 | check |
| 30 | address still 0 before the host ACK | check |
| 31 | status ZLP without ACK: timeout, address held | check |
| 32 | status ACK: ADDRESS 0x2A | check |
| 33 | CONFIGURED | check |
| 34 | address unchanged | check |
| 35 | GET_STATUS(device): DATA1, 2 bytes, self-powered | check |
| 36 | duplicate counted | check |
| 37 | after a new SETUP: data stage served | check |
| 38 | NYET counted | check |
| 39 | dup and NAK counted | check |
| 40 | CRC16 error counted | check |
| 41 | DATA2 counted as PID error | check |
| 42 | PID check error counted | check |
| 43 | CRC5 error counted | check |
| 44 | HS bulk IN: 600 clamped to 512, DATA0 | check |
| 45 | no host ACK: timeout | check |
| 46 | retry repeats DATA0 and the data | check |
| 47 | host NAK instead of ACK: not retired | check |
| 48 | a token instead of the ACK: not retired, served again | check |
| 49 | second packet: DATA1, 20 bytes (third app_wr dropped: FIFO full) | check |
| 50 | interrupt IN: DATA0, 4 bytes | check |
| 51 | next report: DATA1 | check |
| 52 | EP2 halted | check |
| 53 | GET_STATUS(EP2): halted | check |
| 54 | EP2 halt cleared | check |
| 55 | CLEAR_FEATURE resets the toggle to DATA0 | check |
| 56 | SET_CONFIGURATION clears halts | check |
| 57 | configuration 0: back to ADDRESS | check |
| 58 | HS: microframe advances within frame 100 | check |
| 59 | ninth microframe: sof_miss | check |
| 60 | next frame: microframe 0 | check |
| 61 | frame jump: sof_miss | check |
| 62 | frame number wraps 2047 -> 0 | check |
| 63 | SOF with bad CRC5: ignored | check |
| 64 | split completed | check |
| 65 | CSPLIT IN done: DATA0, 8 bytes | check |
| 66 | second split completed | check |
| 67 | split token CRC5 error counted once | check |
| 68 | stray data packet with a bad CRC: not counted | check |
| 69 | SOF after a SPLIT is still a SOF | check |
| 70 | HS: 23 clocks without packets | check |
| 71 | HS: 24 clocks idle with J -> suspend (FS termination) | check |
| 72 | resume K, then back to HS | check |
| 73 | suspend again | check |
| 74 | SE0 for 15 clocks in suspend: no reset yet | check |
| 75 | SE0 16 clocks in suspend: reset, chirp | check |
| 76 | HS again after the reset | check |
| 77 | reset without host chirp: FS | check |
| 78 | FS bulk IN clamp 64 | check |
| 79 | rst_n clears everything | check |

## 3. UVM 測試平台內容

UVM 測試需商用模擬器（VCS / Xcelium / Questa）執行；開源流程只做 elaboration（L1a）。

| 項目 | 數量 | 名稱 |
|---|---|---|
| UVM tests | 11 | `usb_base_test`, `usb_random_regression_test`, `usb_directed_test`, `usb_hs_test`, `usb_ss_test`, `usb_ssp_test`, `usb_ss20_test`, `usb4_test`, `usb_eusb2_test`, `usb_pd_test`, `usb2_link_test` |
| Sequences | 15 | `usb_base_sequence`, `usb_normal_seq`, `usb_error_inject_seq`, `usb_reset_seq`, `usb_back_to_back_seq`, `usb_stress_seq`, `usb_corner_seq`, `usb_sof_seq`, `usb_random_sequence`, `usb_regression_sequence`, `usb_directed_regression_sequence`, `usb_sequence_item`, `usb2_item`, `usb2_base_seq`, `usb2_regression_seq` |
| SVA（assert / cover property） | 9 / 12 | `LBL`, `c_hs`, `c_fs_fall`, `c_susp`, `c_resume`, `c_nyet`, `c_stall`, `c_data1`, `c_split`, `c_uframe7`, `c_miss`, `c_babble` … |
| Covergroups / coverpoints | 18 / 54 | |

## 4. 充分度判定與缺口

判定：**✅ Sufficient**（230 個 check，mutation score 100%）。

無已知缺口。

