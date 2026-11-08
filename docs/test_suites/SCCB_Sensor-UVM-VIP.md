# SCCB / I2C camera sensor control 測試套件（SCCB_Sensor-UVM-VIP）

> 由 `tools/gen_test_suite_docs.py` 依 VIP 內容、`func_report.csv` 與 `mutation_report.csv` 自動產生，請勿手動修改。

## 1. 概要

| 項目 | 內容 |
|---|---|
| 類別 | MIPI |
| 類型 | UVM VIP |
| 功能測試 | 1 個檔案，18 個 check，全部通過 |
| Mutation | 23/23 個 mutant 被偵測（100%） |
| 判定 | **✅ Sufficient**（18 個 check，mutation score 100%） |

## 2. 可執行的功能測試

執行：`python3 tools/run_func_tests.py SCCB_Sensor-UVM-VIP`（Icarus Verilog 或 Verilator 5.052）。

### `tb/smoke_func_tb.sv`

結果：**PASS**（iverilog，18 checks）

模型合約與範圍（摘自測試檔頭）：

```text
Functional smoke testbench (SCCB DUT model)
```

| # | Check | 類型 |
|---|---|---|
| 1 | SDA released in reset | check |
| 2 | chip ID 5A 31 | check |
| 3 | device address, register address and data bytes ACKed | check |
| 4 | auto-increment write, repeated-START read | check |
| 5 | SCCB two-phase read: pointer kept across STOP | check |
| 6 | pointer advanced past the read bytes | check |
| 7 | chip ID is read only | check |
| 8 | unmapped register: write ACKed and ignored, reads 0 | check |
| 9 | last registers, then 0 past 0x01FF | check |
| 10 | another device address: no ACK, bus ignored | check |
| 11 | and nothing written | check |
| 12 | read from another address: no ACK | check |
| 13 | an empty START / STOP changes nothing | check |
| 14 | one address byte leaves the pointer unchanged | check |
| 15 | write, repeated START, write | check |
| 16 | read with ACKs continues, NACK ends it | check |
| 17 | the target never holds SDA low at a START or STOP | check |
| 18 | the target leaves SDA alone on an idle bus | check |

## 3. UVM 測試平台內容

UVM agent test（`sccb_func_test`：directed + constrained-random 流量，scoreboard 以 DUT 模型的參考模型逐筆比對，並比對 driver 與 monitor 的 transaction）在 Verilator 上以 `python3 tools/run_uvm_tests.py SCCB_Sensor-UVM-VIP` 執行；agent 由 `tools/gen_uvm_agents.py` 依 `tools/uvm_agents/` 的協定 spec 產生。

| 項目 | 數量 | 名稱 |
|---|---|---|
| UVM tests | 2 | `sccb_base_test`, `sccb_func_test` |
| Sequences | 3 | `sccb_base_sequence`, `sccb_directed_sequence`, `sccb_transaction` |
| SVA（assert / cover property） | 3 / 1 | - |
| Covergroups / coverpoints | 1 / 3 | |

## 4. 充分度判定與缺口

判定：**✅ Sufficient**（18 個 check，mutation score 100%）。

無已知缺口。

