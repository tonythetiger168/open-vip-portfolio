# IR remote control (NEC / RC5) 測試套件（IR_Remote-UVM-VIP）

> 由 `tools/gen_test_suite_docs.py` 依 VIP 內容、`func_report.csv` 與 `mutation_report.csv` 自動產生，請勿手動修改。

## 1. 概要

| 項目 | 內容 |
|---|---|
| 類別 | Peripherals |
| 類型 | UVM VIP |
| 功能測試 | 1 個檔案，40 個 check，全部通過 |
| Mutation | 26/26 個 mutant 被偵測（100%） |
| 判定 | **✅ Sufficient**（40 個 check，mutation score 100%） |

## 2. 可執行的功能測試

執行：`python3 tools/run_func_tests.py IR_Remote-UVM-VIP`（Icarus Verilog 或 Verilator 5.054）。

### `tb/smoke_func_tb.sv`

結果：**PASS**（iverilog，40 checks）

模型合約與範圍（摘自測試檔頭）：

```text
Functional smoke testbench (IR DUT model)
```

| # | Check | 類型 |
|---|---|---|
| 1 | no report in reset | check |
| 2 | repeat before any frame: last address/command 0 | check |
| 3 | NEC 0x04 / 0x08 | check |
| 4 | NEC 0x00 / 0xFF | check |
| 5 | repeat: last frame's address and command | check |
| 6 | extended NEC address 0x1234 | check |
| 7 | ~cmd wrong: check error | check |
| 8 | repeat ignores the failed frame | check |
| 9 | 5T space in bit 7: timing error | check |
| 10 | no stop mark: timing error | check |
| 11 | 6T leader: unknown frame | check |
| 12 | 12T leader space | check |
| 13 | NEC after the faults | check |
| 14 | RC5 TV standby, toggle 0 | check |
| 15 | RC5 toggle 1 | check |
| 16 | RC5 all ones | check |
| 17 | RC5 alternating bits | check |
| 18 | RC5 zeros (ends on a space) | check |
| 19 | RC5X: S2 = 0 sets cmd bit 6 | check |
| 20 | RC5 half bit 3H: error | check |
| 21 | NEC with jitter inside the windows | check |
| 22 | repeat after the jittered frame | check |
| 23 | marks while re-arming (under 20T of space) are ignored | check |
| 24 | 3-clock glitch once armed: error | check |
| 25 | leader space 10T accepted | check |
| 26 | leader space 10T + 1 rejected | check |
| 27 | bit space 4T is a 1 | check |
| 28 | bit space 4T + 1 rejected | check |
| 29 | bit mark T/2 accepted | check |
| 30 | bit mark T/2 - 1 rejected | check |
| 31 | bit mark 3T/2 accepted | check |
| 32 | bit mark 3T/2 + 1 rejected | check |
| 33 | first mark of 6 clocks: neither NEC nor RC5 | check |
| 34 | a frame 20T after the last one is decoded | check |
| 35 | a frame 20T - 1 after the last one is ignored | check |
| 36 | RC5 mark half of 3H/2 accepted | check |
| 37 | RC5 space half of 3H/2 accepted | check |
| 38 | RC5 mark half of 6 rejected | check |
| 39 | RC5 space half of 5 rejected at its end | check |
| 40 | RC5 mark of 40 rejected at its end | check |

## 3. UVM 測試平台內容

UVM agent test（`ir_func_test`：directed + constrained-random 流量，scoreboard 以 DUT 模型的參考模型逐筆比對，並比對 driver 與 monitor 的 transaction）在 Verilator 上以 `python3 tools/run_uvm_tests.py IR_Remote-UVM-VIP` 執行；agent 由 `tools/gen_uvm_agents.py` 依 `tools/uvm_agents/` 的協定 spec 產生。

| 項目 | 數量 | 名稱 |
|---|---|---|
| UVM tests | 2 | `ir_base_test`, `ir_func_test` |
| Sequences | 3 | `ir_base_sequence`, `ir_directed_sequence`, `ir_transaction` |
| SVA（assert / cover property） | 4 / 3 | - |
| Covergroups / coverpoints | 1 / 5 | |

## 4. 充分度判定與缺口

判定：**✅ Sufficient**（40 個 check，mutation score 100%）。

無已知缺口。

