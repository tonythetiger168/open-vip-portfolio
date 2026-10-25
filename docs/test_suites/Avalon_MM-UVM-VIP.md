# Avalon-MM 測試套件（Avalon_MM-UVM-VIP）

> 由 `tools/gen_test_suite_docs.py` 依 VIP 內容、`func_report.csv` 與 `mutation_report.csv` 自動產生，請勿手動修改。

## 1. 概要

| 項目 | 內容 |
|---|---|
| 類別 | Interconnect |
| 類型 | UVM VIP |
| 功能測試 | 1 個檔案，34 個 check，全部通過 |
| Mutation | 8/15 個 mutant 被偵測（53%） |
| 判定 | **🟡 Partial**（mutation score 53%） |

## 2. 可執行的功能測試

執行：`python3 tools/run_func_tests.py Avalon_MM-UVM-VIP`（Icarus Verilog 或 Verilator 5.052）。

### `tb/smoke_func_tb.sv`

結果：**PASS**（iverilog，34 checks）

| # | Check | 類型 |
|---|---|---|
| 1 | waitrequest reset low | check |
| 2 | response reset OKAY | check |
| 3 | write stalls on waitrequest | check |
| 4 | waitrequest released | check |
| 5 | read stalls on waitrequest | check |
| 6 | read waitrequest released | check |
| 7 | readdatavalid after read | check |
| 8 | read data integrity | check |
| 9 | response OKAY | check |
| 10 | no readdatavalid when idle | check |

## 3. UVM 測試平台內容

UVM agent test（`avalon_mm_func_test`：directed + constrained-random 流量，scoreboard 以 DUT 模型的參考模型逐筆比對，並比對 driver 與 monitor 的 transaction）在 Verilator 上以 `python3 tools/run_uvm_tests.py Avalon_MM-UVM-VIP` 執行；agent 由 `tools/gen_uvm_agents.py` 依 `tools/uvm_agents/` 的協定 spec 產生。

| 項目 | 數量 | 名稱 |
|---|---|---|
| UVM tests | 2 | `avalon_mm_base_test`, `avalon_mm_func_test` |
| Sequences | 3 | `avalon_mm_base_sequence`, `avalon_mm_directed_sequence`, `avalon_mm_transaction` |
| SVA（assert / cover property） | 4 / 2 | - |
| Covergroups / coverpoints | 1 / 2 | |

## 4. 充分度判定與缺口

判定：**🟡 Partial**（mutation score 53%）。

未被偵測的 mutant（測試缺口或等價 mutant）：

- `dut_avalon_mm_model.sv:27 1'b0 inverted [av_readdatavalid  <= 1'b0;]`
- `dut_avalon_mm_model.sv:29 1'b0 inverted [rd_d              <= 1'b0;]`
- `dut_avalon_mm_model.sv:30 0 -> 1 [for (int i = 0; i < 64; i++) mem[i] <= '0;]`
- `dut_avalon_mm_model.sv:30 64 -> 65 [for (int i = 0; i < 64; i++) mem[i] <= '0;]`
- `dut_avalon_mm_model.sv:33 || flipped [av_waitrequest <= (av_write || av_read) && !av_waitrequest;]`
- `dut_avalon_mm_model.sv:33 && flipped [av_waitrequest <= (av_write || av_read) && !av_waitrequest;]`
- `dut_avalon_mm_model.sv:40 && flipped [rd_d             <= av_read && av_waitrequest;]`

