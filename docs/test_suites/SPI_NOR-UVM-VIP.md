# Quad-SPI NOR flash (XIP) 測試套件（SPI_NOR-UVM-VIP）

> 由 `tools/gen_test_suite_docs.py` 依 VIP 內容、`func_report.csv` 與 `mutation_report.csv` 自動產生，請勿手動修改。

## 1. 概要

| 項目 | 內容 |
|---|---|
| 類別 | Memory |
| 類型 | UVM VIP |
| 功能測試 | 1 個檔案，26 個 check，全部通過 |
| Mutation | 29/29 個 mutant 被偵測（100%） |
| 判定 | **✅ Sufficient**（26 個 check，mutation score 100%） |

## 2. 可執行的功能測試

執行：`python3 tools/run_func_tests.py SPI_NOR-UVM-VIP`（Icarus Verilog 或 Verilator 5.054）。

### `tb/smoke_func_tb.sv`

結果：**PASS**（iverilog，26 checks）

模型合約與範圍（摘自測試檔頭）：

```text
Functional smoke testbench (SNOR DUT model)
```

| # | Check | 類型 |
|---|---|---|
| 1 | flash IO released | check |
| 2 | JEDEC ID EF 40 18, then 00 | check |
| 3 | status after reset: WEL 0 | check |
| 4 | read 0x03 of the preloaded array | check |
| 5 | fast read 0x0B with 8 dummy clocks | check |
| 6 | quad read 0x6B: four lines, high nibble first | check |
| 7 | quad read wraps at 64 KB (address bits 23:16 ignored) | check |
| 8 | page program without WEL is ignored | check |
| 9 | WREN sets WEL | check |
| 10 | page program clears WEL | check |
| 11 | programmed bytes are ANDed into the array | check |
| 12 | and read the same in quad mode | check |
| 13 | WRDI clears WEL | check |
| 14 | sector erase without WEL is ignored | check |
| 15 | sector erase clears the whole 4 KB sector to FF, not the one before | check |
| 16 | and not the one after | check |
| 17 | erase clears WEL | check |
| 18 | program to the end of the page | check |
| 19 | then wraps to the page start | check |
| 20 | page program with no data bit keeps WEL | check |
| 21 | a partial data byte clears WEL | check |
| 22 | and programs nothing | check |
| 23 | unknown command: the flash stays off the bus | check |
| 24 | a transfer cut in the address leaves no state behind | check |
| 25 | WREN cut before 8 bits is ignored | check |
| 26 | no IO contention | check |

## 3. UVM 測試平台內容

UVM agent test（`snor_func_test`：directed + constrained-random 流量，scoreboard 以 DUT 模型的參考模型逐筆比對，並比對 driver 與 monitor 的 transaction）在 Verilator 上以 `python3 tools/run_uvm_tests.py SPI_NOR-UVM-VIP` 執行；agent 由 `tools/gen_uvm_agents.py` 依 `tools/uvm_agents/` 的協定 spec 產生。

| 項目 | 數量 | 名稱 |
|---|---|---|
| UVM tests | 2 | `snor_base_test`, `snor_func_test` |
| Sequences | 3 | `snor_base_sequence`, `snor_directed_sequence`, `snor_transaction` |
| SVA（assert / cover property） | 4 / 1 | - |
| Covergroups / coverpoints | 1 / 3 | |

## 4. 充分度判定與缺口

判定：**✅ Sufficient**（26 個 check，mutation score 100%）。

無已知缺口。

