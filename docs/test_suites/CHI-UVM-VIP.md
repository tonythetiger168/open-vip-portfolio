# CHI 測試套件（CHI-UVM-VIP）

> 由 `tools/gen_test_suite_docs.py` 依 VIP 內容、`func_report.csv` 與 `mutation_report.csv` 自動產生，請勿手動修改。

## 1. 概要

| 項目 | 內容 |
|---|---|
| 類別 | AMBA |
| 類型 | UVM VIP |
| 功能測試 | 1 個檔案，11 個 check，全部通過 |
| Mutation | 7/10 個 mutant 被偵測（70%） |
| 判定 | **🟡 Partial**（mutation score 70%） |

## 2. 可執行的功能測試

執行：`python3 tools/run_func_tests.py CHI-UVM-VIP`（Icarus Verilog 或 Verilator 5.052）。

### `tb/smoke_func_tb.sv`

結果：**PASS**（iverilog，11 checks）

| # | Check | 類型 |
|---|---|---|
| 1 | channels reset quiet | check |
| 2 | no response without request | check |
| 3 | REQ accepted | check |
| 4 | DAT accepted | check |
| 5 | RSPVALID after request | check |
| 6 | RSP OK status | check |
| 7 | RSP completes | check |
| 8 | second REQ accepted | check |
| 9 | second RSP received | check |

## 3. UVM 測試平台內容

UVM 測試需商用模擬器（VCS / Xcelium / Questa）執行；開源流程只做 elaboration（L1a）。

| 項目 | 數量 | 名稱 |
|---|---|---|
| UVM tests | 1 | `chi_base_test` |
| Sequences | 2 | `chi_base_sequence`, `chi_transaction` |
| SVA（assert / cover property） | 3 / 2 | - |
| Covergroups / coverpoints | 1 / 6 | |

## 4. 充分度判定與缺口

判定：**🟡 Partial**（mutation score 70%）。

未被偵測的 mutant（測試缺口或等價 mutant）：

- `dut_chi_model.sv:29 1'b0 inverted [dat_ready <= 1'b0;]`
- `dut_chi_model.sv:33 1'b0 inverted [req_ready <= 1'b0;]`
- `dut_chi_model.sv:34 1'b0 inverted [dat_ready <= 1'b0;]`

