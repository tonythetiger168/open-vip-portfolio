# HBM3 測試套件（hbm3-VIP）

> 由 `tools/gen_test_suite_docs.py` 依 VIP 內容、`func_report.csv` 與 `mutation_report.csv` 自動產生，請勿手動修改。

## 1. 概要

| 項目 | 內容 |
|---|---|
| 類別 | Memory |
| 類型 | UVM VIP |
| 功能測試 | 1 個檔案，118 個 check，全部通過 |
| Mutation | 7/7 個 mutant 被偵測（100%） |
| 判定 | **✅ Sufficient**（118 個 check，mutation score 100%） |

## 2. 可執行的功能測試

執行：`python3 tools/run_func_tests.py hbm3-VIP`（Icarus Verilog 或 Verilator 5.054）。

### `hbm3_vip/tb/func_hbm3_dev_tb.sv`

結果：**PASS**（verilator，118 checks）

JESD238 row / column bus 雙沿裝置模型：依編碼表以隨機 "valid" 位元產生指令；兩個 PC 交錯，且同一 bank / row / column；MRS 改 RL / WL；每個時序參數的邊界；refresh 與 PC 獨立性；RDA / WRA；bus error；CA parity 與 AERR；缺寫入資料；30 輪隨機流量對參考記憶體。

## 3. UVM 測試平台內容

UVM agent test（`hbm3_func_test`：directed + constrained-random 流量）以 `python3 tools/run_uvm_tests.py hbm3-VIP` 執行。agent 以兩個時脈沿驅動 R[9:0] / C[7:0] / APAR 與兩個 PC 的資料，接 `hbm3_dev_model.sv`；driver 依全部時序規則排程，monitor 自行解碼兩條 bus，規則檢查器檢查每個指令，scoreboard 以參考記憶體比對每筆讀取，並比對 driver 與 monitor 的 transaction；裝置拒絕任何指令、bus error 或 AERR 即為 UVM error。msim 結果：868 個指令、0 違規、770 個 scoreboard check、coverage 100%。

| 項目 | 數量 | 名稱 |
|---|---|---|
| UVM tests | 2 | `hbm3_base_test`, `hbm3_func_test` |
| Sequences | 3 | `hbm3_seq_base`, `hbm3_base_sequence`, `hbm3_directed_sequence` |
| SVA（assert / cover property） | 13 / 4 | - |
| Covergroups / coverpoints | 4 / 8 | |

## 4. 充分度判定與缺口

判定：**✅ Sufficient**（118 個 check，mutation score 100%）。

模型未實作的功能（不在測試範圍）：data bus inversion、data parity / DERR、ECC / SEV、IEEE 1500 port、power-down / self-refresh exit timing。

