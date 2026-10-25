# UEC 測試套件（UEC-VIP）

> 由 `tools/gen_test_suite_docs.py` 依 VIP 內容、`func_report.csv` 與 `mutation_report.csv` 自動產生，請勿手動修改。

## 1. 概要

| 項目 | 內容 |
|---|---|
| 類別 | Networking |
| 類型 | UVM VIP |
| 功能測試 | 1 個檔案，12 個 check，全部通過 |
| Mutation | 8/12 個 mutant 被偵測（67%） |
| 判定 | **🟡 Partial**（mutation score 67%） |

## 2. 可執行的功能測試

執行：`python3 tools/run_func_tests.py UEC-VIP`（Icarus Verilog 或 Verilator 5.052）。

### `tb/smoke_func_tb.sv`

結果：**PASS**（iverilog，12 checks）

| # | Check | 類型 |
|---|---|---|
| 1 | rx quiet in reset | check |
| 2 | tx_ready high | check |
| 3 | latency not visible yet | check |
| 4 | good packet delivered | check |
| 5 | payload intact | check |
| 6 | no err on good packet | check |
| 7 | single-cycle delivery | check |
| 8 | undersize dropped | check |
| 9 | undersize err pulse | check |
| 10 | err is a pulse | check |
| 11 | oversize dropped with err | check |
| 12 | err clears | check |

## 3. UVM 測試平台內容

UVM 測試需商用模擬器（VCS / Xcelium / Questa）執行；開源流程只做 elaboration（L1a）。

| 項目 | 數量 | 名稱 |
|---|---|---|
| UVM tests | 1 | `uec_base_test` |
| Sequences | 2 | `uec_base_sequence`, `uec_transaction` |
| SVA（assert / cover property） | 4 / 2 | - |
| Covergroups / coverpoints | 1 / 3 | |

## 4. 充分度判定與缺口

判定：**🟡 Partial**（mutation score 67%）。

未被偵測的 mutant（測試缺口或等價 mutant）：

- `dut_uec_model.sv:27 1'b0 inverted [initial begin rx_valid = 1'b0; rx_err = 1'b0; end]`
- `dut_uec_model.sv:27 1'b0 inverted [initial begin rx_valid = 1'b0; rx_err = 1'b0; end]`
- `dut_uec_model.sv:30 1'b0 inverted [v1 <= 1'b0; v2 <= 1'b0; rx_valid <= 1'b0; rx_err <= 1'b0;]`
- `dut_uec_model.sv:30 1'b0 inverted [v1 <= 1'b0; v2 <= 1'b0; rx_valid <= 1'b0; rx_err <= 1'b0;]`

