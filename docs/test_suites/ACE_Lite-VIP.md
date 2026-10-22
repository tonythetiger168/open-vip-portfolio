# ACE-Lite 測試套件（ACE_Lite-VIP）

> 由 `tools/gen_test_suite_docs.py` 依 VIP 內容、`func_report.csv` 與 `mutation_report.csv` 自動產生，請勿手動修改。

## 1. 概要

| 項目 | 內容 |
|---|---|
| 類別 | AMBA |
| 類型 | RTL IP |
| 功能測試 | 1 個檔案，49480 次斷言評估，全部通過 |
| Mutation | 9/12 個 mutant 被偵測（75%） |
| 判定 | **🟡 Partial**（mutation score 75%） |

## 2. 可執行的功能測試

執行：`python3 tools/run_func_tests.py ACE_Lite-VIP`（Icarus Verilog 或 Verilator 5.052）。

### `tb/ACE_Lite_tb.sv`

結果：**PASS**（verilator，49480 次斷言評估）

| # | 測試段落 |
|---|---|
| 1 | 1. reset state check |
| 2 | 2. burst write / read-back compare |
| 3 | 3. byte-strobe merge |
| 4 | 4. barrier write then read: in-order completion |
| 5 | 5. error injection: out-of-range -> SLVERR + irq |
| 6 | 6. back-to-back transactions |

## 3. UVM 測試平台內容

RTL IP：以 `tb/` 的 self-checking testbench 驗證，無 UVM 測試。

## 4. 充分度判定與缺口

判定：**🟡 Partial**（mutation score 75%）。

未被偵測的 mutant（測試缺口或等價 mutant）：

- `ACE_Lite_top.sv:11 32 -> 33 [parameter int DW = 32,          // data width]`
- `ACE_Lite_top.sv:89 1'b0 inverted [werr_q  <= 1'b0;]`
- `ACE_Lite_top.sv:117 1'b1 inverted [if (werr_q) irq <= 1'b1;]`

