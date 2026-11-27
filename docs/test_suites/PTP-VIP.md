# IEEE 1588 PTP 測試套件（PTP-VIP）

> 由 `tools/gen_test_suite_docs.py` 依 VIP 內容、`func_report.csv` 與 `mutation_report.csv` 自動產生，請勿手動修改。

## 1. 概要

| 項目 | 內容 |
|---|---|
| 類別 | Networking |
| 類型 | UVM VIP |
| 功能測試 | 1 個檔案，114 個 check，全部通過 |
| Mutation | 30/30 個 mutant 被偵測（100%） |
| 判定 | **✅ Sufficient**（114 個 check，mutation score 100%） |

## 2. 可執行的功能測試

執行：`python3 tools/run_func_tests.py PTP-VIP`（Icarus Verilog 或 Verilator 5.054）。

### `tb/smoke_func_tb.sv`

結果：**PASS**（iverilog，114 checks）

模型合約與範圍（摘自測試檔頭）：

```text
Functional smoke testbench (PTP DUT model)
```

| # | Check | 類型 |
|---|---|---|
| 1 | %s: drop %0d (got %0d, %0d done) | check |
| 2 | reset values | check |
| 3 | free-running clock 8 ns per cycle (%0d) | check |
| 4 | no frame reported or sent after reset | check |
| 5 | nothing selected, nothing sent | check |
| 6 | A selected | check |
| 7 | worse priority1: A kept | check |
| 8 | better clockQuality: B selected | check |
| 9 | better priority2: A selected | check |
| 10 | identity tie-break: C selected | check |
| 11 | the master's own Announce updates its dataset | check |
| 12 | A selected over C's new dataset | check |
| 13 | equal dataset from another port: master port kept | check |
| 14 | no Delay_Req before the delay | check |
| 15 | Delay_Req 4 clocks after the Sync (%0d) | check |
| 16 | Delay_Req is 58 bytes (%0d) | check |
| 17 | Delay_Req Ethernet header | check |
| 18 | Delay_Req message header | check |
| 19 | Delay_Req correction 0 | check |
| 20 | Delay_Req sourcePortIdentity | check |
| 21 | first Delay_Req sequenceId 0 | check |
| 22 | originTimestamp = t3 (%0d) | check |
| 23 | reserved bytes zero | check |
| 24 | offset -50 ms, delay 48 (%0d, %0d) | check |
| 25 | clock stepped +50 ms (%0d) | check |
| 26 | two-step: no Delay_Req before the Follow_Up | check |
| 27 | second Delay_Req sequenceId 1 | check |
| 28 | originTimestamp = t3 after the step (%0d) | check |
| 29 | offset +5 us, delay 100 (%0d, %0d) | check |
| 30 | clock stepped -5 us (%0d) | check |
| 31 | third Delay_Req sequenceId 2 | check |
| 32 | offset 100, delay 200 (%0d, %0d) | check |
| 33 | delay (7 + 8) / 2 = 7, offset 0 (%0d, %0d) | check |
| 34 | delay of the second exchange (%0d) | check |
| 35 | Delay_Req carries domainNumber 5 | check |
| 36 | reset clears the clock and the master | check |
| 37 | Delay_Req sequenceId restarts at 0 | check |
| 38 | zero offset, zero delay | check |
| 39 | clock stepped +3 s (%0d) | check |
| 40 | originTimestamp seconds 3 (%0d) | check |
| 41 | tx_last only with tx_valid (%0d) | check |

## 3. UVM 測試平台內容

UVM agent test（`ptp_func_test`：directed + constrained-random 流量，scoreboard 以 DUT 模型的參考模型逐筆比對，並比對 driver 與 monitor 的 transaction）在 Verilator 上以 `python3 tools/run_uvm_tests.py PTP-VIP` 執行；agent 由 `tools/gen_uvm_agents.py` 依 `tools/uvm_agents/` 的協定 spec 產生。

| 項目 | 數量 | 名稱 |
|---|---|---|
| UVM tests | 2 | `ptp_base_test`, `ptp_func_test` |
| Sequences | 3 | `ptp_base_sequence`, `ptp_directed_sequence`, `ptp_transaction` |
| SVA（assert / cover property） | 9 / 3 | - |
| Covergroups / coverpoints | 1 / 13 | |

## 4. 充分度判定與缺口

判定：**✅ Sufficient**（114 個 check，mutation score 100%）。

無已知缺口。

