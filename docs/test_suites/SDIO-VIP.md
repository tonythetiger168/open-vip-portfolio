# SDIO 測試套件（SDIO-VIP）

> 由 `tools/gen_test_suite_docs.py` 依 VIP 內容、`func_report.csv` 與 `mutation_report.csv` 自動產生，請勿手動修改。

## 1. 概要

| 項目 | 內容 |
|---|---|
| 類別 | Storage |
| 類型 | RTL IP |
| 功能測試 | 1 個檔案，125541 次斷言評估，全部通過 |
| Mutation | 8/12 個 mutant 被偵測（67%） |
| 判定 | **🟡 Partial**（mutation score 67%） |

## 2. 可執行的功能測試

執行：`python3 tools/run_func_tests.py SDIO-VIP`（Icarus Verilog 或 Verilator 5.052）。

### `tb/SDIO_tb.sv`

結果：**PASS**（verilator，125541 次斷言評估）

## 3. UVM 測試平台內容

RTL IP：以 `tb/` 的 self-checking testbench 驗證，無 UVM 測試。

## 4. 充分度判定與缺口

判定：**🟡 Partial**（mutation score 67%）。

未被偵測的 mutant（測試缺口或等價 mutant）：

- `SDIO_top.sv:32 32 -> 33 [parameter int DW = 32,       // data width (kept for interfa]`
- `SDIO_top.sv:161 1 -> 2 [wire bit_tick = (BIT_CLKS <= 1) || (bd_cnt == BIT_CLKS-1);]`
- `SDIO_top.sv:187 1'b0 inverted [rd_phase    <= 1'b0;]`
- `SDIO_top.sv:195 0 -> 1 [for (int l = 0; l < 4;   l++) crc16_rd[l] <= 16'h0000;]`

