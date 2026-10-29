# OBI 測試套件（OBI-UVM-VIP）

> 由 `tools/gen_test_suite_docs.py` 依 VIP 內容、`func_report.csv` 與 `mutation_report.csv` 自動產生，請勿手動修改。

## 1. 概要

| 項目 | 內容 |
|---|---|
| 類別 | Interconnect |
| 類型 | UVM VIP |
| 功能測試 | 1 個檔案，39 個 check，全部通過 |
| Mutation | 13/13 個 mutant 被偵測（100%） |
| 判定 | **✅ Sufficient**（39 個 check，mutation score 100%） |

## 2. 可執行的功能測試

執行：`python3 tools/run_func_tests.py OBI-UVM-VIP`（Icarus Verilog 或 Verilator 5.052）。

### `tb/smoke_func_tb.sv`

結果：**PASS**（iverilog，39 checks）

模型合約與範圍（摘自測試檔頭）：

```text
Functional smoke testbench (OBI DUT model)
```

| # | Check | 類型 |
|---|---|---|
| 1 | request granted | check |
| 2 | response returned | check |
| 3 | rid echoes aid | check |
| 4 | idle out of reset | check |
| 5 | word 0 reads 0 after reset | check |
| 6 | last word (0x3FC) reads 0 after reset, in range | check |
| 7 | 0x400 is the first out-of-range address | check |
| 8 | write in range: no error | check |
| 9 | read back full word | check |
| 10 | byte-enable merge on lane 1 | check |
| 11 | write above 0x3FF: error response | check |
| 12 | read above 0x3FF: error response, rdata 0 | check |
| 13 | four outstanding requests, then no gnt while the FIFO is full | check |
| 14 | response held while rready is low | check |
| 15 | FIFO drains when rready returns | check |

## 3. UVM 測試平台內容

UVM agent test（`obi_func_test`：directed + constrained-random 流量，scoreboard 以 DUT 模型的參考模型逐筆比對，並比對 driver 與 monitor 的 transaction）在 Verilator 上以 `python3 tools/run_uvm_tests.py OBI-UVM-VIP` 執行；agent 由 `tools/gen_uvm_agents.py` 依 `tools/uvm_agents/` 的協定 spec 產生。

| 項目 | 數量 | 名稱 |
|---|---|---|
| UVM tests | 2 | `obi_base_test`, `obi_func_test` |
| Sequences | 3 | `obi_base_sequence`, `obi_directed_sequence`, `obi_transaction` |
| SVA（assert / cover property） | 6 / 3 | - |
| Covergroups / coverpoints | 1 / 4 | |

## 4. 充分度判定與缺口

判定：**✅ Sufficient**（39 個 check，mutation score 100%）。

無已知缺口。

