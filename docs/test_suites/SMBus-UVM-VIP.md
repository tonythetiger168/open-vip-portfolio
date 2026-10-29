# SMBus/PMBus 測試套件（SMBus-UVM-VIP）

> 由 `tools/gen_test_suite_docs.py` 依 VIP 內容、`func_report.csv` 與 `mutation_report.csv` 自動產生，請勿手動修改。

## 1. 概要

| 項目 | 內容 |
|---|---|
| 類別 | Power |
| 類型 | UVM VIP |
| 功能測試 | 1 個檔案，40 個 check，全部通過 |
| Mutation | 28/28 個 mutant 被偵測（100%） |
| 判定 | **✅ Sufficient**（40 個 check，mutation score 100%） |

## 2. 可執行的功能測試

執行：`python3 tools/run_func_tests.py SMBus-UVM-VIP`（Icarus Verilog 或 Verilator 5.052）。

### `tb/smoke_func_tb.sv`

結果：**PASS**（iverilog，40 checks）

模型合約與範圍（摘自測試檔頭）：

```text
Functional smoke testbench (SMBus/PMBus DUT model)
```

| # | Check | 類型 |
|---|---|---|
| 1 | device releases SDA for the master NACK | check |
| 2 | bus released in reset | check |
| 3 | PMBUS_REVISION = 0x33 with a good PEC | check |
| 4 | OPERATION resets to 0x80 | check |
| 5 | address ACK | check |
| 6 | VOUT_COMMAND ACK | check |
| 7 | good PEC ACKed | check |
| 8 | READ_VOUT returns the commanded value | check |
| 9 | bad PEC NACKed | check |
| 10 | STATUS_CML[5] PEC failed | check |
| 11 | STATUS_BYTE CML bit | check |
| 12 | discarded write left VOUT_COMMAND unchanged | check |
| 13 | unsupported command NACKed | check |
| 14 | STATUS_CML[7] invalid command | check |
| 15 | other address NACKed | check |
| 16 | CLEAR_FAULTS clears STATUS_CML | check |
| 17 | one stretch in a write (after the address) | check |
| 18 | two stretches in a read (after each address) | check |
| 19 | no stretch after a NACKed address | check |
| 20 | PEC after one data byte ACKed | check |
| 21 | extra byte after the PEC NACKed | check |
| 22 | STATUS_CML[6] invalid data | check |
| 23 | write with extra bytes discarded | check |
| 24 | read of a send-byte command NACKed | check |
| 25 | STATUS_CML[7] for the read of a write-only command | check |
| 26 | repeated start to another address NACKed | check |
| 27 | repeated start with the write bit NACKed | check |
| 28 | no fault from a foreign or write repeated start | check |

## 3. UVM 測試平台內容

UVM agent test（`smbus_func_test`：directed + constrained-random 流量，scoreboard 以 DUT 模型的參考模型逐筆比對，並比對 driver 與 monitor 的 transaction）在 Verilator 上以 `python3 tools/run_uvm_tests.py SMBus-UVM-VIP` 執行；agent 由 `tools/gen_uvm_agents.py` 依 `tools/uvm_agents/` 的協定 spec 產生。

| 項目 | 數量 | 名稱 |
|---|---|---|
| UVM tests | 2 | `smbus_base_test`, `smbus_func_test` |
| Sequences | 3 | `smbus_base_sequence`, `smbus_directed_sequence`, `smbus_transaction` |
| SVA（assert / cover property） | 3 / 3 | - |
| Covergroups / coverpoints | 1 / 4 | |

## 4. 充分度判定與缺口

判定：**✅ Sufficient**（40 個 check，mutation score 100%）。

無已知缺口。

