# DFI 5.0 (MC-PHY Interface) 測試套件（DFI-VIP）

> 由 `tools/gen_test_suite_docs.py` 依 VIP 內容、`func_report.csv` 與 `mutation_report.csv` 自動產生，請勿手動修改。

## 1. 概要

| 項目 | 內容 |
|---|---|
| 類別 | Memory |
| 類型 | UVM VIP |
| 功能測試 | 1 個檔案，29 個 check，全部通過 |
| Mutation | 12/12 個 mutant 被偵測（100%） |
| 判定 | **✅ Sufficient**（29 個 check，mutation score 100%） |

## 2. 可執行的功能測試

執行：`python3 tools/run_func_tests.py DFI-VIP`（Icarus Verilog 或 Verilator 5.052）。

### `tb/func_dfi_tb.sv`

結果：**PASS**（verilator，29 checks）

模型合約與範圍（摘自測試檔頭）：

```text
func_dfi_tb.sv -- self-checking functional test for the DFI DRAM model
(dfi_dram_model, flattened by smoke/flatten.py).
Run: python3 tools/run_func_tests.py DFI-VIP

Model contract (from tb/top_tb.sv and dfi_defs_pkg):
   commands on dfi_cmd (ACT=1 RD=2 WR=3 PRE=4 REF=5) when cke=1 and cs_n=0;
   ACT opens a row; RD/WR need an open row and tRCD=3 clocks since ACT;
   ACT needs tRP=3 clocks since the last PRE/REF; a violation pulses
   dfi_error for one clock and the command is dropped. Write data is taken
   from dfi_wrdata at the command edge; read data appears with a one-clock
   dfi_rddata_valid pulse RL=4 clocks after the command. Unwritten
   locations read 0x5A5A_0000. Storage is keyed by {bank, column}: the row
   address is not part of the key (model limitation, not tested here).
```

| # | Check | 類型 |
|---|---|---|
| 1 | RD to a closed bank raises dfi_error | check |
| 2 | RD to a closed bank returns no data | check |
| 3 | dfi_error is a single-clock pulse | check |
| 4 | ACT accepted after reset | check |
| 5 | WR before tRCD raises dfi_error | check |
| 6 | WR after tRCD accepted | check |
| 7 | read returns written data (early WR was dropped) | check |
| 8 | rddata_valid arrives RL clocks after RD | check |
| 9 | unwritten column returns the fill pattern | check |
| 10 | pipelined read 1 data | check |
| 11 | pipelined read 2 data in order | check |
| 12 | two back-to-back reads give exactly two valid beats | check |
| 13 | bank 5 holds its own data | check |
| 14 | bank 0 unaffected by bank 5 write | check |
| 15 | PRE closes the bank (RD rejected) | check |
| 16 | PRE leaves other banks open | check |
| 17 | ACT before tRP raises dfi_error | check |
| 18 | ACT after tRP accepted | check |
| 19 | data retained across PRE/ACT | check |
| 20 | WR exactly tRCD after ACT accepted | check |
| 21 | RD exactly tRCD after ACT accepted | check |
| 22 | ACT exactly tRP after PRE accepted | check |
| 23 | data written at the tRCD boundary reads back | check |
| 24 | REF closes all banks | check |
| 25 | ACT with CS_n high is ignored | check |
| 26 | ACT with CKE low is ignored | check |
| 27 | outputs cleared by reset | check |
| 28 | no read data valid from the read pipeline after reset | check |
| 29 | reset closes open rows | check |

## 3. UVM 測試平台內容

UVM 測試需商用模擬器（VCS / Xcelium / Questa）執行；開源流程只做 elaboration（L1a）。

| 項目 | 數量 | 名稱 |
|---|---|---|
| UVM tests | 3 | `dfi_base_test`, `dfi_random_test`, `dfi_regression_test` |
| Sequences | 11 | `dfi_base_sequence`, `dfi_read_seq`, `dfi_write_seq`, `dfi_read_write_seq`, `dfi_refresh_seq`, `dfi_trcd_violation_seq`, `dfi_trp_violation_seq`, `dfi_reset_seq`, `dfi_random_sequence`, `dfi_regression_sequence`, `dfi_transaction` |
| SVA（assert / cover property） | 21 / 2 | `a_dfi_l1_clk`, `a_dfi_l1_rst`, `a_dfi_l1_state`, `a_dfi_l1_valid`, `a_dfi_trans_idle`, `a_dfi_trans_activate`, `a_dfi_trans_read`, `a_dfi_trans_write`, `a_dfi_trans_precharge`, `a_dfi_trans_refresh`, `a_dfi_l3_reset_idle`, `a_dfi_l3_no_stuck` … |
| Covergroups / coverpoints | 3 / 8 | |

## 4. 充分度判定與缺口

判定：**✅ Sufficient**（29 個 check，mutation score 100%）。

模型未實作的功能（不在測試範圍）：

- Storage is keyed by {bank, column}: the row address is not part of the key (model limitation, not tested here).

