# DSI 測試套件（DSI-VIP）

> 由 `tools/gen_test_suite_docs.py` 依 VIP 內容、`func_report.csv` 與 `mutation_report.csv` 自動產生，請勿手動修改。

## 1. 概要

| 項目 | 內容 |
|---|---|
| 類別 | MIPI |
| 類型 | UVM VIP |
| 功能測試 | 1 個檔案，29 個 check，全部通過 |
| Mutation | 11/11 個 mutant 被偵測（100%） |
| 判定 | **✅ Sufficient**（29 個 check，mutation score 100%） |

## 2. 可執行的功能測試

執行：`python3 tools/run_func_tests.py DSI-VIP`（Icarus Verilog 或 Verilator 5.052）。

### `tb/func_mipi_tb.sv`

結果：**PASS**（verilator，29 checks）

| # | Check | 類型 |
|---|---|---|
| 1 | outputs held low in reset | check |
| 2 | PHY / link ready outputs and error report low in reset | check |
| 3 | lane_count reports 4 lanes in reset | check |
| 4 | lane_count reports 4 lanes | check |
| 5 | CRC-16 reference matches the specification examples | check |
| 6 | six payload words accepted with valid/ready | check |
| 7 | correct header ECC flagged ecc_ok | check |
| 8 | correct payload CRC (spec example 1) flagged crc_ok | check |
| 9 | rx_pkts counts the packet at eop | check |
| 10 | second spec example on VC2: ECC and CRC accepted | check |
| 11 | header ECC with one flipped parity bit flagged bad | check |
| 12 | payload CRC still good when only the ECC is wrong | check |
| 13 | corrupted payload CRC flagged bad | check |
| 14 | ECC detects a data-type change | check |
| 15 | single-beat packet: header and CRC accepted | check |
| 16 | valid gap inside a packet keeps the payload intact | check |
| 17 | ready lags valid by one clock | check |
| 18 | ready follows valid | check |
| 19 | ready drops with valid | check |
| 20 | D-PHY/M-PHY/UniPro/HSI/CSE requests acknowledged | check |
| 21 | HS mode enables termination | check |
| 22 | LP-11 reports calibration/stop state done | check |
| 23 | side-band responses drop when the requests drop | check |
| 24 | BTA acknowledged, no error after a good packet | check |
| 25 | BTA after an ECC error reports the error | check |
| 26 | ack and error report are single-cycle with BTA | check |
| 27 | reset clears handshake, status and packet count | check |

## 3. UVM 測試平台內容

UVM 測試需商用模擬器（VCS / Xcelium / Questa）執行；開源流程只做 elaboration（L1a）。

| 項目 | 數量 | 名稱 |
|---|---|---|
| UVM tests | 14 | `mipi_base_test`, `mipi_dsi_test`, `mipi_dsi_error_test`, `mipi_dsi_reset_test`, `mipi_dsi_stress_test`, `mipi_dsi_regression_test`, `mipi_csi2_test`, `mipi_dphy_test`, `mipi_cphy_test`, `mipi_mphy_test`, `mipi_unipro_test`, `mipi_digrf_test`, `mipi_hsi_test`, `mipi_cse_test` |
| Sequences | 10 | `mipi_seq_item`, `mipi_base_sequence`, `mipi_normal_seq`, `mipi_error_seq`, `mipi_reset_seq`, `mipi_back_to_back_seq`, `mipi_stress_seq`, `mipi_corner_seq`, `mipi_random_sequence`, `mipi_regression_sequence` |
| SVA（assert / cover property） | 23 / 16 | `assert_dphy_hs`, `assert_cphy_sym`, `assert_mphy_gear`, `assert_unipro_tc`, `assert_digrf`, `assert_hsi_wake`, `assert_cse_cmd`, `assert_p_dsi_dt`, `cover_p_dsi_dt`, `assert_p_dsi_vc`, `cover_p_dsi_vc`, `assert_p_dsi_wc` … |
| Covergroups / coverpoints | 13 / 44 | |

## 4. 充分度判定與缺口

判定：**✅ Sufficient**（29 個 check，mutation score 100%）。

無已知缺口。

