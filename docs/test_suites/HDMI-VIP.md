# HDMI 2.1 測試套件（HDMI-VIP）

> 由 `tools/gen_test_suite_docs.py` 依 VIP 內容、`func_report.csv` 與 `mutation_report.csv` 自動產生，請勿手動修改。

## 1. 概要

| 項目 | 內容 |
|---|---|
| 類別 | Video |
| 類型 | UVM VIP |
| 功能測試 | 1 個檔案，20 個 check，全部通過 |
| Mutation | 25/25 個 mutant 被偵測（100%） |
| 判定 | **✅ Sufficient**（20 個 check，mutation score 100%） |

## 2. 可執行的功能測試

執行：`python3 tools/run_func_tests.py HDMI-VIP`（Icarus Verilog 或 Verilator 5.052）。

### `tb/func_hdmi_tb.sv`

結果：**PASS**（iverilog，20 checks）

模型合約與範圍（摘自測試檔頭）：

```text
func_hdmi_tb.sv -- self-checking functional test for the HDMI sink model
(hdmi_sink_model in tb/top_tb.sv, flattened by smoke/flatten.py).
Run: python3 tools/run_func_tests.py HDMI-VIP

Model contract (from tb/top_tb.sv and hdmi_defs_pkg), tmds_cw = {ch2, ch1,
ch0} 10-bit code words, period type on state (0 IDLE, 1 CONTROL_PREAMBLE,
2 DATA_ISLAND, 3 VIDEO_GUARD, 4 VIDEO_DATA):
   * pixels are abstracted as {0, d[7:0], 0}; the last video word carries
     {2'b11, crc} on ch0, where crc folds every pixel since the preamble:
     crc = {crc[6:0], 0} ^ R ^ G ^ B ^ 0x1D. A mismatch pulses crc_err.
   * preamble (HDMI 1.4b 5.2.1.1): ch1 CTRL1 + ch2 CTRL0 = video,
     ch1 = ch2 = CTRL1 = data island (preamble_video / preamble_island).
   * a video guard band whose ch0 word is not 1011001100 is warned about.
   * HPD: a rising edge on hpd_drop_req drops HPD for 3 clocks, starting 2
     clocks later; requests while a drop is in progress are ignored.
     (HPD itself is registered: low on the 4th..6th clock after the edge.)
```

| # | Check | 類型 |
|---|---|---|
| 1 | HPD low in reset | check |
| 2 | HPD asserted after reset | check |
| 3 | CRC word ends each video period (frame_count) | check |
| 4 | matching CRC raises no error | check |
| 5 | single-pixel period: CRC restarted at the preamble | check |
| 6 | CRC mismatch pulses crc_err once | check |
| 7 | next clean period passes again | check |
| 8 | single corrupted pixel caught by the CRC | check |
| 9 | bad guard band does not affect the CRC | check |
| 10 | blue >= 0x80 is pixel data, not the CRC word | check |
| 11 | spec video preamble (ch1 CTRL1, ch2 CTRL0) decoded as video | check |
| 12 | spec island preamble (ch1 = ch2 = CTRL1) decoded as island | check |
| 13 | preamble flags clear outside control periods | check |
| 14 | HPD low for 3 clocks (got %0d) | check |
| 15 | HPD drops on the 4th clock after the request (got %0d) | check |
| 16 | a new request edge during the drop is ignored | check |
| 17 | HPD restored | check |
| 18 | a held request does not retrigger the drop | check |
| 19 | reset: HPD low, CRC accumulator cleared | check |
| 20 | reset clears the preamble flags | check |

## 3. UVM 測試平台內容

UVM 測試需商用模擬器（VCS / Xcelium / Questa）執行；開源流程只做 elaboration（L1a）。

| 項目 | 數量 | 名稱 |
|---|---|---|
| UVM tests | 3 | `hdmi_base_test`, `hdmi_random_test`, `hdmi_regression_test` |
| Sequences | 11 | `hdmi_base_sequence`, `hdmi_video_seq`, `hdmi_island_seq`, `hdmi_hdcp_seq`, `hdmi_long_burst_seq`, `hdmi_guard_error_seq`, `hdmi_hpd_error_seq`, `hdmi_reset_seq`, `hdmi_random_sequence`, `hdmi_regression_sequence`, `hdmi_transaction` |
| SVA（assert / cover property） | 21 / 2 | `a_hdmi_l1_clk`, `a_hdmi_l1_rst`, `a_hdmi_l1_state`, `a_hdmi_l1_valid`, `a_hdmi_trans_idle`, `a_hdmi_trans_control_preamble`, `a_hdmi_trans_data_island`, `a_hdmi_trans_video_guard`, `a_hdmi_trans_video_data`, `a_hdmi_l3_reset_idle`, `a_hdmi_l3_no_stuck`, `a_hdmi_l3_full_cycle` … |
| Covergroups / coverpoints | 3 / 10 | |

## 4. 充分度判定與缺口

判定：**✅ Sufficient**（20 個 check，mutation score 100%）。

無已知缺口。

