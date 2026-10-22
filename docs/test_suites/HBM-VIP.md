# HBM 測試套件（HBM-VIP）

> 由 `tools/gen_test_suite_docs.py` 依 VIP 內容、`func_report.csv` 與 `mutation_report.csv` 自動產生，請勿手動修改。

## 1. 概要

| 項目 | 內容 |
|---|---|
| 類別 | Memory |
| 類型 | UVM VIP |
| 功能測試 | 1 個檔案，20 個 check，全部通過 |
| Mutation | 6/6 個 mutant 被偵測（100%） |
| 判定 | **✅ Sufficient**（20 個 check，mutation score 100%） |

## 2. 可執行的功能測試

執行：`python3 tools/run_func_tests.py HBM-VIP`（Icarus Verilog 或 Verilator 5.052）。

### `tb/func_mem_tb.sv`

結果：**PASS**（verilator，20 checks）

模型合約與範圍（摘自測試檔頭）：

```text
func_mem_tb.sv -- self-checking functional test for the HBM memory model
(hbm_mem_model, flattened by smoke/flatten.py). Run: python3 tools/run_func_tests.py HBM-VIP

Model contract (from HBM-VIP/tb_top.sv):
   ACT (ras_n=0,cas_n=1,we_n=1) latches the row of bank cid*4+ba; WR/RD are
   ras_n=1,cas_n=0,we_n=0/1; PRE is ras_n=0,cas_n=1,we_n=0; REF is
   ras_n=0,cas_n=0,we_n=1.
   WR/RD start a 8-beat burst at column c, beat i at column c+8*i. Write
   beat 0 is sampled TCWL=8 clocks after the command, read beat 0 is
   driven TCL=14 clocks after it; one beat per clock.
dq is a variable shared by the model and the controller in the original
interface, so the test writes it hierarchically (u_dut.vif_dq) exactly as
the UVM driver writes vif.dq.
```

| # | Check | 類型 |
|---|---|---|
| 1 | burst write reads back beat-for-beat in order | check |
| 2 | read data not driven before TCL | check |
| 3 | read data not driven past the burst | check |
| 4 | burst column mapping: col+8 starts at beat 1 | check |
| 5 | unwritten columns read 0 | check |
| 6 | second burst overwrites the first | check |
| 7 | bank 0 unaffected by other banks | check |
| 8 | bank 1 holds its own burst | check |
| 9 | channel 5 / bank 2 holds its own burst | check |
| 10 | other row of same bank does not alias | check |
| 11 | row data retained across PRE/ACT | check |
| 12 | data retained across REFRESH | check |
| 13 | write while chip deselected is ignored | check |
| 14 | command during reset had no effect | check |
| 15 | selected NOP leaves the open row unchanged | check |
| 16 | selected NOP does not drive dq | check |
| 17 | fresh bank: burst written | check |
| 18 | burst write does not spill into the following columns | check |
| 19 | REFRESH does not drive dq | check |
| 20 | 24 random bursts match the reference | check |

## 3. UVM 測試平台內容

UVM 測試需商用模擬器（VCS / Xcelium / Questa）執行；開源流程只做 elaboration（L1a）。

| 項目 | 數量 | 名稱 |
|---|---|---|
| UVM tests | 3 | `memory_base_test`, `memory_directed_test`, `memory_coverage_regression_test` |
| Sequences | 21 | `ddr_seq_item`, `lpddr_seq_item`, `ufs_seq_item`, `unipro_seq_item`, `emmc_seq_item`, `onfi_seq_item`, `sd_seq_item`, `hbm_seq_item`, `hbm_base_seq`, `hbm_rw_seq`, `hbm_write_seq`, `hbm_read_seq`, `hbm_refresh_seq`, `hbm_bank_conflict_seq`, `hbm_back_to_back_seq`, `hbm_page_hit_seq`, `hbm_page_miss_seq`, `hbm_stress_seq`, `hbm_regression_seq`, `hbm_cov_cmd_seq` |
| SVA（assert / cover property） | 28 / 24 | `assert_p_hbm_cmd_valid`, `cover_p_hbm_cmd_valid`, `assert_p_hbm_addr_valid`, `cover_p_hbm_addr_valid`, `assert_p_hbm_data_valid`, `cover_p_hbm_data_valid`, `assert_p_hbm_no_x`, `cover_p_hbm_no_x`, `assert_p_hbm_tRCD`, `cover_p_hbm_tRCD`, `assert_p_hbm_tRP`, `cover_p_hbm_tRP` … |
| Covergroups / coverpoints | 10 / 25 | |

## 4. 充分度判定與缺口

判定：**✅ Sufficient**（20 個 check，mutation score 100%）。

無已知缺口。

