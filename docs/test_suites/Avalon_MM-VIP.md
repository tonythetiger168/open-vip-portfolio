# Avalon-MM 測試套件（Avalon_MM-VIP）

> 由 `tools/gen_test_suite_docs.py` 依 VIP 內容、`func_report.csv` 與 `mutation_report.csv` 自動產生，請勿手動修改。

## 1. 概要

| 項目 | 內容 |
|---|---|
| 類別 | Interconnect |
| 類型 | RTL IP |
| 功能測試 | 2 個檔案，33 個 check，11732 次斷言評估，全部通過 |
| Mutation | 9/9 個 mutant 被偵測（100%） |
| 判定 | **✅ Sufficient**（33 個 check，mutation score 100%） |

## 2. 可執行的功能測試

執行：`python3 tools/run_func_tests.py Avalon_MM-VIP`（Icarus Verilog 或 Verilator 5.052）。

### `tb/Avalon_MM_tb.sv`

結果：**PASS**（verilator，11732 次斷言評估）

### `tb/func_avalon_mm_tb.sv`

結果：**PASS**（verilator，33 checks）

| # | Check | 類型 |
|---|---|---|
| 1 | fast-window write burst: no wait states | check |
| 2 | fast-window read command: no wait state | check |
| 3 | fast-window read burst: 4 back-to-back beats right after the command | check |
| 4 | fast-window burst data in order | check |
| 5 | legal fast-window traffic raises no irq | check |
| 6 | first slow-window write after reset: exactly 1 wait state (%0d) | check |
| 7 | slow-window write burst: exactly 1 wait state per beat | check |
| 8 | slow-window read command: exactly 1 wait state | check |
| 9 | slow-window read burst: one-cycle bubble before every beat | check |
| 10 | slow-window burst data in order | check |
| 11 | slow-window write after a read: exactly 1 wait state | check |
| 12 | slow single read returns the new data after one bubble | check |
| 13 | legal slow-window traffic raises no irq | check |
| 14 | slow write behind a slow read: 2 drain + 1 wait-state cycles (%0d) | check |
| 15 | slow command presented at reset release: 1 wait state (%0d) | check |
| 16 | write burst crossing into the slow window: wait states only on slow beats | check |
| 17 | burstcount 16 is legal: 16 beats, no irq | check |
| 18 | burstcount 0 transfers one beat | check |
| 19 | burstcount 0 raises no irq | check |
| 20 | burstcount 17 clamped to 16 beats (%0d) | check |
| 21 | burstcount > 16 raises irq | check |
| 22 | simultaneous read and write raise irq | check |
| 23 | out-of-range single write raises irq | check |
| 24 | write burst running past 0x3FF raises irq | check |
| 25 | in-range beat of the truncated write burst landed | check |
| 26 | out-of-range read raises irq and returns no data | check |
| 27 | read burst past 0x3FF truncated to the in-range beats + irq | check |
| 28 | reset clears irq | check |
| 29 | each byte lane written alone (%h) | check |
| 30 | byteenable 0 writes nothing | check |
| 31 | 60 random accesses: data matches the reference (%0d bad) | check |
| 32 | 60 random accesses: wait states/bubbles match the window (%0d bad) | check |
| 33 | random legal accesses raise no irq | check |

## 3. UVM 測試平台內容

RTL IP：以 `tb/` 的 self-checking testbench 驗證，無 UVM 測試。

## 4. 充分度判定與缺口

判定：**✅ Sufficient**（33 個 check，mutation score 100%）。

無已知缺口。

