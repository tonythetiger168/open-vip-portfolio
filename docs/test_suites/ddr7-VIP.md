# DDR7 測試套件（ddr7-VIP）

> 由 `tools/gen_test_suite_docs.py` 依 VIP 內容、`func_report.csv` 與 `mutation_report.csv` 自動產生，請勿手動修改。

## 1. 概要

| 項目 | 內容 |
|---|---|
| 類別 | Memory |
| 類型 | UVM VIP |
| 功能測試 | 1 個檔案，16 個 check，全部通過 |
| Mutation | 5/5 個 mutant 被偵測（100%） |
| 判定 | **✅ Sufficient**（16 個 check，mutation score 100%） |

## 2. 可執行的功能測試

執行：`python3 tools/run_func_tests.py ddr7-VIP`（Icarus Verilog 或 Verilator 5.052）。

### `ddr7_vip/tb/func_mem_tb.sv`

結果：**PASS**（verilator，16 checks）

模型合約與範圍（摘自測試檔頭）：

```text
func_mem_tb.sv -- self-checking functional test for the DDR7 memory model
(ddr7_mem_model, flattened by smoke/flatten.py). Run: python3 tools/run_func_tests.py ddr7-VIP

Model contract (from ddr7-VIP/ddr7_vip/tb/tb_top.sv):
   ACT (act_n=0) latches the row of bank bg*4+ba; WR/RD are ras_n=1,cas_n=0,
   we_n=0/1; PRE is ras_n=0,cas_n=1,we_n=0; REF is ras_n=0,cas_n=0,we_n=1.
   WR/RD start a 16-beat burst at column c, beat i at column c+8*i. Write
   beat 0 is sampled TCWL=16 clocks after the command, read beat 0 is
   driven TCL=18 clocks after it; one beat per clock.
dq is a variable shared by the model and the controller in the original
interface, so the test writes it hierarchically (u_dut.vif_dq) exactly as
the UVM driver writes vif.dq.
```

| # | Check | 類型 |
|---|---|---|
| 1 | burst write reads back beat-for-beat in order | check |
| 2 | read data not driven before TCL | check |
| 3 | read data not driven past the 16-beat burst | check |
| 4 | burst column mapping: col+8 starts at beat 1 | check |
| 5 | unwritten columns read 0 | check |
| 6 | second burst overwrites the first | check |
| 7 | bank 0 unaffected by other banks | check |
| 8 | bank 1 holds its own burst | check |
| 9 | bank group 5 / bank 2 holds its own burst | check |
| 10 | other row of same bank does not alias | check |
| 11 | row data retained across PRE/ACT | check |
| 12 | data retained across REFRESH | check |
| 13 | write while chip deselected is ignored | check |
| 14 | command during reset had no effect | check |
| 15 | REFRESH / selected NOP do not drive dq | check |
| 16 | 24 random bursts on 4 banks / 2 rows match the reference | check |

## 3. UVM 測試平台內容

UVM 測試需商用模擬器（VCS / Xcelium / Questa）執行；開源流程只做 elaboration（L1a）。

| 項目 | 數量 | 名稱 |
|---|---|---|
| UVM tests | 3 | `ddr7_base_test`, `ddr7_directed_test`, `ddr7_stress_test` |
| Sequences | 12 | `ddr7_transaction`, `ddr7_base_sequence`, `ddr7_rw_round_seq`, `ddr7_write_seq`, `ddr7_read_seq`, `ddr7_refresh_seq`, `ddr7_bank_conflict_seq`, `ddr7_back_to_back_seq`, `ddr7_page_hit_seq`, `ddr7_page_miss_seq`, `ddr7_stress_seq`, `ddr7_regression_seq` |
| SVA（assert / cover property） | 40 / 28 | `a_ddr7_l1_clk`, `a_ddr7_l1_ca`, `a_ddr7_l1_addr`, `a_ddr7_l2_act_enc`, `a_ddr7_l2_bg`, `a_ddr7_l2_cke`, `a_ddr7_l3_reset_idle`, `a_ddr7_l3_ref_quiet`, `a_ddr7_l4_trcd`, `a_ddr7_l4_tras`, `a_ddr7_l4_tfaw`, `a_ddr7_l4_rdwr_open` … |
| Covergroups / coverpoints | 3 / 10 | |

## 4. 充分度判定與缺口

判定：**✅ Sufficient**（16 個 check，mutation score 100%）。

無已知缺口。

