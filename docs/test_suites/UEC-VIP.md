# UEC 測試套件（UEC-VIP）

> 由 `tools/gen_test_suite_docs.py` 依 VIP 內容、`func_report.csv` 與 `mutation_report.csv` 自動產生，請勿手動修改。

## 1. 概要

| 項目 | 內容 |
|---|---|
| 類別 | Networking |
| 類型 | UVM VIP |
| 功能測試 | 1 個檔案，16 個 check，全部通過 |
| Mutation | 12/12 個 mutant 被偵測（100%） |
| 判定 | **✅ Sufficient**（16 個 check，mutation score 100%） |

## 2. 可執行的功能測試

執行：`python3 tools/run_func_tests.py UEC-VIP`（Icarus Verilog 或 Verilator 5.052）。

### `tb/smoke_func_tb.sv`

結果：**PASS**（iverilog，16 checks）

| # | Check | 類型 |
|---|---|---|
| 1 | rx outputs defined low from time 0 | check |
| 2 | rx quiet in reset | check |
| 3 | tx_ready high | check |
| 4 | pipeline empty out of reset | check |
| 5 | latency not visible yet | check |
| 6 | good packet delivered | check |
| 7 | payload intact | check |
| 8 | no err on good packet | check |
| 9 | single-cycle delivery | check |
| 10 | undersize dropped | check |
| 11 | undersize err pulse | check |
| 12 | err is a pulse | check |
| 13 | oversize dropped with err | check |
| 14 | err clears | check |

## 3. UVM 測試平台內容

UVM agent test（`uec_func_test`：directed + constrained-random 流量，scoreboard 以 DUT 模型的參考模型逐筆比對，並比對 driver 與 monitor 的 transaction）在 Verilator 上以 `python3 tools/run_uvm_tests.py UEC-VIP` 執行；agent 由 `tools/gen_uvm_agents.py` 依 `tools/uvm_agents/` 的協定 spec 產生。

| 項目 | 數量 | 名稱 |
|---|---|---|
| UVM tests | 2 | `uec_base_test`, `uec_func_test` |
| Sequences | 3 | `uec_base_sequence`, `uec_directed_sequence`, `uec_transaction` |
| SVA（assert / cover property） | 4 / 2 | - |
| Covergroups / coverpoints | 1 / 2 | |

## 4. 充分度判定與缺口

判定：**✅ Sufficient**（16 個 check，mutation score 100%）。

無已知缺口。

