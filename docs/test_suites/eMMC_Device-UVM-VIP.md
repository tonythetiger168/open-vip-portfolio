# eMMC device (1-bit, RST_n) 測試套件（eMMC_Device-UVM-VIP）

> 由 `tools/gen_test_suite_docs.py` 依 VIP 內容、`func_report.csv` 與 `mutation_report.csv` 自動產生，請勿手動修改。

## 1. 概要

| 項目 | 內容 |
|---|---|
| 類別 | Storage |
| 類型 | UVM VIP |
| 功能測試 | 1 個檔案，36 個 check，全部通過 |
| Mutation | 27/27 個 mutant 被偵測（100%） |
| 判定 | **✅ Sufficient**（36 個 check，mutation score 100%） |

## 2. 可執行的功能測試

執行：`python3 tools/run_func_tests.py eMMC_Device-UVM-VIP`（Icarus Verilog 或 Verilator 5.052）。

### `tb/smoke_func_tb.sv`

結果：**PASS**（iverilog，36 checks）

模型合約與範圍（摘自測試檔頭）：

```text
Functional smoke testbench (EMD DUT model)
```

| # | Check | 類型 |
|---|---|---|
| 1 | device off the bus in reset | check |
| 2 | CMD13 in idle: illegal, no response | check |
| 3 | CMD0: no response | check |
| 4 | CMD1: R3 after NCR = 2, busy, sector mode | check |
| 5 | CMD2 in idle: illegal | check |
| 6 | CMD1: ready | check |
| 7 | CMD1 in ready: illegal | check |
| 8 | CMD2: R2 with the CID and its CRC7 | check |
| 9 | CMD3 with RCA 0: illegal | check |
| 10 | CMD3: R1, ILLEGAL_COMMAND reported, ident | check |
| 11 | CMD3 in stby: illegal | check |
| 12 | bad CRC7: no response | check |
| 13 | CMD13: COM_CRC_ERROR and ILLEGAL_COMMAND, stby | check |
| 14 | CMD13 to another RCA: no response | check |
| 15 | CMD7: R1 from stby | check |
| 16 | CMD7: R1b busy, 3 clocks from 2 clocks after the end bit | check |
| 17 | block 0 after reset | check |
| 18 | CMD24: R1, tran state | check |
| 19 | block accepted: token 010 after 2 clocks, 4 clocks busy | check |
| 20 | CMD17 reads the block back, NAC = 2, CRC16 good | check |
| 21 | an untouched block | check |
| 22 | bad CRC16: token 101, no busy | check |
| 23 | and nothing written | check |
| 24 | CMD8: illegal | check |
| 25 | CMD13: ILLEGAL_COMMAND, tran | check |
| 26 | CMD7 again in tran | check |
| 27 | RST_n: off the bus | check |
| 28 | after RST_n: idle, CMD13 illegal | check |
| 29 | after RST_n: busy again | check |
| 30 | flags cleared by RST_n, new ILLEGAL_COMMAND | check |
| 31 | the block survives RST_n | check |
| 32 | CMD7 to another RCA: deselected, no response | check |
| 33 | CMD13: stby | check |
| 34 | CMD17 in stby: illegal | check |
| 35 | CMD0 resets: CMD2 illegal in idle | check |
| 36 | no bus contention | check |

## 3. UVM 測試平台內容

UVM agent test（`emd_func_test`：directed + constrained-random 流量，scoreboard 以 DUT 模型的參考模型逐筆比對，並比對 driver 與 monitor 的 transaction）在 Verilator 上以 `python3 tools/run_uvm_tests.py eMMC_Device-UVM-VIP` 執行；agent 由 `tools/gen_uvm_agents.py` 依 `tools/uvm_agents/` 的協定 spec 產生。

| 項目 | 數量 | 名稱 |
|---|---|---|
| UVM tests | 2 | `emd_base_test`, `emd_func_test` |
| Sequences | 3 | `emd_base_sequence`, `emd_directed_sequence`, `emd_transaction` |
| SVA（assert / cover property） | 5 / 1 | - |
| Covergroups / coverpoints | 1 / 3 | |

## 4. 充分度判定與缺口

判定：**✅ Sufficient**（36 個 check，mutation score 100%）。

無已知缺口。

