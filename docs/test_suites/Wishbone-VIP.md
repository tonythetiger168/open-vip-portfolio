# Wishbone 測試套件（Wishbone-VIP）

> 由 `tools/gen_test_suite_docs.py` 依 VIP 內容、`func_report.csv` 與 `mutation_report.csv` 自動產生，請勿手動修改。

## 1. 概要

| 項目 | 內容 |
|---|---|
| 類別 | Interconnect |
| 類型 | RTL IP |
| 功能測試 | 1 個檔案，6177 次斷言評估，全部通過 |
| Mutation | 8/12 個 mutant 被偵測（67%） |
| 判定 | **🟡 Partial**（mutation score 67%） |

## 2. 可執行的功能測試

執行：`python3 tools/run_func_tests.py Wishbone-VIP`（Icarus Verilog 或 Verilator 5.052）。

### `tb/Wishbone_tb.sv`

結果：**PASS**（verilator，6177 次斷言評估）

## 3. UVM 測試平台內容

RTL IP：以 `tb/` 的 self-checking testbench 驗證，無 UVM 測試。

## 4. 充分度判定與缺口

判定：**🟡 Partial**（mutation score 67%）。

未被偵測的 mutant（測試缺口或等價 mutant）：

- `Wishbone_top.sv:12 32 -> 33 [parameter int DW    = 32,   // data width]`
- `Wishbone_top.sv:91 1'b0 inverted [q_we[0]   <= 1'b0;  q_we[1]   <= 1'b0;]`
- `Wishbone_top.sv:96 1'b0 inverted [q_rsv[0]  <= 1'b0;  q_rsv[1]  <= 1'b0;]`
- `Wishbone_top.sv:98 1'b0 inverted [cls_blk   <= 1'b0;]`

