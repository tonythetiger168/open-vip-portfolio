# CAN-FD 測試套件（CAN_FD-UVM-VIP）

> 由 `tools/gen_test_suite_docs.py` 依 VIP 內容、`func_report.csv` 與 `mutation_report.csv` 自動產生，請勿手動修改。

## 1. 概要

| 項目 | 內容 |
|---|---|
| 類別 | Automotive |
| 類型 | UVM VIP |
| 功能測試 | 1 個檔案，14 個 check，全部通過 |
| Mutation | 13/16 個 mutant 被偵測（81%） |
| 判定 | **✅ Sufficient**（14 個 check，mutation score 81%） |

## 2. 可執行的功能測試

執行：`python3 tools/run_func_tests.py CAN_FD-UVM-VIP`（Icarus Verilog 或 Verilator 5.052）。

### `tb/smoke_func_tb.sv`

結果：**PASS**（iverilog，14 checks）

| # | Check | 類型 |
|---|---|---|
| 1 | tx recessive out of reset | check |
| 2 | error state clean | check |
| 3 | tx recessive while idle | check |
| 4 | stuff error pulse on 6+ dominant | check |
| 5 | error counter incremented | check |
| 6 | stuff error clears with recessive | check |
| 7 | tx still recessive (IFS of delay pipe) | check |
| 8 | dominant propagated after delay | check |
| 9 | recessive restored after delay | check |

## 3. UVM 測試平台內容

UVM agent test（`can_fd_func_test`：directed + constrained-random 流量，scoreboard 以 DUT 模型的參考模型逐筆比對，並比對 driver 與 monitor 的 transaction）在 Verilator 上以 `python3 tools/run_uvm_tests.py CAN_FD-UVM-VIP` 執行；agent 由 `tools/gen_uvm_agents.py` 依 `tools/uvm_agents/` 的協定 spec 產生。

| 項目 | 數量 | 名稱 |
|---|---|---|
| UVM tests | 2 | `can_fd_base_test`, `can_fd_func_test` |
| Sequences | 3 | `can_fd_base_sequence`, `can_fd_directed_sequence`, `can_fd_transaction` |
| SVA（assert / cover property） | 3 / 2 | - |
| Covergroups / coverpoints | 1 / 3 | |

## 4. 充分度判定與缺口

判定：**✅ Sufficient**（14 個 check，mutation score 81%）。

未被偵測的 mutant（測試缺口或等價 mutant）：

- `dut_can_fd_model.sv:23 1'b1 inverted [rx_d      <= 1'b1;]`
- `dut_can_fd_model.sv:32 && flipped [if (rx == rx_d && rx == 1'b0)]`
- `dut_can_fd_model.sv:35 1'b0 inverted [same_cnt <= 1'b0;]`

