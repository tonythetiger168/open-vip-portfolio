# UCIe 測試套件（UCIe-VIP）

> 由 `tools/gen_test_suite_docs.py` 依 VIP 內容、`func_report.csv` 與 `mutation_report.csv` 自動產生，請勿手動修改。

## 1. 概要

| 項目 | 內容 |
|---|---|
| 類別 | Interconnect |
| 類型 | UVM VIP |
| 功能測試 | 1 個檔案，19 個 check，全部通過 |
| Mutation | 12/12 個 mutant 被偵測（100%） |
| 判定 | **✅ Sufficient**（19 個 check，mutation score 100%） |

## 2. 可執行的功能測試

執行：`python3 tools/run_func_tests.py UCIe-VIP`（Icarus Verilog 或 Verilator 5.052）。

### `tb/smoke_func_tb.sv`

結果：**PASS**（iverilog，19 checks）

| # | Check | 類型 |
|---|---|---|
| 1 | tready high when empty | check |
| 2 | rvalid low when empty | check |
| 3 | flit0 head of queue | check |
| 4 | flit1 loopback order | check |
| 5 | flit2 loopback with tlast | check |
| 6 | drained after 3 flits | check |
| 7 | accept while not full | check |
| 8 | tready low when full | check |
| 9 | oldest flit at head | check |
| 10 | fully drained after backpressure test | check |
| 11 | tready high when empty | check |
| 12 | all 6 burst flits delivered | check |

## 3. UVM 測試平台內容

UVM agent test（`ucie_func_test`：directed + constrained-random 流量，scoreboard 以 DUT 模型的參考模型逐筆比對，並比對 driver 與 monitor 的 transaction）在 Verilator 上以 `python3 tools/run_uvm_tests.py UCIe-VIP` 執行；agent 由 `tools/gen_uvm_agents.py` 依 `tools/uvm_agents/` 的協定 spec 產生。

| 項目 | 數量 | 名稱 |
|---|---|---|
| UVM tests | 2 | `ucie_base_test`, `ucie_func_test` |
| Sequences | 3 | `ucie_base_sequence`, `ucie_directed_sequence`, `ucie_transaction` |
| SVA（assert / cover property） | 3 / 2 | - |
| Covergroups / coverpoints | 1 / 1 | |

## 4. 充分度判定與缺口

判定：**✅ Sufficient**（19 個 check，mutation score 100%）。

無已知缺口。

