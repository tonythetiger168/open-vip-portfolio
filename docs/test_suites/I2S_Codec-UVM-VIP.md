# I2S audio codec (clock master) 測試套件（I2S_Codec-UVM-VIP）

> 由 `tools/gen_test_suite_docs.py` 依 VIP 內容、`func_report.csv` 與 `mutation_report.csv` 自動產生，請勿手動修改。

## 1. 概要

| 項目 | 內容 |
|---|---|
| 類別 | Audio |
| 類型 | UVM VIP |
| 功能測試 | 1 個檔案，12 個 check，全部通過 |
| Mutation | 16/16 個 mutant 被偵測（100%） |
| 判定 | **✅ Sufficient**（12 個 check，mutation score 100%） |

## 2. 可執行的功能測試

執行：`python3 tools/run_func_tests.py I2S_Codec-UVM-VIP`（Icarus Verilog 或 Verilator 5.054）。

### `tb/smoke_func_tb.sv`

結果：**PASS**（iverilog，12 checks）

模型合約與範圍（摘自測試檔頭）：

```text
Functional smoke testbench (I2SC DUT model)
```

| # | Check | 類型 |
|---|---|---|
| 1 | sdout low in reset | check |
| 2 | first frame: transmit registers still 0 | check |
| 3 | lrck low from reset: the first left slot is not taken, the first right one is sent back | check |
| 4 | frame 3 sends frame 2 back | check |
| 5 | frame 3's words come back in the next burst | check |
| 6 | 24-bit slots | check |
| 7 | padding after the LSB is 0 | check |
| 8 | 32-bit slots at a slower bclk | check |
| 9 | 16 padding bits | check |
| 10 | left slot cut to 10 bits: word lost, the older left word is sent again | check |
| 11 | right slot cut to 12 bits: the older right word again | check |
| 12 | odd bclk half-period | check |

## 3. UVM 測試平台內容

UVM agent test（`i2sc_func_test`：directed + constrained-random 流量，scoreboard 以 DUT 模型的參考模型逐筆比對，並比對 driver 與 monitor 的 transaction）在 Verilator 上以 `python3 tools/run_uvm_tests.py I2S_Codec-UVM-VIP` 執行；agent 由 `tools/gen_uvm_agents.py` 依 `tools/uvm_agents/` 的協定 spec 產生。

| 項目 | 數量 | 名稱 |
|---|---|---|
| UVM tests | 2 | `i2sc_base_test`, `i2sc_func_test` |
| Sequences | 3 | `i2sc_base_sequence`, `i2sc_directed_sequence`, `i2sc_transaction` |
| SVA（assert / cover property） | 4 / 1 | - |
| Covergroups / coverpoints | 1 / 3 | |

## 4. 充分度判定與缺口

判定：**✅ Sufficient**（12 個 check，mutation score 100%）。

無已知缺口。

