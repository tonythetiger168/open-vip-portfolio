# LPDDR 測試套件（LPDDR-VIP）

> 由 `tools/gen_test_suite_docs.py` 依 VIP 內容、`func_report.csv` 與 `mutation_report.csv` 自動產生，請勿手動修改。

## 1. 概要

| 項目 | 內容 |
|---|---|
| 類別 | Memory |
| 類型 | UVM VIP |
| 功能測試 | 1 個檔案，14 個 check，全部通過 |
| Mutation | 4/4 個 mutant 被偵測（100%） |
| 判定 | **✅ Sufficient**（14 個 check，mutation score 100%） |

## 2. 可執行的功能測試

執行：`python3 tools/run_func_tests.py LPDDR-VIP`（Icarus Verilog 或 Verilator 5.052）。

### `tb/func_mem_tb.sv`

結果：**PASS**（verilator，14 checks）

模型合約與範圍（摘自測試檔頭）：

```text
func_mem_tb.sv -- self-checking functional test for the LPDDR memory model
(lpddr_mem_model, flattened by smoke/flatten.py). Run: python3 tools/run_func_tests.py LPDDR-VIP

Model contract (from LPDDR-VIP/tb_top.sv):
   Commands on CA[5:0] with CS high: ACT 010bbb, WR 101bbb, RD 100bbb,
   PRE 011bbb, REF 110000 (bbb = bank). The model always uses row 0 and
   column 0, so each bank holds exactly one burst.
   WR/RD start a 8-beat burst at column c, beat i at column c+8*i. Write
   beat 0 is sampled TCWL=11 clocks after the command, read beat 0 is
   driven TCL=22 clocks after it; one beat per clock.
dq is a variable shared by the model and the controller in the original
interface, so the test writes it hierarchically (u_dut.vif_dq) exactly as
the UVM driver writes vif.dq.
```

| # | Check | 類型 |
|---|---|---|
| 1 | burst write reads back beat-for-beat in order | check |
| 2 | read data not driven before TCL | check |
| 3 | read data not driven past the burst | check |
| 4 | second burst overwrites the first | check |
| 5 | bank 0 unaffected by other banks | check |
| 6 | bank 1 holds its own burst | check |
| 7 | bank 6 holds its own burst | check |
| 8 | bank data retained across PRE/ACT | check |
| 9 | data retained across REFRESH | check |
| 10 | write while chip deselected is ignored | check |
| 11 | command during reset had no effect | check |
| 12 | fresh bank: burst written | check |
| 13 | REFRESH does not drive dq | check |
| 14 | 24 random bursts match the reference | check |

## 3. UVM 測試平台內容

UVM 測試需商用模擬器（VCS / Xcelium / Questa）執行；開源流程只做 elaboration（L1a）。

| 項目 | 數量 | 名稱 |
|---|---|---|
| UVM tests | 3 | `memory_base_test`, `memory_directed_test`, `memory_coverage_regression_test` |
| Sequences | 21 | `ddr_seq_item`, `hbm_seq_item`, `ufs_seq_item`, `unipro_seq_item`, `emmc_seq_item`, `onfi_seq_item`, `sd_seq_item`, `lpddr_seq_item`, `lpddr_base_seq`, `lpddr_rw_seq`, `lpddr_write_seq`, `lpddr_read_seq`, `lpddr_refresh_seq`, `lpddr_bank_conflict_seq`, `lpddr_back_to_back_seq`, `lpddr_page_hit_seq`, `lpddr_page_miss_seq`, `lpddr_stress_seq`, `lpddr_regression_seq`, `lpddr_cov_cmd_seq` |
| SVA（assert / cover property） | 28 / 24 | `assert_p_lpddr_cmd_valid`, `cover_p_lpddr_cmd_valid`, `assert_p_lpddr_addr_valid`, `cover_p_lpddr_addr_valid`, `assert_p_lpddr_data_valid`, `cover_p_lpddr_data_valid`, `assert_p_lpddr_no_x`, `cover_p_lpddr_no_x`, `assert_p_lpddr_tRCD`, `cover_p_lpddr_tRCD`, `assert_p_lpddr_tRP`, `cover_p_lpddr_tRP` … |
| Covergroups / coverpoints | 10 / 26 | |

## 4. 充分度判定與缺口

判定：**✅ Sufficient**（14 個 check，mutation score 100%）。

無已知缺口。

