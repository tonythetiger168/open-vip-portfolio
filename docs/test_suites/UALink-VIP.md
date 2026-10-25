# UALink 測試套件（UALink-VIP）

> 由 `tools/gen_test_suite_docs.py` 依 VIP 內容、`func_report.csv` 與 `mutation_report.csv` 自動產生，請勿手動修改。

## 1. 概要

| 項目 | 內容 |
|---|---|
| 類別 | Interconnect |
| 類型 | UVM VIP |
| 功能測試 | 1 個檔案，11 個 check，全部通過 |
| Mutation | 10/18 個 mutant 被偵測（56%） |
| 判定 | **🟡 Partial**（mutation score 56%） |

## 2. 可執行的功能測試

執行：`python3 tools/run_func_tests.py UALink-VIP`（Icarus Verilog 或 Verilator 5.052）。

### `tb/smoke_func_tb.sv`

結果：**PASS**（iverilog，11 checks）

| # | Check | 類型 |
|---|---|---|
| 1 | ready high when idle | check |
| 2 | rsp quiet in reset | check |
| 3 | ready drops after accept | check |
| 4 | write rsp OK | check |
| 5 | rsp completes | check |
| 6 | ready returns | check |
| 7 | read rsp OK | check |
| 8 | read data matches write | check |
| 9 | illegal opcode ERR | check |
| 10 | rsp held until ready | check |
| 11 | rsp clears after ready | check |

## 3. UVM 測試平台內容

UVM agent test（`ualink_func_test`：directed + constrained-random 流量，scoreboard 以 DUT 模型的參考模型逐筆比對，並比對 driver 與 monitor 的 transaction）在 Verilator 上以 `python3 tools/run_uvm_tests.py UALink-VIP` 執行；agent 由 `tools/gen_uvm_agents.py` 依 `tools/uvm_agents/` 的協定 spec 產生。

| 項目 | 數量 | 名稱 |
|---|---|---|
| UVM tests | 2 | `ualink_base_test`, `ualink_func_test` |
| Sequences | 3 | `ualink_base_sequence`, `ualink_directed_sequence`, `ualink_transaction` |
| SVA（assert / cover property） | 4 / 2 | - |
| Covergroups / coverpoints | 1 / 3 | |

## 4. 充分度判定與缺口

判定：**🟡 Partial**（mutation score 56%）。

未被偵測的 mutant（測試缺口或等價 mutant）：

- `dut_ualink_model.sv:27 1'b0 inverted [initial begin rsp_valid = 1'b0; req_ready = 1'b1; rsp_status]`
- `dut_ualink_model.sv:27 1'b1 inverted [initial begin rsp_valid = 1'b0; req_ready = 1'b1; rsp_status]`
- `dut_ualink_model.sv:30 1'b0 inverted [busy <= 1'b0; req_ready <= 1'b1;]`
- `dut_ualink_model.sv:33 0 -> 1 [for (i = 0; i < 64; i++) mem[i] <= 64'h0;]`
- `dut_ualink_model.sv:33 64 -> 65 [for (i = 0; i < 64; i++) mem[i] <= 64'h0;]`
- `dut_ualink_model.sv:35 && flipped [if (req_valid && req_ready) begin]`
- `dut_ualink_model.sv:36 1'b1 inverted [busy <= 1'b1;]`
- `dut_ualink_model.sv:52 1'b0 inverted [busy <= 1'b0;]`

