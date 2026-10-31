# SpaceWire (ECSS-E-ST-50-12C) 測試套件（SpaceWire-UVM-VIP）

> 由 `tools/gen_test_suite_docs.py` 依 VIP 內容、`func_report.csv` 與 `mutation_report.csv` 自動產生，請勿手動修改。

## 1. 概要

| 項目 | 內容 |
|---|---|
| 類別 | Aerospace |
| 類型 | UVM VIP |
| 功能測試 | 1 個檔案，38 個 check，全部通過 |
| Mutation | 25/26 個 mutant 被偵測（96%） |
| 判定 | **✅ Sufficient**（38 個 check，mutation score 96%） |

## 2. 可執行的功能測試

執行：`python3 tools/run_func_tests.py SpaceWire-UVM-VIP`（Icarus Verilog 或 Verilator 5.052）。

### `tb/smoke_func_tb.sv`

結果：**PASS**（iverilog，38 checks）

模型合約與範圍（摘自測試檔頭）：

```text
Functional smoke testbench (SpaceWire DUT model)
```

| # | Check | 類型 |
|---|---|---|
| 1 | no FCT after a link reset before a NULL arrives | check |
| 2 | lines low and no report during reset | check |
| 3 | transmitter silent after reset | check |
| 4 | NULLs only until a NULL is received (%0d NULLs, %0d FCTs) | check |
| 5 | no report while the line in is quiet | check |
| 6 | first bit out %0d clocks after reset | check |
| 7 | two FCTs after the first NULL (%0d) | check |
| 8 | packet: 9 bytes, CRC-32 0xCBF43926, EOP (%0d %h %0d) | check |
| 9 | one more FCT once 8 N-chars were used (%0d) | check |
| 10 | credit back up: 24 given, 10 used | check |
| 11 | packet ended by EEP | check |
| 12 | empty packet | check |
| 13 | 30-byte packet across several FCTs | check |
| 14 | FCT received from the agent ignored | check |
| 15 | time-code 1 after 0: tick | check |
| 16 | time-code 5 after 1: no tick, no packet fields | check |
| 17 | time-code 6 with flags: tick, flags kept | check |
| 18 | time-code 63 -> 0 wraps: tick | check |
| 19 | time-codes and NULLs use no credit | check |
| 20 | parity error: code 1, the 2 bytes before it (%0d %0d) | check |
| 21 | transmitter silent after the error (%0d quiet clocks) | check |
| 22 | the characters after the error were ignored | check |
| 23 | link restarts: two FCTs after NULLs (%0d) | check |
| 24 | packet after the restart | check |
| 25 | ESC + EOP: escape error | check |
| 26 | no restart on a stream that never went quiet | check |
| 27 | receiver starts after the minimum quiet time | check |
| 28 | ESC + ESC: escape error | check |
| 29 | ESC + EEP: escape error | check |
| 30 | no start on a bit right after both lines dropped | check |
| 31 | N-char without credit: credit error | check |
| 32 | clean packet at the end | check |
| 33 | the DUT's characters have odd parity | check |
| 34 | DUT bits last 3 clocks (%0d..%0d) | check |
| 35 | lines low from the clock of an error report | check |
| 36 | D and S out never change together | check |

## 3. UVM 測試平台內容

UVM agent test（`spacewire_func_test`：directed + constrained-random 流量，scoreboard 以 DUT 模型的參考模型逐筆比對，並比對 driver 與 monitor 的 transaction）在 Verilator 上以 `python3 tools/run_uvm_tests.py SpaceWire-UVM-VIP` 執行；agent 由 `tools/gen_uvm_agents.py` 依 `tools/uvm_agents/` 的協定 spec 產生。

| 項目 | 數量 | 名稱 |
|---|---|---|
| UVM tests | 2 | `spacewire_base_test`, `spacewire_func_test` |
| Sequences | 3 | `spacewire_base_sequence`, `spacewire_directed_sequence`, `spacewire_transaction` |
| SVA（assert / cover property） | 2 / 4 | - |
| Covergroups / coverpoints | 1 / 6 | |

## 4. 充分度判定與缺口

判定：**✅ Sufficient**（38 個 check，mutation score 96%）。

未被偵測的 mutant（測試缺口或等價 mutant）：

- `dut_spacewire_model.sv:96 0 -> 1 [if (outst == 0) e = 3'd4;]`

