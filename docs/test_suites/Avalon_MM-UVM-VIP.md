# Avalon-MM 測試套件（Avalon_MM-UVM-VIP）

> 由 `tools/gen_test_suite_docs.py` 依 VIP 內容、`func_report.csv` 與 `mutation_report.csv` 自動產生，請勿手動修改。

## 1. 概要

| 項目 | 內容 |
|---|---|
| 類別 | Interconnect |
| 類型 | UVM VIP |
| 功能測試 | 1 個檔案，73 個 check，全部通過 |
| Mutation | 11/11 個 mutant 被偵測（100%） |
| 判定 | **✅ Sufficient**（73 個 check，mutation score 100%） |

## 2. 可執行的功能測試

執行：`python3 tools/run_func_tests.py Avalon_MM-UVM-VIP`（Icarus Verilog 或 Verilator 5.052）。

### `tb/smoke_func_tb.sv`

結果：**PASS**（iverilog，73 checks）

| # | Check | 類型 |
|---|---|---|
| 1 | waitrequest reset low | check |
| 2 | waitrequest stays low in reset even with a command | check |
| 3 | response reset OKAY | check |
| 4 | readdatavalid reset low | check |
| 5 | no readdatavalid out of reset | check |
| 6 | write: waitrequest high on the first clock | check |
| 7 | write: waitrequest low on the second clock | check |
| 8 | write not taken while waitrequest was high | check |
| 9 | write taken on the clock waitrequest was low | check |
| 10 | a write returns no readdatavalid | check |
| 11 | read: waitrequest high on the first clock | check |
| 12 | read: waitrequest low on the second clock | check |
| 13 | readdatavalid two clocks after the transfer | check |
| 14 | read data from the accepted address | check |
| 15 | response OKAY | check |
| 16 | readdatavalid lasts one clock | check |
| 17 | held command: next transfer starts with a wait state | check |
| 18 | second transfer not taken during its wait state | check |
| 19 | back-to-back writes both stored, once each | check |
| 20 | waitrequest low while idle | check |
| 21 | no readdatavalid when idle | check |
| 22 | command at reset release: waitrequest high on its first clock | check |
| 23 | word %0d reads 0 after reset | check |

## 3. UVM 測試平台內容

UVM agent test（`avalon_mm_func_test`：directed + constrained-random 流量，scoreboard 以 DUT 模型的參考模型逐筆比對，並比對 driver 與 monitor 的 transaction）在 Verilator 上以 `python3 tools/run_uvm_tests.py Avalon_MM-UVM-VIP` 執行；agent 由 `tools/gen_uvm_agents.py` 依 `tools/uvm_agents/` 的協定 spec 產生。

| 項目 | 數量 | 名稱 |
|---|---|---|
| UVM tests | 3 | `avalon_mm_base_test`, `avalon_mm_func_test`, `avalon_mm_ral_test` |
| Sequences | 3 | `avalon_mm_base_sequence`, `avalon_mm_directed_sequence`, `avalon_mm_transaction` |
| SVA（assert / cover property） | 4 / 2 | - |
| Covergroups / coverpoints | 1 / 2 | |

## 4. 充分度判定與缺口

判定：**✅ Sufficient**（73 個 check，mutation score 100%）。

無已知缺口。

