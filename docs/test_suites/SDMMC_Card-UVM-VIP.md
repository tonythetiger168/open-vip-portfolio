# SD / eMMC card (1/4/8-bit, 512-byte blocks) 測試套件（SDMMC_Card-UVM-VIP）

> 由 `tools/gen_test_suite_docs.py` 依 VIP 內容、`func_report.csv` 與 `mutation_report.csv` 自動產生，請勿手動修改。

## 1. 概要

| 項目 | 內容 |
|---|---|
| 類別 | Storage |
| 類型 | UVM VIP |
| 功能測試 | 1 個檔案，60 個 check，全部通過 |
| Mutation | 29/29 個 mutant 被偵測（100%） |
| 判定 | **✅ Sufficient**（60 個 check，mutation score 100%） |

## 2. 可執行的功能測試

執行：`python3 tools/run_func_tests.py SDMMC_Card-UVM-VIP`（Icarus Verilog 或 Verilator 5.052）。

### `tb/smoke_func_tb.sv`

結果：**PASS**（iverilog，60 checks）

模型合約與範圍（摘自測試檔頭）：

```text
Functional smoke testbench (SDM DUT model)
```

| # | Check | 類型 |
|---|---|---|
| 1 | card off the bus in reset | check |
| 2 | ACMD41 as the first command after reset: illegal | check |
| 3 | SD: CMD13 in idle: illegal | check |
| 4 | CMD0: no response | check |
| 5 | CMD8 with VHS 2: no response | check |
| 6 | CMD8: R7 echo, NCR = 2 | check |
| 7 | ACMD41 without CMD55: illegal | check |
| 8 | CMD55: ILLEGAL_COMMAND, idle, APP_CMD | check |
| 9 | ACMD41: busy | check |
| 10 | ACMD41: busy (POLLS = 2) | check |
| 11 | ACMD41: ready, CCS | check |
| 12 | SD: CMD1 illegal | check |
| 13 | CMD2: SD CID | check |
| 14 | CMD3: R6, RCA B37A, ILLEGAL_COMMAND (CMD1), ident | check |
| 15 | bad CRC7: no response | check |
| 16 | CMD13: COM_CRC_ERROR, stby | check |
| 17 | CMD17 in stby: illegal | check |
| 18 | CMD7: R1, ILLEGAL_COMMAND, stby | check |
| 19 | CMD7: R1b busy 3 clocks, 2 clocks after the end bit | check |
| 20 | 1-bit CMD17: block 1, NAC = 2 | check |
| 21 | CMD24: R1, tran | check |
| 22 | 1-bit write: token 010 after 2 clocks, 4 clocks busy | check |
| 23 | 1-bit read-back | check |
| 24 | ACMD6: 4-bit, R1 with APP_CMD | check |
| 25 | CMD25: R1 | check |
| 26 | CMD25: 2 blocks, CMD12 in rcv state | check |
| 27 | CMD12: R1b busy | check |
| 28 | 4-bit CMD18: 3 blocks, NAC between, CMD12 in data state | check |
| 29 | back in tran | check |
| 30 | bad CRC16: token 101, no busy | check |
| 31 | and nothing written | check |
| 32 | CMD16: 64-byte blocks | check |
| 33 | 64-byte block 3 is bytes 192..255 | check |
| 34 | CMD16 513: illegal | check |
| 35 | CMD16 512, ILLEGAL_COMMAND reported | check |
| 36 | CMD12 stops a read in the middle of a block | check |
| 37 | CMD12 in tran: illegal | check |
| 38 | CMD7 to another RCA: deselect | check |
| 39 | stby, ILLEGAL_COMMAND (CMD12) | check |
| 40 | eMMC: CMD55 illegal | check |
| 41 | CMD1: busy, sector mode | check |
| 42 | CMD1: ready on the third poll | check |
| 43 | CMD2: eMMC CID | check |
| 44 | CMD3 with RCA 0: illegal | check |
| 45 | CMD3: R1, ident, ILLEGAL_COMMAND | check |
| 46 | CMD7: R1b | check |
| 47 | CMD8: R1 | check |
| 48 | EXT_CSD: BUS_WIDTH 0, rev 8, SEC_COUNT 8 | check |
| 49 | CMD6 SWITCH: 8 bits | check |
| 50 | 8-bit EXT_CSD read: BUS_WIDTH 2 | check |
| 51 | 8-bit read of SD's block 1 | check |
| 52 | 8-bit CMD25 / CMD18 with CMD12 | check |
| 53 | BUS_WIDTH 3: illegal | check |
| 54 | SWITCH of another byte: illegal | check |
| 55 | 4-bit 128-byte write | check |
| 56 | and read-back | check |
| 57 | the 128-byte block 2 sits at bytes 256..383 | check |
| 58 | CMD13: tran, flags cleared by the R1s since | check |
| 59 | CMD0 from tran: idle | check |
| 60 | no bus contention, only bus-width line sets | check |

## 3. UVM 測試平台內容

UVM agent test（`sdm_func_test`：directed + constrained-random 流量，scoreboard 以 DUT 模型的參考模型逐筆比對，並比對 driver 與 monitor 的 transaction）在 Verilator 上以 `python3 tools/run_uvm_tests.py SDMMC_Card-UVM-VIP` 執行；agent 由 `tools/gen_uvm_agents.py` 依 `tools/uvm_agents/` 的協定 spec 產生。

| 項目 | 數量 | 名稱 |
|---|---|---|
| UVM tests | 2 | `sdm_base_test`, `sdm_func_test` |
| Sequences | 3 | `sdm_base_sequence`, `sdm_directed_sequence`, `sdm_transaction` |
| SVA（assert / cover property） | 5 / 1 | - |
| Covergroups / coverpoints | 1 / 3 | |

## 4. 充分度判定與缺口

判定：**✅ Sufficient**（60 個 check，mutation score 100%）。

無已知缺口。

