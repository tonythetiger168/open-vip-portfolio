# ACE-Lite 測試套件（ACE_Lite-UVM-VIP）

> 由 `tools/gen_test_suite_docs.py` 依 VIP 內容、`func_report.csv` 與 `mutation_report.csv` 自動產生，請勿手動修改。

## 1. 概要

| 項目 | 內容 |
|---|---|
| 類別 | AMBA |
| 類型 | UVM VIP |
| 功能測試 | 1 個檔案，12 個 check，全部通過 |
| Mutation | 12/19 個 mutant 被偵測（63%） |
| 判定 | **🟡 Partial**（mutation score 63%） |

## 2. 可執行的功能測試

執行：`python3 tools/run_func_tests.py ACE_Lite-UVM-VIP`（Icarus Verilog 或 Verilator 5.052）。

### `tb/smoke_func_tb.sv`

結果：**PASS**（iverilog，12 checks）

| # | Check | 類型 |
|---|---|---|
| 1 | channels reset quiet | check |
| 2 | AW accepted | check |
| 3 | W accepted | check |
| 4 | BVALID after write | check |
| 5 | BRESP OKAY | check |
| 6 | BVALID completes | check |
| 7 | no spurious BVALID | check |

## 3. UVM 測試平台內容

UVM 測試需商用模擬器（VCS / Xcelium / Questa）執行；開源流程只做 elaboration（L1a）。

| 項目 | 數量 | 名稱 |
|---|---|---|
| UVM tests | 1 | `ace_lite_base_test` |
| Sequences | 2 | `ace_lite_base_sequence`, `ace_lite_transaction` |
| SVA（assert / cover property） | 3 / 2 | - |
| Covergroups / coverpoints | 1 / 7 | |

## 4. 充分度判定與缺口

判定：**🟡 Partial**（mutation score 63%）。

未被偵測的 mutant（測試缺口或等價 mutant）：

- `dut_ace_lite_model.sv:32 1'b0 inverted [wpend   <= 1'b0;]`
- `dut_ace_lite_model.sv:34 && flipped [awready <= awvalid && !awready;]`
- `dut_ace_lite_model.sv:35 && flipped [wready  <= wvalid  && !wready;]`
- `dut_ace_lite_model.sv:36 && flipped [if (wvalid && wready) begin]`
- `dut_ace_lite_model.sv:37 0 -> 1 [for (int i = 0; i < 8; i++)]`
- `dut_ace_lite_model.sv:37 8 -> 9 [for (int i = 0; i < 8; i++)]`
- `dut_ace_lite_model.sv:43 ! dropped in condition [else if (wpend && !(awvalid && !awready)) begin]`

