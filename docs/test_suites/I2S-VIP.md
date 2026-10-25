# I2S Audio 測試套件（I2S-VIP）

> 由 `tools/gen_test_suite_docs.py` 依 VIP 內容、`func_report.csv` 與 `mutation_report.csv` 自動產生，請勿手動修改。

## 1. 概要

| 項目 | 內容 |
|---|---|
| 類別 | Audio |
| 類型 | UVM VIP |
| 功能測試 | 1 個檔案，11 個 check，全部通過 |
| Mutation | 5/5 個 mutant 被偵測（100%） |
| 判定 | **✅ Sufficient**（11 個 check，mutation score 100%） |

## 2. 可執行的功能測試

執行：`python3 tools/run_func_tests.py I2S-VIP`（Icarus Verilog 或 Verilator 5.052）。

### `tb/func_i2s_tb.sv`

結果：**PASS**（verilator，11 checks）

模型合約與範圍（摘自測試檔頭）：

```text
func_i2s_tb.sv -- self-checking functional test for the I2S receiver /
loopback model (i2s_receiver_loopback, flattened by smoke/flatten.py).
Run: python3 tools/run_func_tests.py I2S-VIP

Model contract (from tb/top_tb.sv and i2s_driver.svh):
   the transmitter changes WS and SD on the falling edge of SCK, the
   receiver samples on the rising edge. WS low = left slot, WS high = right
   slot, 24-bit samples MSB first. The MSB is sent in the same SCK cycle as
   the WS transition (left-justified alignment, no Philips one-bit delay).
   A left sample is stored only if all 24 bits arrived before WS rose; each
   complete right sample closes a frame (frame index wr_idx). SD is looped
   back on sd_i half a cycle later (falling edge).
```

| # | Check | 類型 |
|---|---|---|
| 1 | a left+right pair closes one frame | check |
| 2 | left 24-bit sample captured MSB first | check |
| 3 | right 24-bit sample captured MSB first | check |
| 4 | frame counter advances per frame (incl. back-to-back frames) | check |
| 5 | all-ones / all-zeros samples | check |
| 6 | MSB/LSB extremes without an idle gap | check |
| 7 | single-bit samples keep bit order | check |
| 8 | short (16-bit) left slot is not stored | check |
| 9 | right sample after a short left slot still stored | check |
| 10 | SD looped back on sd_i half an SCK cycle later | check |
| 11 | reset clears the frame index and sd_i | check |

## 3. UVM 測試平台內容

UVM 測試需商用模擬器（VCS / Xcelium / Questa）執行；開源流程只做 elaboration（L1a）。

| 項目 | 數量 | 名稱 |
|---|---|---|
| UVM tests | 3 | `i2s_base_test`, `i2s_random_test`, `i2s_regression_test` |
| Sequences | 11 | `i2s_base_sequence`, `i2s_corner_seq`, `i2s_walking_one_seq`, `i2s_ramp_seq`, `i2s_stereo_complement_seq`, `i2s_back_to_back_seq`, `i2s_idle_gap_seq`, `i2s_error_inject_seq`, `i2s_random_sequence`, `i2s_regression_sequence`, `i2s_transaction` |
| SVA（assert / cover property） | 19 / 2 | `a_i2s_l1_clk`, `a_i2s_l1_rst`, `a_i2s_l1_state`, `a_i2s_l1_valid`, `a_i2s_trans_idle`, `a_i2s_trans_left_channel`, `a_i2s_trans_right_channel`, `a_i2s_l3_reset_idle`, `a_i2s_l3_no_stuck`, `a_i2s_l3_full_cycle`, `a_i2s_l3_back_idle`, `a_i2s_l4_ws_edge` … |
| Covergroups / coverpoints | 3 / 7 | |

## 4. 充分度判定與缺口

判定：**✅ Sufficient**（11 個 check，mutation score 100%）。

無已知缺口。

