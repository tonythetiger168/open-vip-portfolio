# MDIO 測試套件（MDIO-VIP）

> 由 `tools/gen_test_suite_docs.py` 依 VIP 內容、`func_report.csv` 與 `mutation_report.csv` 自動產生，請勿手動修改。

## 1. 概要

| 項目 | 內容 |
|---|---|
| 類別 | Networking |
| 類型 | RTL IP |
| 功能測試 | 1 個檔案，2263903 次斷言評估，全部通過 |
| Mutation | 9/12 個 mutant 被偵測（75%） |
| 判定 | **🟡 Partial**（mutation score 75%） |

## 2. 可執行的功能測試

執行：`python3 tools/run_func_tests.py MDIO-VIP`（Icarus Verilog 或 Verilator 5.052）。

### `tb/MDIO_tb.sv`

結果：**PASS**（verilator，2263903 次斷言評估）

## 3. UVM 測試平台內容

RTL IP：以 `tb/` 的 self-checking testbench 驗證，無 UVM 測試。

## 4. 充分度判定與缺口

判定：**🟡 Partial**（mutation score 75%）。

未被偵測的 mutant（測試缺口或等價 mutant）：

- `MDIO_top.sv:28 1'b1 inverted [mdc_s <= 1'b0; mdc_d <= 1'b0; mdio_s <= 1'b1;]`
- `MDIO_top.sv:49 0 -> 1 [for (int i = 0; i < 32; i++) regs[i] <= 16'h0000;]`
- `MDIO_top.sv:71 && flipped [read_frame <= (mdio_s == 1'b0) && (shift[0] == 1'b1); // OP ]`

