# MDIO 測試套件（MDIO-UVM-VIP）

> 由 `tools/gen_test_suite_docs.py` 依 VIP 內容、`func_report.csv` 與 `mutation_report.csv` 自動產生，請勿手動修改。

## 1. 概要

| 項目 | 內容 |
|---|---|
| 類別 | Networking |
| 類型 | UVM VIP |
| 功能測試 | 1 個檔案，153 個 check，全部通過 |
| Mutation | 25/25 個 mutant 被偵測（100%） |
| 判定 | **✅ Sufficient**（153 個 check，mutation score 100%） |

## 2. 可執行的功能測試

執行：`python3 tools/run_func_tests.py MDIO-UVM-VIP`（Icarus Verilog 或 Verilator 5.054）。

### `tb/smoke_func_tb.sv`

結果：**PASS**（iverilog，153 checks）

模型合約與範圍（摘自測試檔頭）：

```text
Functional smoke testbench (MDIO DUT model)
```

| # | Check | 類型 |
|---|---|---|
| 1 | first TA bit left high | check |
| 2 | released bus, BMCR 0x1140 in reset | check |
| 3 | the PHY does not drive MDIO in reset | check |
| 4 | BMCR reset value (%h) | check |
| 5 | BMSR = phy_status pins | check |
| 6 | PHY identifier 1 | check |
| 7 | PHY identifier 2 | check |
| 8 | identifier 1 is read-only | check |
| 9 | identifier 2 is read-only | check |
| 10 | BMSR is read-only | check |
| 11 | BMCR write shows on mdio_status | check |
| 12 | BMCR read back | check |
| 13 | register 4 read / write | check |
| 14 | register 31 read / write | check |
| 15 | register 5 still 0 | check |
| 16 | BMCR reset: back to 0x1140, bit 15 self-clears | check |
| 17 | BMCR reset clears register 4 | check |
| 18 | BMCR reset clears register 31 | check |
| 19 | BMCR reset clears register 12 | check |
| 20 | BMCR reset clears the MMD control register | check |
| 21 | BMSR unaffected | check |
| 22 | BMCR without bit 15 is a plain write | check |
| 23 | MMD 1 register 10 | check |
| 24 | MMD 3 register 10: own storage | check |
| 25 | MMD 7 keeps its own address register | check |
| 26 | a write does not move the address | check |
| 27 | post-read-increment reads at the address | check |
| 28 | then the next register | check |
| 29 | address now 12 | check |
| 30 | MMD device identifier 1 | check |
| 31 | MMD 3 device identifier 2 | check |
| 32 | MMD 7 device identifier 2 | check |
| 33 | devices in package: MMD 1, 3, 7 | check |
| 34 | devices in package is read-only | check |
| 35 | identifier is read-only | check |
| 36 | register 63 is the last one | check |
| 37 | register 64 reads 0 | check |
| 38 | register 64 write did not alias register 0 | check |
| 39 | address 0xFFFF wraps cleanly | check |
| 40 | post-increment past 63 | check |
| 41 | MMD 2 is not implemented: no response | check |
| 42 | other port address: no response | check |
| 43 | another port's address frame is ignored | check |
| 44 | MMD 1 register 10 unchanged | check |
| 45 | register 14 reads the MMD address | check |
| 46 | function 01: data, no increment | check |
| 47 | function 10: two writes moved the address to 22 | check |
| 48 | function 10: read at 20 | check |
| 49 | function 10: read moved to 21 | check |
| 50 | function 11: read at 22 | check |
| 51 | function 11: reads do not increment (still 22) | check |
| 52 | function 11: a write increments | check |
| 53 | Clause 45 sees the indirect writes | check |
| 54 | indirect write at 22 | check |
| 55 | indirect read of an MMD 7 read-only register | check |
| 56 | indirect read of the MMD 1 identifier 1 | check |
| 57 | indirect read of the MMD 1 identifier 2 | check |
| 58 | indirect access past register 63: reads 0, write ignored | check |
| 59 | the write at 64 did not alias register 0 | check |
| 60 | indirect access to an MMD that is not implemented reads 0 | check |
| 61 | and ignores writes | check |
| 62 | indirect write to a read-only register ignored | check |
| 63 | but the address still increments | check |
| 64 | PHY address 4: no response | check |
| 65 | PHY address 6: no response | check |
| 66 | Clause 22 OP 00 ignored | check |
| 67 | Clause 22 OP 11 ignored | check |
| 68 | write to another PHY ignored | check |
| 69 | 31-bit preamble: ignored | check |
| 70 | 31-bit preamble write ignored | check |
| 71 | 45-bit preamble accepted | check |
| 72 | a preamble longer than 63 still counts | check |
| 73 | ST 11 is not a frame | check |
| 74 | ST 10 is not a frame | check |
| 75 | reset | check |
| 76 | reset clears MMD 1 | check |
| 77 | reset clears the MMD 3 address and data | check |
| 78 | reset clears MMD 7 register 0 | check |
| 79 | reset clears register 4 | check |
| 80 | BMSR after reset | check |
| 81 | reset clears the MMD 7 address | check |

## 3. UVM 測試平台內容

UVM agent test（`mdio_func_test`：directed + constrained-random 流量，scoreboard 以 DUT 模型的參考模型逐筆比對，並比對 driver 與 monitor 的 transaction）在 Verilator 上以 `python3 tools/run_uvm_tests.py MDIO-UVM-VIP` 執行；agent 由 `tools/gen_uvm_agents.py` 依 `tools/uvm_agents/` 的協定 spec 產生。

| 項目 | 數量 | 名稱 |
|---|---|---|
| UVM tests | 2 | `mdio_base_test`, `mdio_func_test` |
| Sequences | 3 | `mdio_base_sequence`, `mdio_directed_sequence`, `mdio_transaction` |
| SVA（assert / cover property） | 3 / 2 | - |
| Covergroups / coverpoints | 1 / 9 | |

## 4. 充分度判定與缺口

判定：**✅ Sufficient**（153 個 check，mutation score 100%）。

無已知缺口。

