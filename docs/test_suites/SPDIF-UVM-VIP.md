# S/PDIF (IEC 60958) 測試套件（SPDIF-UVM-VIP）

> 由 `tools/gen_test_suite_docs.py` 依 VIP 內容、`func_report.csv` 與 `mutation_report.csv` 自動產生，請勿手動修改。

## 1. 概要

| 項目 | 內容 |
|---|---|
| 類別 | Audio |
| 類型 | UVM VIP |
| 功能測試 | 1 個檔案，26 個 check，全部通過 |
| Mutation | 27/27 個 mutant 被偵測（100%） |
| 判定 | **✅ Sufficient**（26 個 check，mutation score 100%） |

## 2. 可執行的功能測試

執行：`python3 tools/run_func_tests.py SPDIF-UVM-VIP`（Icarus Verilog 或 Verilator 5.054）。

### `tb/smoke_func_tb.sv`

結果：**PASS**（iverilog，26 checks）

模型合約與範圍（摘自測試檔頭）：

```text
Functional smoke testbench (SPDIF DUT model)
```

| # | Check | 類型 |
|---|---|---|
| 1 | no report in reset | check |
| 2 | no report on an idle line | check |
| 3 | B subframe: data, C = 1, parity ok | check |
| 4 | W subframe | check |
| 5 | M subframe, all zeros, V = 1 | check |
| 6 | all ones, U = 1 (parity 1) | check |
| 7 | parity error: data kept | check |
| 8 | missing transition: violation | check |
| 9 | next subframe received after re-lock | check |
| 10 | illegal preamble, then W | check |
| 11 | line stops inside a subframe | check |
| 12 | edge jitter at the window limits | check |
| 13 | channel status word after 32 frames | check |
| 14 | no second word without a new B | check |
| 15 | a run of 3 clocks is a violation | check |
| 16 | two runs of 3 clocks are not a 1 cell | check |
| 17 | two runs of 4 clocks are a 1 cell (parity now odd) | check |
| 18 | a run of 20 clocks (2.5 UI) in a cell is a violation | check |
| 19 | a run of 19 clocks is a 0 cell | check |
| 20 | a first preamble run of 28 clocks is not one: the hunt locks on the next 3 UI run and fails | check |
| 21 | a first preamble run of 27 clocks starts a preamble | check |
| 22 | preamble 3,3,1,3 is illegal | check |
| 23 | preamble 3,3,1,2 is illegal | check |
| 24 | preamble 3,1,3,3 is illegal | check |
| 25 | preamble 3,2,2,2 is illegal | check |
| 26 | channel status from 32 channel A subframes without W | check |

## 3. UVM 測試平台內容

UVM agent test（`spdif_func_test`：directed + constrained-random 流量，scoreboard 以 DUT 模型的參考模型逐筆比對，並比對 driver 與 monitor 的 transaction）在 Verilator 上以 `python3 tools/run_uvm_tests.py SPDIF-UVM-VIP` 執行；agent 由 `tools/gen_uvm_agents.py` 依 `tools/uvm_agents/` 的協定 spec 產生。

| 項目 | 數量 | 名稱 |
|---|---|---|
| UVM tests | 2 | `spdif_base_test`, `spdif_func_test` |
| Sequences | 3 | `spdif_base_sequence`, `spdif_directed_sequence`, `spdif_transaction` |
| SVA（assert / cover property） | 4 / 2 | - |
| Covergroups / coverpoints | 1 / 4 | |

## 4. 充分度判定與缺口

判定：**✅ Sufficient**（26 個 check，mutation score 100%）。

無已知缺口。

