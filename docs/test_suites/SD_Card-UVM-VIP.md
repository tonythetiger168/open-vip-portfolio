# SD memory card (4-bit) 測試套件（SD_Card-UVM-VIP）

> 由 `tools/gen_test_suite_docs.py` 依 VIP 內容、`func_report.csv` 與 `mutation_report.csv` 自動產生，請勿手動修改。

## 1. 概要

| 項目 | 內容 |
|---|---|
| 類別 | Storage |
| 類型 | UVM VIP |
| 功能測試 | 1 個檔案，32 個 check，全部通過 |
| Mutation | 28/28 個 mutant 被偵測（100%） |
| 判定 | **✅ Sufficient**（32 個 check，mutation score 100%） |

## 2. 可執行的功能測試

執行：`python3 tools/run_func_tests.py SD_Card-UVM-VIP`（Icarus Verilog 或 Verilator 5.052）。

### `tb/smoke_func_tb.sv`

結果：**PASS**（iverilog，32 checks）

模型合約與範圍（摘自測試檔頭）：

```text
Functional smoke testbench (SDC DUT model)
```

| # | Check | 類型 |
|---|---|---|
| 1 | card off the bus in reset | check |
| 2 | CMD0: no response | check |
| 3 | CMD8 with VHS 2: no response | check |
| 4 | CMD8: R7 echo after NCR = 2 | check |
| 5 | CMD41 without CMD55: illegal, no response | check |
| 6 | CMD55: ILLEGAL_COMMAND, idle, APP_CMD | check |
| 7 | ACMD41: R3, busy | check |
| 8 | flags cleared after a report | check |
| 9 | ACMD41: ready, CCS 1 | check |
| 10 | CMD3 in ready: illegal, no response | check |
| 11 | CMD2: R2 with the CID and its CRC7 | check |
| 12 | CMD3: R6 with the RCA, ILLEGAL_COMMAND, ident state | check |
| 13 | CMD55 in stby | check |
| 14 | ACMD41 in stby: illegal, no response | check |
| 15 | bad CRC7: no response | check |
| 16 | CMD13: COM_CRC_ERROR and ILLEGAL_COMMAND, stby, NCR = 2 | check |
| 17 | CMD7: selected | check |
| 18 | CMD24: R1 after NCR = 2, tran state, flags clear | check |
| 19 | block accepted: token 010 after 2 clocks, 4 clocks busy | check |
| 20 | CMD17 reads the block back, NAC = 2, CRC16s good | check |
| 21 | an untouched block | check |
| 22 | bad CRC16: token 101, no busy | check |
| 23 | and nothing written | check |
| 24 | CMD6: illegal | check |
| 25 | CMD7 to another RCA: deselected, no response | check |
| 26 | CMD17 in stby: illegal | check |
| 27 | CMD13: ILLEGAL_COMMAND, stby | check |
| 28 | CMD13 to another RCA: no response | check |
| 29 | after CMD0: busy again | check |
| 30 | no HCS: ready with CCS 0 | check |
| 31 | byte addressing: address 64 is block 2 | check |
| 32 | no bus contention | check |

## 3. UVM 測試平台內容

UVM agent test（`sdc_func_test`：directed + constrained-random 流量，scoreboard 以 DUT 模型的參考模型逐筆比對，並比對 driver 與 monitor 的 transaction）在 Verilator 上以 `python3 tools/run_uvm_tests.py SD_Card-UVM-VIP` 執行；agent 由 `tools/gen_uvm_agents.py` 依 `tools/uvm_agents/` 的協定 spec 產生。

| 項目 | 數量 | 名稱 |
|---|---|---|
| UVM tests | 2 | `sdc_base_test`, `sdc_func_test` |
| Sequences | 3 | `sdc_base_sequence`, `sdc_directed_sequence`, `sdc_transaction` |
| SVA（assert / cover property） | 4 / 1 | - |
| Covergroups / coverpoints | 1 / 3 | |

## 4. 充分度判定與缺口

判定：**✅ Sufficient**（32 個 check，mutation score 100%）。

無已知缺口。

