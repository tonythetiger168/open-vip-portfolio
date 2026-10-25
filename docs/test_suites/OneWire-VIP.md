# 1-Wire 測試套件（OneWire-VIP）

> 由 `tools/gen_test_suite_docs.py` 依 VIP 內容、`func_report.csv` 與 `mutation_report.csv` 自動產生，請勿手動修改。

## 1. 概要

| 項目 | 內容 |
|---|---|
| 類別 | Peripherals |
| 類型 | RTL IP |
| 功能測試 | 2 個檔案，20 個 check，12446178 次斷言評估，全部通過 |
| Mutation | 11/11 個 mutant 被偵測（100%） |
| 判定 | **✅ Sufficient**（20 個 check，mutation score 100%） |

## 2. 可執行的功能測試

執行：`python3 tools/run_func_tests.py OneWire-VIP`（Icarus Verilog 或 Verilator 5.052）。

### `tb/_1_Wire_tb.sv`

結果：**PASS**（verilator，12446178 次斷言評估）

### `tb/func_onewire_tb.sv`

結果：**PASS**（verilator，20 checks）

| # | Check | 類型 |
|---|---|---|
| 1 | idle bus after reset release: slave never busy, line released | check |
| 2 | reset clears rx_byte / rx_valid | check |
| 3 | reset pulse recognised from 480 us + 3 clocks (%0d) | check |
| 4 | presence pulse after a 600 us reset | check |
| 5 | presence pulse lasts 120 us + 2 clocks (%0d) | check |
| 6 | slave busy waiting for a command after presence | check |
| 7 | command byte received LSB-first (%h) | check |
| 8 | rx_valid pulses once per byte for one clock (%0d) | check |
| 9 | response byte sent LSB-first (%h) | check |
| 10 | next command byte accepted right after the read phase | check |
| 11 | read-slot 0 bit held 40 us from the falling edge (%0d clocks after release) | check |
| 12 | write slot sampled at 15 us (%h) | check |
| 13 | slave sending read data | check |
| 14 | reset pulse recognised while sending a read byte | check |
| 15 | command after the mid-read reset starts at bit 0 | check |
| 16 | reset pulse recognised in the middle of a command byte | check |
| 17 | bit counter restarts after the mid-byte reset | check |
| 18 | 100 us low pulse is ignored | check |
| 19 | 6 random command/response exchanges (%0d bad) | check |
| 20 | irq mirrors rx_valid | check |

## 3. UVM 測試平台內容

RTL IP：以 `tb/` 的 self-checking testbench 驗證，無 UVM 測試。

## 4. 充分度判定與缺口

判定：**✅ Sufficient**（20 個 check，mutation score 100%）。

無已知缺口。

