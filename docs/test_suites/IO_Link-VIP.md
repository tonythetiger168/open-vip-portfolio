# IO-Link 測試套件（IO_Link-VIP）

> 由 `tools/gen_test_suite_docs.py` 依 VIP 內容、`func_report.csv` 與 `mutation_report.csv` 自動產生，請勿手動修改。

## 1. 概要

| 項目 | 內容 |
|---|---|
| 類別 | Industrial |
| 類型 | UVM VIP |
| 功能測試 | 1 個檔案，12 個 check，全部通過 |
| Mutation | 28/28 個 mutant 被偵測（100%） |
| 判定 | **✅ Sufficient**（12 個 check，mutation score 100%） |

## 2. 可執行的功能測試

執行：`python3 tools/run_func_tests.py IO_Link-VIP`（Icarus Verilog 或 Verilator 5.052）。

### `tb/smoke_func_tb.sv`

結果：**PASS**（iverilog，12 checks）

| # | Check | 類型 |
|---|---|---|
| 1 | tx line idle high | check |
| 2 | handshakes quiet | check |
| 3 | no rx_valid for 50 clocks out of reset with rx idle | check |
| 4 | tx_cnf after transmission | check |
| 5 | serial frame observed on tx | check |
| 6 | serialised data integrity | check |
| 7 | stop bit is high | check |
| 8 | tx_cnf is a one-clock pulse (%0d) | check |
| 9 | rx_valid after host byte | check |
| 10 | received data integrity | check |
| 11 | rx_valid after the second host byte | check |
| 12 | second received byte integrity | check |

## 3. UVM 測試平台內容

UVM agent test（`io_link_func_test`：directed + constrained-random 流量，scoreboard 以 DUT 模型的參考模型逐筆比對，並比對 driver 與 monitor 的 transaction）在 Verilator 上以 `python3 tools/run_uvm_tests.py IO_Link-VIP` 執行；agent 由 `tools/gen_uvm_agents.py` 依 `tools/uvm_agents/` 的協定 spec 產生。

| 項目 | 數量 | 名稱 |
|---|---|---|
| UVM tests | 2 | `io_link_base_test`, `io_link_func_test` |
| Sequences | 3 | `io_link_base_sequence`, `io_link_directed_sequence`, `io_link_transaction` |
| SVA（assert / cover property） | 3 / 2 | - |
| Covergroups / coverpoints | 1 / 2 | |

## 4. 充分度判定與缺口

判定：**✅ Sufficient**（12 個 check，mutation score 100%）。

無已知缺口。

