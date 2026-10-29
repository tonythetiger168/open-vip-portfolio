# xSPI (JESD251) 測試套件（xSPI-UVM-VIP）

> 由 `tools/gen_test_suite_docs.py` 依 VIP 內容、`func_report.csv` 與 `mutation_report.csv` 自動產生，請勿手動修改。

## 1. 概要

| 項目 | 內容 |
|---|---|
| 類別 | Serial |
| 類型 | UVM VIP |
| 功能測試 | 1 個檔案，18 個 check，全部通過 |
| Mutation | 24/24 個 mutant 被偵測（100%） |
| 判定 | **✅ Sufficient**（18 個 check，mutation score 100%） |

## 2. 可執行的功能測試

執行：`python3 tools/run_func_tests.py xSPI-UVM-VIP`（Icarus Verilog 或 Verilator 5.052）。

### `tb/smoke_func_tb.sv`

結果：**PASS**（iverilog，18 checks）

模型合約與範圍（摘自測試檔頭）：

```text
Functional smoke testbench (xSPI DUT model)
```

| # | Check | 類型 |
|---|---|---|
| 1 | WIP clears | check |
| 2 | DQ released in reset | check |
| 3 | RDID | check |
| 4 | RDID repeats every 3 bytes | check |
| 5 | erased array reads 0xFF | check |
| 6 | program without WEL ignored | check |
| 7 | WREN sets WEL | check |
| 8 | WIP and WEL while programming | check |
| 9 | WEL cleared after program | check |
| 10 | programmed bytes read back | check |
| 11 | read from another address | check |
| 12 | program while WIP ignored | check |
| 13 | WRDI clears WEL | check |
| 14 | program after WRDI ignored | check |
| 15 | sector erase | check |
| 16 | wrong command extension ignored | check |

## 3. UVM 測試平台內容

UVM agent test（`xspi_func_test`：directed + constrained-random 流量，scoreboard 以 DUT 模型的參考模型逐筆比對，並比對 driver 與 monitor 的 transaction）在 Verilator 上以 `python3 tools/run_uvm_tests.py xSPI-UVM-VIP` 執行；agent 由 `tools/gen_uvm_agents.py` 依 `tools/uvm_agents/` 的協定 spec 產生。

| 項目 | 數量 | 名稱 |
|---|---|---|
| UVM tests | 2 | `xspi_base_test`, `xspi_func_test` |
| Sequences | 3 | `xspi_base_sequence`, `xspi_directed_sequence`, `xspi_transaction` |
| SVA（assert / cover property） | 5 / 2 | - |
| Covergroups / coverpoints | 1 / 4 | |

## 4. 充分度判定與缺口

判定：**✅ Sufficient**（18 個 check，mutation score 100%）。

無已知缺口。

