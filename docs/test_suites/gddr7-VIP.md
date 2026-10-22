# GDDR7 測試套件（gddr7-VIP）

> 由 `tools/gen_test_suite_docs.py` 依 VIP 內容、`func_report.csv` 與 `mutation_report.csv` 自動產生，請勿手動修改。

## 1. 概要

| 項目 | 內容 |
|---|---|
| 類別 | Memory |
| 類型 | UVM VIP |
| 功能測試 | 1 個檔案，15 個 check，全部通過 |
| Mutation | 7/7 個 mutant 被偵測（100%） |
| 判定 | **✅ Sufficient**（15 個 check，mutation score 100%） |

## 2. 可執行的功能測試

執行：`python3 tools/run_func_tests.py gddr7-VIP`（Icarus Verilog 或 Verilator 5.052）。

### `gddr7_vip/tb/func_mem_tb.sv`

結果：**PASS**（verilator，15 checks）

模型合約與範圍（摘自測試檔頭）：

```text
func_mem_tb.sv -- self-checking functional test for the GDDR7 memory model
(gddr7_mem_model, flattened by smoke/flatten.py). Run: python3 tools/run_func_tests.py gddr7-VIP

Model contract (from tb_top.sv):
   ACT (act_n=0) latches the row of {stack_id,bg,ba}; RD/WR (ras_n=1,cas_n=0)
   address column addr[9:0] of the open row. A write samples dq 1 clock
   after the command; a read drives dq on the negedge after 7 clocks
   (TCL=8) for one clock, then releases dq to Z.
dq is a variable shared by the model and the controller in the original
interface, so the test writes it hierarchically (u_dut.vif_dq) exactly as
the UVM driver writes vif.dq.
```

| # | Check | 類型 |
|---|---|---|
| 1 | write then read same bank/row/col returns written data | check |
| 2 | read data not yet on dq one clock before CL (read latency = TCL) | check |
| 3 | read data held for exactly one clock, then released | check |
| 4 | unwritten column reads 0 | check |
| 5 | second write to same address overwrites the first | check |
| 6 | bank 0 unaffected by writes to other banks | check |
| 7 | bank 1 holds its own data | check |
| 8 | bank group 3 holds its own data | check |
| 9 | stack_id 1 holds its own data | check |
| 10 | stack_id 0 unaffected by stack_id 1 write | check |
| 11 | new row in same bank does not alias the previous row | check |
| 12 | row data retained across PRE/ACT | check |
| 13 | second row data retained independently | check |
| 14 | write with CS_n high is ignored | check |
| 15 | command during reset had no effect | check |

## 3. UVM 測試平台內容

UVM 測試需商用模擬器（VCS / Xcelium / Questa）執行；開源流程只做 elaboration（L1a）。

| 項目 | 數量 | 名稱 |
|---|---|---|
| UVM tests | 4 | `gddr7_base_test`, `gddr7_write_test`, `gddr7_read_test`, `gddr7_stress_test` |
| Sequences | 11 | `gddr7_transaction`, `gddr7_base_sequence`, `gddr7_write_seq`, `gddr7_read_seq`, `gddr7_refresh_seq`, `gddr7_bank_conflict_seq`, `gddr7_back_to_back_seq`, `gddr7_stress_seq`, `gddr7_corner_seq`, `gddr7_random_sequence`, `gddr7_regression_sequence` |
| SVA（assert / cover property） | 32 / 24 | `assert_p_gddr7_cmd_valid`, `cover_p_gddr7_cmd_valid`, `assert_p_gddr7_addr_valid`, `cover_p_gddr7_addr_valid`, `assert_p_gddr7_bg`, `cover_p_gddr7_bg`, `assert_p_gddr7_ba`, `cover_p_gddr7_ba`, `assert_p_gddr7_tRCD`, `cover_p_gddr7_tRCD`, `assert_p_gddr7_tRP`, `cover_p_gddr7_tRP` … |
| Covergroups / coverpoints | 3 / 7 | |

## 4. 充分度判定與缺口

判定：**✅ Sufficient**（15 個 check，mutation score 100%）。

無已知缺口。

