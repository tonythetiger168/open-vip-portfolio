# V-by-One HS panel sink 測試套件（VbyOne_HS-UVM-VIP）

> 由 `tools/gen_test_suite_docs.py` 依 VIP 內容、`func_report.csv` 與 `mutation_report.csv` 自動產生，請勿手動修改。

## 1. 概要

| 項目 | 內容 |
|---|---|
| 類別 | Video |
| 類型 | UVM VIP |
| 功能測試 | 1 個檔案，12 個 check，全部通過 |
| Mutation | 27/27 個 mutant 被偵測（100%） |
| 判定 | **✅ Sufficient**（12 個 check，mutation score 100%） |

## 2. 可執行的功能測試

執行：`python3 tools/run_func_tests.py VbyOne_HS-UVM-VIP`（Icarus Verilog 或 Verilator 5.052）。

### `tb/smoke_func_tb.sv`

結果：**PASS**（iverilog，12 checks）

模型合約與範圍（摘自測試檔頭）：

```text
Functional smoke testbench (VbyOne DUT model)
```

| # | Check | 類型 |
|---|---|---|
| 1 | unplugged: training only, a symbol every 2 clocks | check |
| 2 | HTPDN low, LOCKN high: still training | check |
| 3 | locked: K28.5 idle | check |
| 4 | frame start: K28.2, 2 groups, 4 padded pixels | check |
| 5 | next line: K28.0 | check |
| 6 | two full groups | check |
| 7 | one pixel, 7 padded | check |
| 8 | input gaps: K28.5 between groups | check |
| 9 | 40 pixels | check |
| 10 | LOCKN high: training again | check |
| 11 | line after the relock | check |
| 12 | no malformed symbol | check |

## 3. UVM 測試平台內容

UVM agent test（`vbo_func_test`：directed + constrained-random 流量，scoreboard 以 DUT 模型的參考模型逐筆比對，並比對 driver 與 monitor 的 transaction）在 Verilator 上以 `python3 tools/run_uvm_tests.py VbyOne_HS-UVM-VIP` 執行；agent 由 `tools/gen_uvm_agents.py` 依 `tools/uvm_agents/` 的協定 spec 產生。

| 項目 | 數量 | 名稱 |
|---|---|---|
| UVM tests | 2 | `vbo_base_test`, `vbo_func_test` |
| Sequences | 3 | `vbo_base_sequence`, `vbo_directed_sequence`, `vbo_transaction` |
| SVA（assert / cover property） | 5 / 1 | - |
| Covergroups / coverpoints | 1 / 3 | |

## 4. 充分度判定與缺口

判定：**✅ Sufficient**（12 個 check，mutation score 100%）。

無已知缺口。

