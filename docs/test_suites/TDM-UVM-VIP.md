# TDM audio (DSP mode) 測試套件（TDM-UVM-VIP）

> 由 `tools/gen_test_suite_docs.py` 依 VIP 內容、`func_report.csv` 與 `mutation_report.csv` 自動產生，請勿手動修改。

## 1. 概要

| 項目 | 內容 |
|---|---|
| 類別 | Audio |
| 類型 | UVM VIP |
| 功能測試 | 1 個檔案，13 個 check，全部通過 |
| Mutation | 17/17 個 mutant 被偵測（100%） |
| 判定 | **✅ Sufficient**（13 個 check，mutation score 100%） |

## 2. 可執行的功能測試

執行：`python3 tools/run_func_tests.py TDM-UVM-VIP`（Icarus Verilog 或 Verilator 5.052）。

### `tb/smoke_func_tb.sv`

結果：**PASS**（iverilog，13 checks）

模型合約與範圍（摘自測試檔頭）：

```text
Functional smoke testbench (TDM audio DUT model)
```

| # | Check | 類型 |
|---|---|---|
| 1 | no report during reset | check |
| 2 | no frame open after reset | check |
| 3 | TDM8 frame: slot i = i, no error | check |
| 4 | report only after the frame's last bit | check |
| 5 | back-to-back frames: both reported | check |
| 6 | first bit after FSYNC is the MSB of slot 0 | check |
| 7 | last bit is the LSB of slot 7 | check |
| 8 | FSYNC two clocks wide: framing error, data kept | check |
| 9 | early FSYNC: two reports | check |
| 10 | the cut frame: framing error, its 40 bits MSB-aligned | check |
| 11 | the restarted frame is clean | check |
| 12 | frames after idle gaps | check |
| 13 | no frame without FSYNC | check |

## 3. UVM 測試平台內容

UVM agent test（`tdm_func_test`：directed + constrained-random 流量，scoreboard 以 DUT 模型的參考模型逐筆比對，並比對 driver 與 monitor 的 transaction）在 Verilator 上以 `python3 tools/run_uvm_tests.py TDM-UVM-VIP` 執行；agent 由 `tools/gen_uvm_agents.py` 依 `tools/uvm_agents/` 的協定 spec 產生。

| 項目 | 數量 | 名稱 |
|---|---|---|
| UVM tests | 2 | `tdm_base_test`, `tdm_func_test` |
| Sequences | 3 | `tdm_base_sequence`, `tdm_directed_sequence`, `tdm_transaction` |
| SVA（assert / cover property） | 3 / 4 | - |
| Covergroups / coverpoints | 1 / 4 | |

## 4. 充分度判定與缺口

判定：**✅ Sufficient**（13 個 check，mutation score 100%）。

無已知缺口。

