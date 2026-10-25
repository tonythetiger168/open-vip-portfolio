# WTB 測試套件（WTB-VIP）

> 由 `tools/gen_test_suite_docs.py` 依 VIP 內容、`func_report.csv` 與 `mutation_report.csv` 自動產生，請勿手動修改。

## 1. 概要

| 項目 | 內容 |
|---|---|
| 類別 | Debug |
| 類型 | RTL IP |
| 功能測試 | 1 個檔案，466062 次斷言評估，全部通過 |
| Mutation | 10/12 個 mutant 被偵測（83%） |
| 判定 | **✅ Sufficient**（self-checking testbench，mutation score 83%） |

## 2. 可執行的功能測試

執行：`python3 tools/run_func_tests.py WTB-VIP`（Icarus Verilog 或 Verilator 5.052）。

### `tb/WTB_tb.sv`

結果：**PASS**（verilator，466062 次斷言評估）

## 3. UVM 測試平台內容

RTL IP：以 `tb/` 的 self-checking testbench 驗證，無 UVM 測試。

## 4. 充分度判定與缺口

判定：**✅ Sufficient**（self-checking testbench，mutation score 83%）。

未被偵測的 mutant（測試缺口或等價 mutant）：

- `WTB_top.sv:14 32 -> 33 [parameter int DW = 32,             // cpu data width]`
- `WTB_top.sv:285 1'b0 inverted [tsh    <= {B_PRE[6:0], 1'b0};   // pre-shifted: bit7 driven ]`

