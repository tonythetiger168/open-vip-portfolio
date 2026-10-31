# SPI 測試套件（SPI-VIP）

> 由 `tools/gen_test_suite_docs.py` 依 VIP 內容、`func_report.csv` 與 `mutation_report.csv` 自動產生，請勿手動修改。

## 1. 概要

| 項目 | 內容 |
|---|---|
| 類別 | Serial |
| 類型 | UVM VIP |
| 功能測試 | 1 個檔案，10 個 check，全部通過 |
| Mutation | 25/25 個 mutant 被偵測（100%） |
| 判定 | **✅ Sufficient**（10 個 check，mutation score 100%） |

## 2. 可執行的功能測試

執行：`python3 tools/run_func_tests.py SPI-VIP`（Icarus Verilog 或 Verilator 5.052）。

### `tb/smoke_func_tb.sv`

結果：**PASS**（iverilog，10 checks）

| # | Check | 類型 |
|---|---|---|
| 1 | MISO tri-stated while CS high (idle) | check |
| 2 | frame 1 MISO = 0x00 (empty loopback) | check |
| 3 | MISO released after frame 1 | check |
| 4 | frame 2 MISO = 0xA5 (echo of frame 1) | check |
| 5 | frame 3 byte 0 = 0x3C (echo of frame 2) | check |
| 6 | frame 3 byte 1 = 0x00 (queue drained) | check |
| 7 | frame 4 echoes both bytes of frame 3 | check |
| 8 | MISO released after final frame | check |
| 9 | frame 5 echoes both bytes of frame 4 | check |
| 10 | partial / empty frames do not replace the echo data | check |

## 3. UVM 測試平台內容

UVM 測試需商用模擬器（VCS / Xcelium / Questa）執行；開源流程只做 elaboration（L1a）。

| 項目 | 數量 | 名稱 |
|---|---|---|
| UVM tests | 3 | `spi_base_test`, `spi_random_test`, `spi_regression_test` |
| Sequences | 11 | `spi_base_sequence`, `spi_write_seq`, `spi_read_seq`, `spi_burst_seq`, `spi_back_to_back_seq`, `spi_mode_sweep_seq`, `spi_error_inject_seq`, `spi_reset_seq`, `spi_random_sequence`, `spi_regression_sequence`, `spi_transaction` |
| SVA（assert / cover property） | 18 / 2 | `a_spi_l1_clk`, `a_spi_l1_rst`, `a_spi_l1_state`, `a_spi_l1_valid`, `a_spi_trans_idle`, `a_spi_trans_cs_assert`, `a_spi_trans_shift`, `a_spi_trans_cs_deassert`, `a_spi_l3_reset_idle`, `a_spi_l3_no_stuck`, `a_spi_l3_full_cycle`, `a_spi_l3_back_idle` … |
| Covergroups / coverpoints | 3 / 7 | |

## 4. 充分度判定與缺口

判定：**✅ Sufficient**（10 個 check，mutation score 100%）。

無已知缺口。

