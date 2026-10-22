# UniPro-Mem 測試套件（UniPro_Mem-VIP）

> 由 `tools/gen_test_suite_docs.py` 依 VIP 內容、`func_report.csv` 與 `mutation_report.csv` 自動產生，請勿手動修改。

## 1. 概要

| 項目 | 內容 |
|---|---|
| 類別 | Memory |
| 類型 | UVM VIP |
| 功能測試 | 1 個檔案，22 個 check，全部通過 |
| Mutation | 22/22 個 mutant 被偵測（100%） |
| 判定 | **✅ Sufficient**（22 個 check，mutation score 100%） |

## 2. 可執行的功能測試

執行：`python3 tools/run_func_tests.py UniPro_Mem-VIP`（Icarus Verilog 或 Verilator 5.052）。

### `tb/func_unipro_mem_tb.sv`

結果：**PASS**（iverilog，22 checks）

模型合約與範圍（摘自測試檔頭）：

```text
func_unipro_mem_tb.sv -- self-checking functional test for the UniPro
endpoint model and the UFS/eMMC loopback stubs of tb_top.sv (flattened by
smoke/flatten.py). Run: python3 tools/run_func_tests.py UniPro_Mem-VIP

Model contract (from tb_top.sv); every output is registered one clock
later (with a #1ns delay):
   * unipro_endpoint_dut: tx_data/tx_data_valid loop back to rx_data/
     rx_data_valid; rx_cred = tx_cred + 1, with rx_cred_valid on any data
     or credit transfer; data 0xFF is an error frame (err for one clock,
     err_frames++), status is 2'b10 the clock after an error and 2'b01
     otherwise; ready follows valid; rx_frames counts data transfers.
   * ufs_device_dut / emmc_device_dut: data_out (cmd) loops back to data_in
     (resp) with its valid; eMMC busy stays low.
```

| # | Check | 類型 |
|---|---|---|
| 1 | outputs cleared in reset | check |
| 2 | data and credit outputs cleared in reset | check |
| 3 | eMMC / UFS stub outputs cleared in reset | check |
| 4 | status OK after reset | check |
| 5 | data looped back in order with gaps (%0d of %0d) | check |
| 6 | rx_frames counts data transfers | check |
| 7 | no error for ordinary data | check |
| 8 | output registered one clock later | check |
| 9 | credit returned as tx_cred + 1 | check |
| 10 | credit counter wraps at 8 bits | check |
| 11 | rx_cred_valid only with a transfer | check |
| 12 | data transfer also returns a credit | check |
| 13 | data 0xFF flags an error | check |
| 14 | status reports the error the next clock | check |
| 15 | error is a single-clock event, counted once | check |
| 16 | 0xFF without data valid is not an error | check |
| 17 | ready follows valid | check |
| 18 | ready drops with valid | check |
| 19 | UFS stub loops data_out back to data_in | check |
| 20 | eMMC stub echoes cmd as resp, never busy | check |
| 21 | stub valids drop | check |
| 22 | asynchronous reset clears the endpoint | check |

## 3. UVM 測試平台內容

UVM 測試需商用模擬器（VCS / Xcelium / Questa）執行；開源流程只做 elaboration（L1a）。

| 項目 | 數量 | 名稱 |
|---|---|---|
| UVM tests | 7 | `memory_base_test`, `memory_coverage_regression_test`, `memory_random_test`, `unipro_regression_test`, `unipro_error_test`, `unipro_reset_test`, `unipro_stress_test` |
| Sequences | 45 | `ddr_seq_item`, `ddr_base_seq`, `ddr_rw_seq`, `ddr_cov_cmd_seq`, `ddr_cov_bank_seq`, `ddr_cov_bl_seq`, `emmc_seq_item`, `emmc_base_seq`, `emmc_rw_seq`, `emmc_cov_cmd_seq`, `emmc_cov_bw_seq`, `hbm_seq_item`, `hbm_base_seq`, `hbm_rw_seq`, `hbm_cov_cmd_seq`, `hbm_cov_ch_seq`, `lpddr_seq_item`, `lpddr_base_seq`, `lpddr_rw_seq`, `lpddr_cov_cmd_seq` |
| SVA（assert / cover property） | 26 / 26 | `assert_p_unipro_mem_cmd_valid`, `cover_p_unipro_mem_cmd_valid`, `assert_p_unipro_mem_reset`, `cover_p_unipro_mem_reset`, `assert_p_unipro_mem_sof_eof`, `cover_p_unipro_mem_sof_eof`, `assert_p_unipro_mem_power`, `cover_p_unipro_mem_power`, `assert_p_unipro_mem_cp_state`, `cover_p_unipro_mem_cp_state`, `assert_p_unipro_mem_tc`, `cover_p_unipro_mem_tc` … |
| Covergroups / coverpoints | 10 / 22 | |

## 4. 充分度判定與缺口

判定：**✅ Sufficient**（22 個 check，mutation score 100%）。

無已知缺口。

