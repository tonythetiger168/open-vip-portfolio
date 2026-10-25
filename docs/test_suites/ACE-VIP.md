# ACE 測試套件（ACE-VIP）

> 由 `tools/gen_test_suite_docs.py` 依 VIP 內容、`func_report.csv` 與 `mutation_report.csv` 自動產生，請勿手動修改。

## 1. 概要

| 項目 | 內容 |
|---|---|
| 類別 | AMBA |
| 類型 | RTL IP |
| 功能測試 | 1 個檔案，45337 次斷言評估，全部通過 |
| Mutation | 8/12 個 mutant 被偵測（67%） |
| 判定 | **🟡 Partial**（mutation score 67%） |

## 2. 可執行的功能測試

執行：`python3 tools/run_func_tests.py ACE-VIP`（Icarus Verilog 或 Verilator 5.052）。

### `tb/ACE_tb.sv`

結果：**PASS**（verilator，45337 次斷言評估）

| # | 測試段落 |
|---|---|
| 1 | 1. reset state check |
| 2 | 2. burst write then read-back compare |
| 3 | 3. snoop ReadShared hit on dirty line |
| 4 | 4. snoop miss (never-written address) |
| 5 | 5. MakeUnique invalidation |
| 6 | 6. error injection: out-of-range -> SLVERR + irq |
| 7 | 7. back-to-back transactions |

## 3. UVM 測試平台內容

RTL IP：以 `tb/` 的 self-checking testbench 驗證，無 UVM 測試。

## 4. 充分度判定與缺口

判定：**🟡 Partial**（mutation score 67%）。

未被偵測的 mutant（測試缺口或等價 mutant）：

- `ACE_top.sv:10 32 -> 33 [parameter int DW = 32,          // data width]`
- `ACE_top.sv:140 1'b0 inverted [snp_xfer_q  <= 1'b0;]`
- `ACE_top.sv:192 1'b1 inverted [if (rerr_q) irq <= 1'b1;]`
- `ACE_top.sv:222 1'b0 inverted [line_valid[acaddr[7:2]] <= 1'b0;]`

