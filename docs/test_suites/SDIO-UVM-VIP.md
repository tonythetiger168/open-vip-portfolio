# SDIO 測試套件（SDIO-UVM-VIP）

> 由 `tools/gen_test_suite_docs.py` 依 VIP 內容、`func_report.csv` 與 `mutation_report.csv` 自動產生，請勿手動修改。

## 1. 概要

| 項目 | 內容 |
|---|---|
| 類別 | Storage |
| 類型 | UVM VIP |
| 功能測試 | 1 個檔案，15 個 check，全部通過 |
| Mutation | 10/18 個 mutant 被偵測（56%） |
| 判定 | **🟡 Partial**（mutation score 56%） |

## 2. 可執行的功能測試

執行：`python3 tools/run_func_tests.py SDIO-UVM-VIP`（Icarus Verilog 或 Verilator 5.052）。

### `tb/smoke_func_tb.sv`

結果：**PASS**（iverilog，15 checks）

| # | Check | 類型 |
|---|---|---|
| 1 | card quiet out of reset | check |
| 2 | no response without command | check |
| 3 | CMD8 response driven | check |
| 4 | response carries low bits (not stuck high) | check |
| 5 | card released after response | check |

## 3. UVM 測試平台內容

UVM agent test（`sdio_func_test`：directed + constrained-random 流量，scoreboard 以 DUT 模型的參考模型逐筆比對，並比對 driver 與 monitor 的 transaction）在 Verilator 上以 `python3 tools/run_uvm_tests.py SDIO-UVM-VIP` 執行；agent 由 `tools/gen_uvm_agents.py` 依 `tools/uvm_agents/` 的協定 spec 產生。

| 項目 | 數量 | 名稱 |
|---|---|---|
| UVM tests | 2 | `sdio_base_test`, `sdio_func_test` |
| Sequences | 3 | `sdio_base_sequence`, `sdio_directed_sequence`, `sdio_transaction` |
| SVA（assert / cover property） | 3 / 2 | - |
| Covergroups / coverpoints | 1 / 1 | |

## 4. 充分度判定與缺口

判定：**🟡 Partial**（mutation score 56%）。

未被偵測的 mutant（測試缺口或等價 mutant）：

- `dut_sdio_model.sv:30 1'b0 inverted [resp   <= 1'b0;]`
- `dut_sdio_model.sv:32 1'b0 inverted [cmd_o  <= 1'b0;]`
- `dut_sdio_model.sv:39 && flipped [if (!cmd_i && bcnt == 0) begin]`
- `dut_sdio_model.sv:39 ! dropped in condition [if (!cmd_i && bcnt == 0) begin]`
- `dut_sdio_model.sv:47 == flipped [if (bcnt == 6'd47) begin]`
- `dut_sdio_model.sv:50 1'b1 inverted [rsh  <= {2'b00, sh[45:40], 8'h00, 8'h00, 8'h01, 8'h00, 7'h00]`
- `dut_sdio_model.sv:57 1'b0 inverted [rsh    <= {rsh[46:0], 1'b0};]`
- `dut_sdio_model.sv:64 1'b0 inverted [dat_oe <= 1'b0;]`

