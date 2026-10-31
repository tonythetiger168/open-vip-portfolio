# EtherCAT 測試套件（EtherCAT-VIP）

> 由 `tools/gen_test_suite_docs.py` 依 VIP 內容、`func_report.csv` 與 `mutation_report.csv` 自動產生，請勿手動修改。

## 1. 概要

| 項目 | 內容 |
|---|---|
| 類別 | Industrial |
| 類型 | UVM VIP |
| 功能測試 | 1 個檔案，23 個 check，全部通過 |
| Mutation | 3/3 個 mutant 被偵測（100%） |
| 判定 | **✅ Sufficient**（23 個 check，mutation score 100%） |

## 2. 可執行的功能測試

執行：`python3 tools/run_func_tests.py EtherCAT-VIP`（Icarus Verilog 或 Verilator 5.052）。

### `tb/smoke_func_tb.sv`

結果：**PASS**（iverilog，23 checks）

| # | Check | 類型 |
|---|---|---|
| 1 | tx_en quiet out of reset | check |
| 2 | tx_er quiet in reset | check |
| 3 | txd idle nibble (0x5) | check |
| 4 | tx_en low between frames | check |
| 5 | idle nibble while not forwarding | check |
| 6 | tx_en high during frame | check |
| 7 | forwarded nibble integrity | check |
| 8 | tx_en drops at frame end | check |
| 9 | process data passthrough | check |

## 3. UVM 測試平台內容

UVM agent test（`ethercat_func_test`：directed + constrained-random 流量，scoreboard 以 DUT 模型的參考模型逐筆比對，並比對 driver 與 monitor 的 transaction）在 Verilator 上以 `python3 tools/run_uvm_tests.py EtherCAT-VIP` 執行；agent 由 `tools/gen_uvm_agents.py` 依 `tools/uvm_agents/` 的協定 spec 產生。

| 項目 | 數量 | 名稱 |
|---|---|---|
| UVM tests | 2 | `ethercat_base_test`, `ethercat_func_test` |
| Sequences | 3 | `ethercat_base_sequence`, `ethercat_directed_sequence`, `ethercat_transaction` |
| SVA（assert / cover property） | 3 / 2 | - |
| Covergroups / coverpoints | 1 / 3 | |

## 4. 充分度判定與缺口

判定：**✅ Sufficient**（23 個 check，mutation score 100%）。

無已知缺口。

