# HyperBus / HyperRAM 測試套件（HyperBus-UVM-VIP）

> 由 `tools/gen_test_suite_docs.py` 依 VIP 內容、`func_report.csv` 與 `mutation_report.csv` 自動產生，請勿手動修改。

## 1. 概要

| 項目 | 內容 |
|---|---|
| 類別 | Memory |
| 類型 | UVM VIP |
| 功能測試 | 1 個檔案，40 個 check，全部通過 |
| Mutation | 30/30 個 mutant 被偵測（100%） |
| 判定 | **✅ Sufficient**（40 個 check，mutation score 100%） |

## 2. 可執行的功能測試

執行：`python3 tools/run_func_tests.py HyperBus-UVM-VIP`（Icarus Verilog 或 Verilator 5.052）。

### `tb/smoke_func_tb.sv`

結果：**PASS**（iverilog，40 checks）

模型合約與範圍（摘自測試檔頭）：

```text
Functional smoke testbench (HyperBus DUT model)
```

| # | Check | 類型 |
|---|---|---|
| 1 | bus released during reset | check |
| 2 | CR0 reads 0x8F1F after reset (%h) | check |
| 3 | fixed latency: device drives RWDS high during the command-address | check |
| 4 | and drives it low through the latency of a read | check |
| 5 | read data after 2 x 6 clocks (24 CK edges, saw %0d) | check |
| 6 | ID0 | check |
| 7 | ID1 | check |
| 8 | unmapped register reads 0 | check |
| 9 | a register read repeats the register | check |
| 10 | memory 0 after reset | check |
| 11 | last word 0 after reset | check |
| 12 | device releases RWDS for the write mask | check |
| 13 | linear write and read of 4 words, bits 15:8 first | check |
| 14 | RWDS byte masks (%h %h) | check |
| 15 | masked burst left the next word | check |
| 16 | wrapped read wraps at the 16-word boundary | check |
| 17 | linear read runs on past it | check |
| 18 | wrapped write wraps too | check |
| 19 | and does not reach the next group | check |
| 20 | device releases RWDS for a register write | check |
| 21 | CR0 written (%h) | check |
| 22 | variable latency: RWDS low (%0d) and high (%0d) | check |
| 23 | variable latency: data after 3 or 6 clocks as RWDS says | check |
| 24 | 8-word wrap read | check |
| 25 | 8-word wrap: 0x0F then 0x08 | check |
| 26 | code 0: 5 clocks doubled | check |
| 27 | code 1: 6 clocks doubled | check |
| 28 | code 2: 7 clocks doubled | check |
| 29 | code F: 4 clocks doubled | check |
| 30 | code E: 3 clocks doubled | check |
| 31 | reserved code: 6 clocks | check |
| 32 | write data inside the latency ignored | check |
| 33 | 64-word wrap | check |
| 34 | 32-word wrap | check |
| 35 | ID0 is read-only | check |
| 36 | a write to ID0 does not reach CR0 (%h) | check |
| 37 | CR0 bits 15:8 and 2 are fixed (%h) | check |
| 38 | transaction after a cut command-address | check |
| 39 | DQ / RWDS never driven by both sides | check |
| 40 | device releases the bus while CS# is high | check |

## 3. UVM 測試平台內容

UVM agent test（`hyperbus_func_test`：directed + constrained-random 流量，scoreboard 以 DUT 模型的參考模型逐筆比對，並比對 driver 與 monitor 的 transaction）在 Verilator 上以 `python3 tools/run_uvm_tests.py HyperBus-UVM-VIP` 執行；agent 由 `tools/gen_uvm_agents.py` 依 `tools/uvm_agents/` 的協定 spec 產生。

| 項目 | 數量 | 名稱 |
|---|---|---|
| UVM tests | 2 | `hyperbus_base_test`, `hyperbus_func_test` |
| Sequences | 3 | `hyperbus_base_sequence`, `hyperbus_directed_sequence`, `hyperbus_transaction` |
| SVA（assert / cover property） | 7 / 2 | - |
| Covergroups / coverpoints | 1 / 7 | |

## 4. 充分度判定與缺口

判定：**✅ Sufficient**（40 個 check，mutation score 100%）。

無已知缺口。

