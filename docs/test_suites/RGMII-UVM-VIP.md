# RGMII 測試套件（RGMII-UVM-VIP）

> 由 `tools/gen_test_suite_docs.py` 依 VIP 內容、`func_report.csv` 與 `mutation_report.csv` 自動產生，請勿手動修改。

## 1. 概要

| 項目 | 內容 |
|---|---|
| 類別 | Networking |
| 類型 | UVM VIP |
| 功能測試 | 1 個檔案，14 個 check，全部通過 |
| Mutation | 2/2 個 mutant 被偵測（100%） |
| 判定 | **✅ Sufficient**（14 個 check，mutation score 100%） |

## 2. 可執行的功能測試

執行：`python3 tools/run_func_tests.py RGMII-UVM-VIP`（Icarus Verilog 或 Verilator 5.052）。

### `tb/smoke_func_tb.sv`

結果：**PASS**（iverilog，14 checks）

| # | Check | 類型 |
|---|---|---|
| 1 | tx path reset quiet | check |
| 2 | tx_ctl high during stream | check |
| 3 | loopback nibble integrity | check |
| 4 | tx_ctl drops after stream | check |

## 3. UVM 測試平台內容

UVM 測試需商用模擬器（VCS / Xcelium / Questa）執行；開源流程只做 elaboration（L1a）。

| 項目 | 數量 | 名稱 |
|---|---|---|
| UVM tests | 1 | `rgmii_base_test` |
| Sequences | 2 | `rgmii_base_sequence`, `rgmii_transaction` |
| SVA（assert / cover property） | 3 / 2 | - |
| Covergroups / coverpoints | 1 / 2 | |

## 4. 充分度判定與缺口

判定：**✅ Sufficient**（14 個 check，mutation score 100%）。

無已知缺口。

