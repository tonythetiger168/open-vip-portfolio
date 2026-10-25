# DDR4 測試套件（DDR4-VIP）

> 由 `tools/gen_test_suite_docs.py` 依 VIP 內容、`func_report.csv` 與 `mutation_report.csv` 自動產生，請勿手動修改。

## 1. 概要

| 項目 | 內容 |
|---|---|
| 類別 | Memory |
| 類型 | RTL IP |
| 功能測試 | 2 個檔案，39 個 check，19736 次斷言評估，全部通過 |
| Mutation | 7/7 個 mutant 被偵測（100%） |
| 判定 | **✅ Sufficient**（39 個 check，mutation score 100%） |

## 2. 可執行的功能測試

執行：`python3 tools/run_func_tests.py DDR4-VIP`（Icarus Verilog 或 Verilator 5.052）。

### `tb/DDR4_tb.sv`

結果：**PASS**（verilator，19736 次斷言評估）

### `tb/func_ddr4_tb.sv`

結果：**PASS**（verilator，39 checks）

| # | Check | 類型 |
|---|---|---|
| 1 | reset: CKE low, command pins idle (NOP) | check |
| 2 | reset: differential clock, host ready, no done/trace, read data 0 | check |
| 3 | reset: DQ released | check |
| 4 | CKE follows reset release | check |
| 5 | ACT emits one gem5 activate trace with the host address | check |
| 6 | ACT encoding RAS_n=0 CAS_n=1 WE_n=1 | check |
| 7 | ACT drives the row address haddr[31:18] | check |
| 8 | ACT is a single-cycle command | check |
| 9 | host ready again exactly tRCD after ACT (k=%0d) | check |
| 10 | ACT does not pulse hdone | check |
| 11 | WR emits one write trace | check |
| 12 | write data driven on DQ in the WR cycle | check |
| 13 | DQ released after the WR cycle | check |
| 14 | WR encoding RAS_n=1 CAS_n=0 WE_n=0 | check |
| 15 | WR drives the column address haddr[7:0] | check |
| 16 | WR is a single-cycle command | check |
| 17 | WR busy for CL, no hdone | check |
| 18 | RD emits one read trace | check |
| 19 | RD encoding RAS_n=1 CAS_n=0 WE_n=1 | check |
| 20 | RD drives the column address | check |
| 21 | RD is a single-cycle command | check |
| 22 | single hdone exactly CL after RD | check |
| 23 | read data returned at the end of CL | check |
| 24 | host ready the clock after hdone | check |
| 25 | controller does not drive DQ on a read | check |
| 26 | column C3 unaffected by C2 write | check |
| 27 | column C2 holds its word | check |
| 28 | top column FF holds its word | check |
| 29 | column 0 holds its word | check |
| 30 | unwritten column reads 0 | check |
| 31 | idle host command is a no-op | check |
| 32 | PRE encoding RAS_n=0 CAS_n=1 WE_n=0 | check |
| 33 | PRE emits no trace and no hdone | check |
| 34 | PRE is a single-cycle command (pins return to NOP) | XFAIL（模型缺陷） |
| 35 | host held off for tRP after PRE | XFAIL（模型缺陷） |
| 36 | 40 random reads/writes match the reference (%0d bad) | check |
| 37 | reset returns pins to NOP, ready, data 0 | check |
| 38 | reset clears stored data | check |
| 39 | reset clears column 0 | check |

## 3. UVM 測試平台內容

RTL IP：以 `tb/` 的 self-checking testbench 驗證，無 UVM 測試。

## 4. 充分度判定與缺口

判定：**✅ Sufficient**（39 個 check，mutation score 100%）。

DUT 模型缺陷（XFAIL check，修好模型後會變成 XPASS 提醒移除標記）：

- PRE is a single-cycle command (pins return to NOP)
- host held off for tRP after PRE

