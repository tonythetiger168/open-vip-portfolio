# CHI 測試套件（CHI-VIP）

> 由 `tools/gen_test_suite_docs.py` 依 VIP 內容、`func_report.csv` 與 `mutation_report.csv` 自動產生，請勿手動修改。

## 1. 概要

| 項目 | 內容 |
|---|---|
| 類別 | AMBA |
| 類型 | RTL IP |
| 功能測試 | 1 個檔案，6489 次斷言評估，全部通過 |
| Mutation | 8/12 個 mutant 被偵測（67%） |
| 判定 | **🟡 Partial**（mutation score 67%） |

## 2. 可執行的功能測試

執行：`python3 tools/run_func_tests.py CHI-VIP`（Icarus Verilog 或 Verilator 5.052）。

### `tb/CHI_tb.sv`

結果：**PASS**（verilator，6489 次斷言評估）

## 3. UVM 測試平台內容

RTL IP：以 `tb/` 的 self-checking testbench 驗證，無 UVM 測試。

## 4. 充分度判定與缺口

判定：**🟡 Partial**（mutation score 67%）。

未被偵測的 mutant（測試缺口或等價 mutant）：

- `CHI_top.sv:44 == flipped [assign irq         = (cstate == C_SEND) && (tx_crd != 0);]`
- `CHI_top.sv:44 && flipped [assign irq         = (cstate == C_SEND) && (tx_crd != 0);]`
- `CHI_top.sv:61 0 -> 1 [C_IDLE: if (txreqflitv && rx_crd != 0) begin]`
- `CHI_top.sv:66 == flipped [C_LAT: if (lat_cnt == 0) cstate <= C_SEND;]`

