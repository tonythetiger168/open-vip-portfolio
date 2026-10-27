# RapidIO 測試套件（RapidIO-VIP）

> 由 `tools/gen_test_suite_docs.py` 依 VIP 內容、`func_report.csv` 與 `mutation_report.csv` 自動產生，請勿手動修改。

## 1. 概要

| 項目 | 內容 |
|---|---|
| 類別 | Interconnect |
| 類型 | UVM VIP |
| 功能測試 | 1 個檔案，22 個 check，全部通過 |
| Mutation | 3/3 個 mutant 被偵測（100%） |
| 判定 | **✅ Sufficient**（22 個 check，mutation score 100%） |

## 2. 可執行的功能測試

執行：`python3 tools/run_func_tests.py RapidIO-VIP`（Icarus Verilog 或 Verilator 5.052）。

### `tb/smoke_func_tb.sv`

結果：**PASS**（iverilog，22 checks）

| # | Check | 類型 |
|---|---|---|
| 1 | out_valid quiet out of reset | check |
| 2 | out_soc quiet in reset | check |
| 3 | out_valid low without input | check |
| 4 | symbol forwarded | check |
| 5 | symbol data integrity | check |
| 6 | start-of-control passthrough | check |
| 7 | priority passthrough | check |
| 8 | out_valid drops after burst | check |

## 3. UVM 測試平台內容

UVM agent test（`rapidio_func_test`：directed + constrained-random 流量，scoreboard 以 DUT 模型的參考模型逐筆比對，並比對 driver 與 monitor 的 transaction）在 Verilator 上以 `python3 tools/run_uvm_tests.py RapidIO-VIP` 執行；agent 由 `tools/gen_uvm_agents.py` 依 `tools/uvm_agents/` 的協定 spec 產生。

| 項目 | 數量 | 名稱 |
|---|---|---|
| UVM tests | 2 | `rapidio_base_test`, `rapidio_func_test` |
| Sequences | 3 | `rapidio_base_sequence`, `rapidio_directed_sequence`, `rapidio_transaction` |
| SVA（assert / cover property） | 3 / 2 | - |
| Covergroups / coverpoints | 1 / 2 | |

## 4. 充分度判定與缺口

判定：**✅ Sufficient**（22 個 check，mutation score 100%）。

無已知缺口。

