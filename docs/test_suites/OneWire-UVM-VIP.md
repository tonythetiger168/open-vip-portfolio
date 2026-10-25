# 1-Wire 測試套件（OneWire-UVM-VIP）

> 由 `tools/gen_test_suite_docs.py` 依 VIP 內容、`func_report.csv` 與 `mutation_report.csv` 自動產生，請勿手動修改。

## 1. 概要

| 項目 | 內容 |
|---|---|
| 類別 | Peripherals |
| 類型 | UVM VIP |
| 功能測試 | 1 個檔案，25 個 check，全部通過 |
| Mutation | 13/16 個 mutant 被偵測（81%） |
| 判定 | **✅ Sufficient**（25 個 check，mutation score 81%） |

## 2. 可執行的功能測試

執行：`python3 tools/run_func_tests.py OneWire-UVM-VIP`（Icarus Verilog 或 Verilator 5.052）。

### `tb/smoke_func_tb.sv`

結果：**PASS**（iverilog，25 checks）

| # | Check | 類型 |
|---|---|---|
| 1 | presence reset low | check |
| 2 | dq pulled high (tri1) when idle | check |
| 3 | no presence without reset pulse | check |
| 4 | presence pulse after reset pulse | check |
| 5 | dq driven low during presence | check |
| 6 | presence pulse terminated (bounded) | check |
| 7 | presence pulse bounded in time | check |
| 8 | back to idle | check |
| 9 | dq released high after presence | check |

## 3. UVM 測試平台內容

UVM agent test（`onewire_func_test`：directed + constrained-random 流量，scoreboard 以 DUT 模型的參考模型逐筆比對，並比對 driver 與 monitor 的 transaction）在 Verilator 上以 `python3 tools/run_uvm_tests.py OneWire-UVM-VIP` 執行；agent 由 `tools/gen_uvm_agents.py` 依 `tools/uvm_agents/` 的協定 spec 產生。

| 項目 | 數量 | 名稱 |
|---|---|---|
| UVM tests | 2 | `onewire_base_test`, `onewire_func_test` |
| Sequences | 3 | `onewire_base_sequence`, `onewire_directed_sequence`, `onewire_transaction` |
| SVA（assert / cover property） | 3 / 2 | - |
| Covergroups / coverpoints | 1 / 2 | |

## 4. 充分度判定與缺口

判定：**✅ Sufficient**（25 個 check，mutation score 81%）。

未被偵測的 mutant（測試缺口或等價 mutant）：

- `dut_onewire_model.sv:26 == flipped [else if (dq == 1'b1)]`
- `dut_onewire_model.sv:26 1'b1 inverted [else if (dq == 1'b1)]`
- `dut_onewire_model.sv:29 >= -> > in condition [if (low_cnt >= 4'd8) begin]`

