# MIPI DPI (Display Pixel Interface) 測試套件（DPI-VIP）

> 由 `tools/gen_test_suite_docs.py` 依 VIP 內容、`func_report.csv` 與 `mutation_report.csv` 自動產生，請勿手動修改。

## 1. 概要

| 項目 | 內容 |
|---|---|
| 類別 | MIPI |
| 類型 | UVM VIP |
| 功能測試 | 1 個檔案，10 個 check，全部通過 |
| Mutation | 20/20 個 mutant 被偵測（100%） |
| 判定 | **✅ Sufficient**（10 個 check，mutation score 100%） |

## 2. 可執行的功能測試

執行：`python3 tools/run_func_tests.py DPI-VIP`（Icarus Verilog 或 Verilator 5.052）。

### `tb/func_dpi_tb.sv`

結果：**PASS**（iverilog，10 checks）

模型合約與範圍（摘自測試檔頭）：

```text
func_dpi_tb.sv -- self-checking functional test for the MIPI DPI display
sink model (dpi_display_sink, flattened by smoke/flatten.py).
Run: python3 tools/run_func_tests.py DPI-VIP

Model contract (from tb/top_tb.sv and dpi_defs_pkg):
   frames of 11 lines x 22 clocks (VSYNC 1 line, HSYNC 2 clocks, DE window
   16 pixels x 8 lines = 128 pixels). At every VSYNC rising edge the sink
   checks that the previous frame carried exactly 128 DE cycles, and it
   flags DE asserted during VSYNC; both are reported with `uvm_error.
   error_inject marks the current frame as intentionally corrupted, which
   suppresses its checks. The sink has no outputs: the test checks its
   counters hierarchically and counts its error reports (dut_errors).
```

| # | Check | 類型 |
|---|---|---|
| 1 | first VSYNC starts frame tracking | check |
| 2 | a frame carries 16x8 = 128 DE cycles | check |
| 3 | short frame counted as 127 pixels | check |
| 4 | DE during VSYNC is counted as an extra pixel | check |
| 5 | error_inject marks the frame as corrupted | check |
| 6 | error_inject marking cleared at the next frame | check |
| 7 | frame counter advances on every VSYNC rising edge | check |
| 8 | reset clears frame tracking | check |
| 9 | reset clears the error mark and the VSYNC edge detector | check |
| 10 | frame tracking restarts after reset (clean frames, no error) | check |

## 3. UVM 測試平台內容

UVM 測試需商用模擬器（VCS / Xcelium / Questa）執行；開源流程只做 elaboration（L1a）。

| 項目 | 數量 | 名稱 |
|---|---|---|
| UVM tests | 3 | `dpi_base_test`, `dpi_random_test`, `dpi_regression_test` |
| Sequences | 10 | `dpi_base_sequence`, `dpi_full_frame_seq`, `dpi_solid_color_seq`, `dpi_gradient_seq`, `dpi_corner_seq`, `dpi_error_inject_seq`, `dpi_reset_seq`, `dpi_random_sequence`, `dpi_regression_sequence`, `dpi_transaction` |
| SVA（assert / cover property） | 20 / 2 | `a_dpi_l1_clk`, `a_dpi_l1_rst`, `a_dpi_l1_state`, `a_dpi_l1_valid`, `a_dpi_trans_idle`, `a_dpi_trans_vsync`, `a_dpi_trans_hblank`, `a_dpi_trans_hactive`, `a_dpi_l3_reset_idle`, `a_dpi_l3_no_stuck`, `a_dpi_l3_full_cycle`, `a_dpi_l3_active` … |
| Covergroups / coverpoints | 3 / 6 | |

## 4. 充分度判定與缺口

判定：**✅ Sufficient**（10 個 check，mutation score 100%）。

無已知缺口。

