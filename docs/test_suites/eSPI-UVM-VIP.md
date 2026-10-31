# eSPI (Enhanced SPI) 測試套件（eSPI-UVM-VIP）

> 由 `tools/gen_test_suite_docs.py` 依 VIP 內容、`func_report.csv` 與 `mutation_report.csv` 自動產生，請勿手動修改。

## 1. 概要

| 項目 | 內容 |
|---|---|
| 類別 | Peripherals |
| 類型 | UVM VIP |
| 功能測試 | 1 個檔案，54 個 check，全部通過 |
| Mutation | 26/28 個 mutant 被偵測（93%） |
| 判定 | **✅ Sufficient**（54 個 check，mutation score 93%） |

## 2. 可執行的功能測試

執行：`python3 tools/run_func_tests.py eSPI-UVM-VIP`（Icarus Verilog 或 Verilator 5.052）。

### `tb/smoke_func_tb.sv`

結果：**PASS**（iverilog，54 checks）

模型合約與範圍（摘自測試檔頭）：

```text
Functional smoke testbench (eSPI DUT model)
```

| # | Check | 類型 |
|---|---|---|
| 1 | MISO released during reset | check |
| 2 | device ID 0x00000001 (%h) | check |
| 3 | general capabilities 0x0000000F after reset | check |
| 4 | peripheral channel enabled and ready after reset | check |
| 5 | unimplemented register reads 0 | check |
| 6 | only bits 31:16 of 0x08 written (%h) | check |
| 7 | and no write | check |
| 8 | device ID is read-only | check |
| 9 | unimplemented register ignores writes | check |
| 10 | channel disabled, ready bit read-only | check |
| 11 | channel enabled again | check |
| 12 | I/O registers 0 after reset (and the disabled write did nothing) | check |
| 13 | I/O read back, LSB first (%h) | check |
| 14 | 1-byte read at an offset | check |
| 15 | 2-byte read | check |
| 16 | 2-byte write and read at the window end | check |
| 17 | 1-byte write leaves the neighbours | check |
| 18 | rejected writes changed nothing | check |
| 19 | memory 0 after reset | check |
| 20 | memory read back | check |
| 21 | 1-byte memory read at an offset | check |
| 22 | window end data | check |
| 23 | MISO never driven for those | check |
| 24 | the write with the CRC error did not happen | check |
| 25 | MISO released whenever CS# is high | check |
| 26 | MISO changes only while SCLK is low (%0d) | check |

## 3. UVM 測試平台內容

UVM agent test（`espi_func_test`：directed + constrained-random 流量，scoreboard 以 DUT 模型的參考模型逐筆比對，並比對 driver 與 monitor 的 transaction）在 Verilator 上以 `python3 tools/run_uvm_tests.py eSPI-UVM-VIP` 執行；agent 由 `tools/gen_uvm_agents.py` 依 `tools/uvm_agents/` 的協定 spec 產生。

| 項目 | 數量 | 名稱 |
|---|---|---|
| UVM tests | 2 | `espi_base_test`, `espi_func_test` |
| Sequences | 3 | `espi_base_sequence`, `espi_directed_sequence`, `espi_transaction` |
| SVA（assert / cover property） | 4 / 2 | - |
| Covergroups / coverpoints | 1 / 4 | |

## 4. 充分度判定與缺口

判定：**✅ Sufficient**（54 個 check，mutation score 93%）。

未被偵測的 mutant（測試缺口或等價 mutant）：

- `dut_espi_model.sv:63 10 -> 11 [for (int i = 0; i < 10; i++) cb[i] <= '0;]`
- `dut_espi_model.sv:139 1'b1 inverted [miso <= rsp[63]; miso_oe <= 1'b1; rsp <= rsp << 1; rbits <= ]`

