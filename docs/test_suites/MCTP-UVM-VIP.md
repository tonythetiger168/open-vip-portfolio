# MCTP over SMBus (DMTF DSP0237) 測試套件（MCTP-UVM-VIP）

> 由 `tools/gen_test_suite_docs.py` 依 VIP 內容、`func_report.csv` 與 `mutation_report.csv` 自動產生，請勿手動修改。

## 1. 概要

| 項目 | 內容 |
|---|---|
| 類別 | Power |
| 類型 | UVM VIP |
| 功能測試 | 1 個檔案，23 個 check，全部通過 |
| Mutation | 44/44 個 mutant 被偵測（100%） |
| 判定 | **✅ Sufficient**（23 個 check，mutation score 100%） |

## 2. 可執行的功能測試

執行：`python3 tools/run_func_tests.py MCTP-UVM-VIP`（Icarus Verilog 或 Verilator 5.052）。

### `tb/smoke_func_tb.sv`

結果：**PASS**（iverilog，23 checks）

模型合約與範圍（摘自測試檔頭）：

```text
Functional smoke testbench (MCTP over SMBus DUT model)
```

| # | Check | 類型 |
|---|---|---|
| 1 | CRC-8/SMBUS check value of 123456789 = 0xF4 (%h) | check |
| 2 | bus released during reset | check |
| 3 | idle bus, no report | check |
| 4 | packet without SOM right after reset: dropped | check |
| 5 | every byte ACKed | check |
| 6 | single packet: type 7E, 9 bytes, CRC-32 0xCBF43926 (%0d %h %0d %h) | check |
| 7 | tag, TO and source EID reported | check |
| 8 | packet without SOM after an EOM: dropped | check |
| 9 | no report before EOM | check |
| 10 | three packets reassembled, sequence 3, 0, 1 | check |
| 11 | PEC error reported | check |
| 12 | the rest of the message dropped without a report | check |
| 13 | packet sequence 2 then 0: sequence error | check |
| 14 | destination EID 0x42: not for this endpoint | check |
| 15 | broadcast EID: control message accepted | check |
| 16 | null EID, type byte only: empty payload | check |
| 17 | command code 0x0E: format error | check |
| 18 | byte count one too large: format error | check |
| 19 | header version 2: format error | check |
| 20 | another slave address: NACK, no report | check |
| 21 | middle packet without a message: dropped | check |
| 22 | clean SPDM-type message afterwards | check |
| 23 | endpoint SDA stable while SCL high (%0d changes) | check |

## 3. UVM 測試平台內容

UVM agent test（`mctp_func_test`：directed + constrained-random 流量，scoreboard 以 DUT 模型的參考模型逐筆比對，並比對 driver 與 monitor 的 transaction）在 Verilator 上以 `python3 tools/run_uvm_tests.py MCTP-UVM-VIP` 執行；agent 由 `tools/gen_uvm_agents.py` 依 `tools/uvm_agents/` 的協定 spec 產生。

| 項目 | 數量 | 名稱 |
|---|---|---|
| UVM tests | 2 | `mctp_base_test`, `mctp_func_test` |
| Sequences | 3 | `mctp_base_sequence`, `mctp_directed_sequence`, `mctp_transaction` |
| SVA（assert / cover property） | 4 / 3 | - |
| Covergroups / coverpoints | 1 / 5 | |

## 4. 充分度判定與缺口

判定：**✅ Sufficient**（23 個 check，mutation score 100%）。

無已知缺口。

