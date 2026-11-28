# Wishbone 測試套件（Wishbone-UVM-VIP）

> 由 `tools/gen_test_suite_docs.py` 依 VIP 內容、`func_report.csv` 與 `mutation_report.csv` 自動產生，請勿手動修改。

## 1. 概要

| 項目 | 內容 |
|---|---|
| 類別 | Interconnect |
| 類型 | UVM VIP |
| 功能測試 | 1 個檔案，139 個 check，全部通過 |
| Mutation | 28/28 個 mutant 被偵測（100%） |
| 判定 | **✅ Sufficient**（139 個 check，mutation score 100%） |

## 2. 可執行的功能測試

執行：`python3 tools/run_func_tests.py Wishbone-UVM-VIP`（Icarus Verilog 或 Verilator 5.054）。

### `tb/smoke_func_tb.sv`

結果：**PASS**（iverilog，139 checks）

模型合約與範圍（摘自測試檔頭）：

```text
Functional smoke testbench (Wishbone DUT model)
```

| # | Check | 類型 |
|---|---|---|
| 1 | %0d responses | check |
| 2 | quiet in reset | check |
| 3 | no STALL in reset | check |
| 4 | no STALL without CYC | check |
| 5 | write: ACK, DAT_O 0 | check |
| 6 | read back | check |
| 7 | SEL byte lanes (%h) | check |
| 8 | 0x3FC is memory | check |
| 9 | neighbour still 0 | check |
| 10 | 0x400: ERR | check |
| 11 | 0x7FC: ERR | check |
| 12 | 0x840 (past the device): ERR | check |
| 13 | 0x1000 (ADR above bit 11): ERR | check |
| 14 | upper ADR bits decoded | check |
| 15 | error-region accesses wrote nothing | check |
| 16 | busy device: first try RTY | check |
| 17 | second try RTY | check |
| 18 | another word counts its own tries | check |
| 19 | third try ACK | check |
| 20 | the count restarts after an ACK | check |
| 21 | device word written once accepted | check |
| 22 | RTY attempts wrote nothing | check |
| 23 | last device word, SEL lane 0 | check |
| 24 | device word does not alias memory | check |
| 25 | device word 8: first try RTY | check |
| 26 | reserved CTI to the device: ERR | check |
| 27 | second try RTY | check |
| 28 | third try ACK: the ERR did not count | check |
| 29 | 8 ACKs for the linear burst | check |
| 30 | 8 read beats in order | check |
| 31 | wrap-4 burst accepted | check |
| 32 | wrap-4 without the wrap: ERR | check |
| 33 | wrap-8 back to 0x100 | check |
| 34 | wrap-16 back to 0x100 | check |
| 35 | wrap-8 from 0x13C wraps to 0x120 | check |
| 36 | linear crosses 0x140 | check |
| 37 | linear does not wrap: ERR | check |
| 38 | constant burst: four lanes into one word | check |
| 39 | constant burst with a new address: ERR | check |
| 40 | ERR on the jump, the next request follows it | check |
| 41 | the ERR request wrote nothing | check |
| 42 | the request after it was written | check |
| 43 | after end-of-burst any address is fine | check |
| 44 | classic requests are not a burst | check |
| 45 | reserved CTI %0d: ERR | check |
| 46 | reserved-CTI writes landed nowhere | check |
| 47 | end-of-burst alone is a single | check |
| 48 | a new bus cycle starts outside any burst | check |
| 49 | no fifth request accepted before a response | check |
| 50 | six responses for six requests | check |
| 51 | no response after CYC drops | check |
| 52 | aborted writes were performed when accepted | check |
| 53 | the next cycle gets only its own responses | check |
| 54 | idle clocks inside a burst | check |
| 55 | STALL pattern: %0d stalls for %0d requests | check |
| 56 | device word 0: one try counted before the reset | check |
| 57 | reset clears the responses | check |
| 58 | memory cleared | check |
| 59 | retry count cleared | check |
| 60 | word 0 cleared | check |
| 61 | device word 0: count cleared, first try RTY | check |
| 62 | device word 0: second try RTY | check |
| 63 | device word 0 cleared | check |

## 3. UVM 測試平台內容

UVM agent test（`wishbone_func_test`：directed + constrained-random 流量，scoreboard 以 DUT 模型的參考模型逐筆比對，並比對 driver 與 monitor 的 transaction）在 Verilator 上以 `python3 tools/run_uvm_tests.py Wishbone-UVM-VIP` 執行；agent 由 `tools/gen_uvm_agents.py` 依 `tools/uvm_agents/` 的協定 spec 產生。

| 項目 | 數量 | 名稱 |
|---|---|---|
| UVM tests | 3 | `wishbone_base_test`, `wishbone_func_test`, `wishbone_ral_test` |
| Sequences | 3 | `wishbone_base_sequence`, `wishbone_directed_sequence`, `wishbone_transaction` |
| SVA（assert / cover property） | 6 / 4 | - |
| Covergroups / coverpoints | 1 / 8 | |

## 4. 充分度判定與缺口

判定：**✅ Sufficient**（139 個 check，mutation score 100%）。

無已知缺口。

