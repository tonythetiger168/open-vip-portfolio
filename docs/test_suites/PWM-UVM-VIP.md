# PWM 測試套件（PWM-UVM-VIP）

> 由 `tools/gen_test_suite_docs.py` 依 VIP 內容、`func_report.csv` 與 `mutation_report.csv` 自動產生，請勿手動修改。

## 1. 概要

| 項目 | 內容 |
|---|---|
| 類別 | Peripherals |
| 類型 | UVM VIP |
| 功能測試 | 1 個檔案，35 個 check，全部通過 |
| Mutation | 10/12 個 mutant 被偵測（83%） |
| 判定 | **✅ Sufficient**（35 個 check，mutation score 83%） |

## 2. 可執行的功能測試

執行：`python3 tools/run_func_tests.py PWM-UVM-VIP`（Icarus Verilog 或 Verilator 5.052）。

### `tb/smoke_func_tb.sv`

結果：**PASS**（iverilog，35 checks）

| # | Check | 類型 |
|---|---|---|
| 1 | pwm_out reset low | check |
| 2 | pwm_oe reset low | check |
| 3 | 50-cycle window has 2x duty=4 highs per period | check |
| 4 | pwm_oe high while enabled | check |
| 5 | pwm_out low when disabled | check |
| 6 | pwm_oe low when disabled | check |
| 7 | pwm_out low at duty=0 | check |

## 3. UVM 測試平台內容

UVM agent test（`pwm_func_test`：directed + constrained-random 流量，scoreboard 以 DUT 模型的參考模型逐筆比對，並比對 driver 與 monitor 的 transaction）在 Verilator 上以 `python3 tools/run_uvm_tests.py PWM-UVM-VIP` 執行；agent 由 `tools/gen_uvm_agents.py` 依 `tools/uvm_agents/` 的協定 spec 產生。

| 項目 | 數量 | 名稱 |
|---|---|---|
| UVM tests | 2 | `pwm_base_test`, `pwm_func_test` |
| Sequences | 3 | `pwm_base_sequence`, `pwm_directed_sequence`, `pwm_transaction` |
| SVA（assert / cover property） | 3 / 2 | - |
| Covergroups / coverpoints | 1 / 2 | |

## 4. 充分度判定與缺口

判定：**✅ Sufficient**（35 個 check，mutation score 83%）。

未被偵測的 mutant（測試缺口或等價 mutant）：

- `dut_pwm_model.sv:26 || flipped [if (!enable || period == 16'd0)]`
- `dut_pwm_model.sv:28 >= -> > in condition [else if (cnt >= period - 1)]`

