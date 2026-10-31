# 10BASE-T1S PLCA (IEEE 802.3cg) 測試套件（T1S_PLCA-UVM-VIP）

> 由 `tools/gen_test_suite_docs.py` 依 VIP 內容、`func_report.csv` 與 `mutation_report.csv` 自動產生，請勿手動修改。

## 1. 概要

| 項目 | 內容 |
|---|---|
| 類別 | Automotive |
| 類型 | UVM VIP |
| 功能測試 | 1 個檔案，19 個 check，全部通過 |
| Mutation | 9/9 個 mutant 被偵測（100%） |
| 判定 | **✅ Sufficient**（19 個 check，mutation score 100%） |

## 2. 可執行的功能測試

執行：`python3 tools/run_func_tests.py T1S_PLCA-UVM-VIP`（Icarus Verilog 或 Verilator 5.052）。

### `tb/smoke_func_tb.sv`

結果：**PASS**（verilator，19 checks）

模型合約與範圍（摘自測試檔頭）：

```text
Functional smoke testbench (10BASE-T1S PLCA DUT model)
```

| # | Check | 類型 |
|---|---|---|
| 1 | no report in reset | check |
| 2 | the coordinator starts with a BEACON, carrier on | check |
| 3 | no report without a frame | check |
| 4 | BEACONs repeat (%0d in 400 clocks) | check |
| 5 | BEACON exactly when the clause 148 counter ends a cycle (%0d clocks differ) | check |
| 6 | other nodes start only in their own opportunity, never in node 3's | check |
| 7 | other nodes' frames %0d..%0d clocks | check |
| 8 | BEACON lasts %0d clocks | check |
| 9 | other nodes send frames, unused opportunities expire | check |
| 10 | frame in its own opportunity: FCS good, no error, slot 3 | check |
| 11 | second frame in the same opportunity flagged | check |
| 12 | frame in node 5's opportunity flagged | check |
| 13 | the next cycle's opportunity: accepted | check |
| 14 | bad FCS reported | check |
| 15 | odd nibble count reported | check |
| 16 | frame during the BEACON flagged | check |
| 17 | frame over another node's carrier flagged | check |
| 18 | long frame: the opportunity lasts until the carrier falls | check |
| 19 | the next opportunity starts after the frame | check |

## 3. UVM 測試平台內容

UVM agent test（`t1s_plca_func_test`：directed + constrained-random 流量，scoreboard 以 DUT 模型的參考模型逐筆比對，並比對 driver 與 monitor 的 transaction）在 Verilator 上以 `python3 tools/run_uvm_tests.py T1S_PLCA-UVM-VIP` 執行；agent 由 `tools/gen_uvm_agents.py` 依 `tools/uvm_agents/` 的協定 spec 產生。

| 項目 | 數量 | 名稱 |
|---|---|---|
| UVM tests | 2 | `t1s_plca_base_test`, `t1s_plca_func_test` |
| Sequences | 3 | `t1s_plca_base_sequence`, `t1s_plca_directed_sequence`, `t1s_plca_transaction` |
| SVA（assert / cover property） | 6 / 2 | - |
| Covergroups / coverpoints | 1 / 3 | |

## 4. 充分度判定與缺口

判定：**✅ Sufficient**（19 個 check，mutation score 100%）。

無已知缺口。

