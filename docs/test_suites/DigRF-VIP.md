# DigRF 測試套件（DigRF-VIP）

> 由 `tools/gen_test_suite_docs.py` 依 VIP 內容、`func_report.csv` 與 `mutation_report.csv` 自動產生，請勿手動修改。

## 1. 概要

| 項目 | 內容 |
|---|---|
| 類別 | MIPI |
| 類型 | UVM VIP |
| 功能測試 | 1 個檔案，20 個 check，全部通過 |
| Mutation | 10/12 個 mutant 被偵測（83%） |
| 判定 | **✅ Sufficient**（20 個 check，mutation score 83%） |

## 2. 可執行的功能測試

執行：`python3 tools/run_func_tests.py DigRF-VIP`（Icarus Verilog 或 Verilator 5.052）。

### `tb/func_mipi_tb.sv`

結果：**PASS**（verilator，20 checks）

| # | Check | 類型 |
|---|---|---|
| 1 | outputs held low in reset | check |
| 2 | M-PHY ready out of reset | check |
| 3 | CRC-32 reference matches the standard check value | check |
| 4 | ready low 1 clock in 16 (lows=%0d period=%0d) | check |
| 5 | frame with the correct CRC raises no error | check |
| 6 | frame cut to word_count bytes (padding dropped) | check |
| 7 | padding bytes are excluded from the CRC | check |
| 8 | long frame spans at least one ready-low stall | check |
| 9 | frame held across backpressure is received intact | check |
| 10 | wrong CRC pulses err once | check |
| 11 | wrong CRC on a long frame pulses err once | check |
| 12 | corrupted payload byte detected by CRC | check |
| 13 | beats outside a frame are ignored | check |
| 14 | HSI wake raises hsi_ready | check |
| 15 | HSI valid raises hsi_ready | check |
| 16 | hsi_ready drops without wake/valid | check |
| 17 | D-PHY/UniPro/CSE requests acknowledged | check |
| 18 | acknowledges drop with the requests | check |
| 19 | each frame-sync pulse counts one DigRF frame | check |
| 20 | reset drops the partial frame | check |

## 3. UVM 測試平台內容

UVM 測試需商用模擬器（VCS / Xcelium / Questa）執行；開源流程只做 elaboration（L1a）。

| 項目 | 數量 | 名稱 |
|---|---|---|
| UVM tests | 10 | `mipi_base_test`, `mipi_csi2_test`, `mipi_dsi_test`, `mipi_dphy_test`, `mipi_cphy_test`, `mipi_mphy_test`, `mipi_unipro_test`, `mipi_digrf_test`, `mipi_hsi_test`, `mipi_cse_test` |
| Sequences | 10 | `mipi_seq_item`, `mipi_base_sequence`, `mipi_hsi_sequence`, `mipi_digrf_sequence`, `mipi_back_to_back_sequence`, `mipi_max_payload_sequence`, `mipi_error_inject_sequence`, `mipi_reset_sequence`, `mipi_stress_sequence`, `mipi_regression_sequence` |
| SVA（assert / cover property） | 48 / 17 | `assert_dphy_hs`, `assert_cphy_sym`, `assert_mphy_gear`, `assert_unipro_tc`, `assert_digrf`, `assert_hsi_wake`, `assert_cse_cmd`, `assert_p_digrf_mrd`, `cover_p_digrf_mrd`, `assert_p_digrf_frame`, `cover_p_digrf_frame`, `assert_p_digrf_antenna` … |
| Covergroups / coverpoints | 4 / 17 | |

## 4. 充分度判定與缺口

判定：**✅ Sufficient**（20 個 check，mutation score 83%）。

未被偵測的 mutant（測試缺口或等價 mutant）：

- `dut_mipi_dut.sv:58 0 -> 1 [bp_timer          <= 0;]`
- `dut_mipi_dut.sv:79 0 -> 1 [drf_frame_cnt <= 0;]`

