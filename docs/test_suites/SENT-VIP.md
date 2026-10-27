# SENT 測試套件（SENT-VIP）

> 由 `tools/gen_test_suite_docs.py` 依 VIP 內容、`func_report.csv` 與 `mutation_report.csv` 自動產生，請勿手動修改。

## 1. 概要

| 項目 | 內容 |
|---|---|
| 類別 | Automotive |
| 類型 | UVM VIP |
| 功能測試 | 1 個檔案，16 個 check，全部通過 |
| Mutation | 15/15 個 mutant 被偵測（100%） |
| 判定 | **✅ Sufficient**（16 個 check，mutation score 100%） |

## 2. 可執行的功能測試

執行：`python3 tools/run_func_tests.py SENT-VIP`（Icarus Verilog 或 Verilator 5.052）。

### `tb/smoke_func_tb.sv`

結果：**PASS**（iverilog，16 checks）

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
| 9 | %0d-tick pulse decodes to nibble %0d | check |
| 10 | %0d-tick pulse is not a nibble | check |

## 3. UVM 測試平台內容

UVM agent test（`sent_func_test`：directed + constrained-random 流量，scoreboard 以 DUT 模型的參考模型逐筆比對，並比對 driver 與 monitor 的 transaction）在 Verilator 上以 `python3 tools/run_uvm_tests.py SENT-VIP` 執行；agent 由 `tools/gen_uvm_agents.py` 依 `tools/uvm_agents/` 的協定 spec 產生。

| 項目 | 數量 | 名稱 |
|---|---|---|
| UVM tests | 2 | `sent_base_test`, `sent_func_test` |
| Sequences | 3 | `sent_base_sequence`, `sent_directed_sequence`, `sent_transaction` |
| SVA（assert / cover property） | 3 / 2 | - |
| Covergroups / coverpoints | 1 / 2 | |

## 4. 充分度判定與缺口

判定：**✅ Sufficient**（16 個 check，mutation score 100%）。

無已知缺口。

