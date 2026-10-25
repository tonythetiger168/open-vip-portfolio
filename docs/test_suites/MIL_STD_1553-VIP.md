# MIL-STD-1553 測試套件（MIL_STD_1553-VIP）

> 由 `tools/gen_test_suite_docs.py` 依 VIP 內容、`func_report.csv` 與 `mutation_report.csv` 自動產生，請勿手動修改。

## 1. 概要

| 項目 | 內容 |
|---|---|
| 類別 | Aerospace |
| 類型 | UVM VIP |
| 功能測試 | 1 個檔案，19 個 check，全部通過 |
| Mutation | 12/15 個 mutant 被偵測（80%） |
| 判定 | **✅ Sufficient**（19 個 check，mutation score 80%） |

## 2. 可執行的功能測試

執行：`python3 tools/run_func_tests.py MIL_STD_1553-VIP`（Icarus Verilog 或 Verilator 5.052）。

### `tb/smoke_func_tb.sv`

結果：**PASS**（iverilog，19 checks）

| # | Check | 類型 |
|---|---|---|
| 1 | tx quiet out of reset | check |
| 2 | RT address is the configured 0x05 | check |
| 3 | no response to other RT | check |
| 4 | still quiet for other RT | check |
| 5 | status word transmitted | check |
| 6 | status word carries RT address | check |
| 7 | status word sync asserted | check |
| 8 | status word completes | check |

## 3. UVM 測試平台內容

UVM agent test（`mil_std_1553_func_test`：directed + constrained-random 流量，scoreboard 以 DUT 模型的參考模型逐筆比對，並比對 driver 與 monitor 的 transaction）在 Verilator 上以 `python3 tools/run_uvm_tests.py MIL_STD_1553-VIP` 執行；agent 由 `tools/gen_uvm_agents.py` 依 `tools/uvm_agents/` 的協定 spec 產生。

| 項目 | 數量 | 名稱 |
|---|---|---|
| UVM tests | 2 | `mil_std_1553_base_test`, `mil_std_1553_func_test` |
| Sequences | 3 | `mil_std_1553_base_sequence`, `mil_std_1553_directed_sequence`, `mil_std_1553_transaction` |
| SVA（assert / cover property） | 3 / 2 | - |
| Covergroups / coverpoints | 1 / 4 | |

## 4. 充分度判定與缺口

判定：**✅ Sufficient**（19 個 check，mutation score 80%）。

未被偵測的 mutant（測試缺口或等價 mutant）：

- `dut_mil_std_1553_model.sv:27 1'b0 inverted [busa_tx_sync <= 1'b0;]`
- `dut_mil_std_1553_model.sv:35 == flipped [if (gap == 4'd7) begin]`
- `dut_mil_std_1553_model.sv:45 1'b0 inverted [busa_tx_sync  <= 1'b0;]`

