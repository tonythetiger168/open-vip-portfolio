# SENT 測試套件（SENT-VIP）

> 由 `tools/gen_test_suite_docs.py` 依 VIP 內容、`func_report.csv` 與 `mutation_report.csv` 自動產生，請勿手動修改。

## 1. 概要

| 項目 | 內容 |
|---|---|
| 類別 | Automotive |
| 類型 | UVM VIP |
| 功能測試 | 1 個檔案，12 個 check，全部通過 |
| Mutation | 12/16 個 mutant 被偵測（75%） |
| 判定 | **🟡 Partial**（mutation score 75%） |

## 2. 可執行的功能測試

執行：`python3 tools/run_func_tests.py SENT-VIP`（Icarus Verilog 或 Verilator 5.052）。

### `tb/smoke_func_tb.sv`

結果：**PASS**（iverilog，12 checks）

| # | Check | 類型 |
|---|---|---|
| 1 | decoder quiet out of reset | check |
| 2 | tick counter increments | check |
| 3 | nibble valid strobe | check |
| 4 | nibble 5 decoded (8 ticks) | check |
| 5 | valid strobe is a pulse | check |
| 6 | second nibble strobe | check |
| 7 | nibble 12 decoded (15 ticks) | check |
| 8 | illegal short pulse ignored | check |

## 3. UVM 測試平台內容

UVM 測試需商用模擬器（VCS / Xcelium / Questa）執行；開源流程只做 elaboration（L1a）。

| 項目 | 數量 | 名稱 |
|---|---|---|
| UVM tests | 1 | `sent_base_test` |
| Sequences | 2 | `sent_base_sequence`, `sent_transaction` |
| SVA（assert / cover property） | 3 / 2 | - |
| Covergroups / coverpoints | 1 / 1 | |

## 4. 充分度判定與缺口

判定：**🟡 Partial**（mutation score 75%）。

未被偵測的 mutant（測試缺口或等價 mutant）：

- `dut_sent_model.sv:22 1'b1 inverted [so_d         <= 1'b1;]`
- `dut_sent_model.sv:33 && flipped [if (low_cnt >= 8'd3 && low_cnt <= 8'd27) begin]`
- `dut_sent_model.sv:33 >= -> > in condition [if (low_cnt >= 8'd3 && low_cnt <= 8'd27) begin]`
- `dut_sent_model.sv:33 <= -> < in condition [if (low_cnt >= 8'd3 && low_cnt <= 8'd27) begin]`

