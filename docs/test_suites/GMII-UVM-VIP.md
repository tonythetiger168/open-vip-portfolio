# GMII 測試套件（GMII-UVM-VIP）

> 由 `tools/gen_test_suite_docs.py` 依 VIP 內容、`func_report.csv` 與 `mutation_report.csv` 自動產生，請勿手動修改。

## 1. 概要

| 項目 | 內容 |
|---|---|
| 類別 | Networking |
| 類型 | UVM VIP |
| 功能測試 | 1 個檔案，22 個 check，全部通過 |
| Mutation | 2/3 個 mutant 被偵測（67%） |
| 判定 | **🟡 Partial**（mutation score 67%） |

## 2. 可執行的功能測試

執行：`python3 tools/run_func_tests.py GMII-UVM-VIP`（Icarus Verilog 或 Verilator 5.052）。

### `tb/smoke_func_tb.sv`

結果：**PASS**（iverilog，22 checks）

| # | Check | 類型 |
|---|---|---|
| 1 | rx path reset quiet | check |
| 2 | rx_dv low when tx_en low | check |
| 3 | rx_dv high during stream | check |
| 4 | loopback data integrity | check |
| 5 | rx_dv drops after stream | check |
| 6 | error passthrough | check |

## 3. UVM 測試平台內容

UVM 測試需商用模擬器（VCS / Xcelium / Questa）執行；開源流程只做 elaboration（L1a）。

| 項目 | 數量 | 名稱 |
|---|---|---|
| UVM tests | 1 | `gmii_base_test` |
| Sequences | 2 | `gmii_base_sequence`, `gmii_transaction` |
| SVA（assert / cover property） | 3 / 2 | - |
| Covergroups / coverpoints | 1 / 3 | |

## 4. 充分度判定與缺口

判定：**🟡 Partial**（mutation score 67%）。

未被偵測的 mutant（測試缺口或等價 mutant）：

- `dut_gmii_model.sv:23 1'b0 inverted [rx_er <= 1'b0;]`

