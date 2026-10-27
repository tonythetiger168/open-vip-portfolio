# SDIO 測試套件（SDIO-UVM-VIP）

> 由 `tools/gen_test_suite_docs.py` 依 VIP 內容、`func_report.csv` 與 `mutation_report.csv` 自動產生，請勿手動修改。

## 1. 概要

| 項目 | 內容 |
|---|---|
| 類別 | Storage |
| 類型 | UVM VIP |
| 功能測試 | 1 個檔案，27 個 check，全部通過 |
| Mutation | 17/17 個 mutant 被偵測（100%） |
| 判定 | **✅ Sufficient**（27 個 check，mutation score 100%） |

## 2. 可執行的功能測試

執行：`python3 tools/run_func_tests.py SDIO-UVM-VIP`（Icarus Verilog 或 Verilator 5.052）。

### `tb/smoke_func_tb.sv`

結果：**PASS**（iverilog，27 checks）

| # | Check | 類型 |
|---|---|---|
| 1 | card quiet out of reset | check |
| 2 | no response without command | check |
| 3 | CMD8 response driven | check |
| 4 | response carries low bits (not stuck high) | check |
| 5 | card released after response | check |
| 6 | CMD%0d: response is 48 bits long (%0d) | check |
| 7 | CMD%0d: response bits %h, expected %h | check |
| 8 | CMD%0d: DAT drives 4'h5 for 8 bits (%0d) | check |

## 3. UVM 測試平台內容

UVM agent test（`sdio_func_test`：directed + constrained-random 流量，scoreboard 以 DUT 模型的參考模型逐筆比對，並比對 driver 與 monitor 的 transaction）在 Verilator 上以 `python3 tools/run_uvm_tests.py SDIO-UVM-VIP` 執行；agent 由 `tools/gen_uvm_agents.py` 依 `tools/uvm_agents/` 的協定 spec 產生。

| 項目 | 數量 | 名稱 |
|---|---|---|
| UVM tests | 2 | `sdio_base_test`, `sdio_func_test` |
| Sequences | 3 | `sdio_base_sequence`, `sdio_directed_sequence`, `sdio_transaction` |
| SVA（assert / cover property） | 3 / 2 | - |
| Covergroups / coverpoints | 1 / 1 | |

## 4. 充分度判定與缺口

判定：**✅ Sufficient**（27 個 check，mutation score 100%）。

無已知缺口。

