# XGMII 測試套件（XGMII-VIP）

> 由 `tools/gen_test_suite_docs.py` 依 VIP 內容、`func_report.csv` 與 `mutation_report.csv` 自動產生，請勿手動修改。

## 1. 概要

| 項目 | 內容 |
|---|---|
| 類別 | Networking |
| 類型 | RTL IP |
| 功能測試 | 1 個檔案，19643 次斷言評估，全部通過 |
| Mutation | 10/10 個 mutant 被偵測（100%） |
| 判定 | **✅ Sufficient**（self-checking testbench，mutation score 100%） |

## 2. 可執行的功能測試

執行：`python3 tools/run_func_tests.py XGMII-VIP`（Icarus Verilog 或 Verilator 5.052）。

### `tb/XGMII_tb.sv`

結果：**PASS**（verilator，19643 次斷言評估）

## 3. UVM 測試平台內容

RTL IP：以 `tb/` 的 self-checking testbench 驗證，無 UVM 測試。

## 4. 充分度判定與缺口

判定：**✅ Sufficient**（self-checking testbench，mutation score 100%）。

無已知缺口。

