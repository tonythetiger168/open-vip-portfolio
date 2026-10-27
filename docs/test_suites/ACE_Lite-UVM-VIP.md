# ACE-Lite 測試套件（ACE_Lite-UVM-VIP）

> 由 `tools/gen_test_suite_docs.py` 依 VIP 內容、`func_report.csv` 與 `mutation_report.csv` 自動產生，請勿手動修改。

## 1. 概要

| 項目 | 內容 |
|---|---|
| 類別 | AMBA |
| 類型 | UVM VIP |
| 功能測試 | 1 個檔案，27 個 check，全部通過 |
| Mutation | 18/18 個 mutant 被偵測（100%） |
| 判定 | **✅ Sufficient**（27 個 check，mutation score 100%） |

## 2. 可執行的功能測試

執行：`python3 tools/run_func_tests.py ACE_Lite-UVM-VIP`（Icarus Verilog 或 Verilator 5.052）。

### `tb/smoke_func_tb.sv`

結果：**PASS**（iverilog，27 checks）

| # | Check | 類型 |
|---|---|---|
| 1 | channels reset quiet | check |
| 2 | no ready / BVALID out of reset while idle | check |
| 3 | AW accepted | check |
| 4 | W accepted | check |
| 5 | BVALID after write | check |
| 6 | BRESP OKAY | check |
| 7 | BVALID completes | check |
| 8 | no spurious BVALID | check |
| 9 | full-strobe write stored at awaddr[6:3] | check |
| 10 | BVALID after the partial write | check |
| 11 | WSTRB 0x0F writes byte lanes 0-3 only | check |
| 12 | WSTRB 0x01 writes byte lane 0 only | check |
| 13 | WREADY never high two cycles in a row | check |
| 14 | WREADY on every other cycle while WVALID is held (%0d of 8) | check |
| 15 | B held while AWVALID waits for AWREADY | check |
| 16 | B issued once the AW is accepted | check |

## 3. UVM 測試平台內容

UVM agent test（`ace_lite_func_test`：directed + constrained-random 流量，scoreboard 以 DUT 模型的參考模型逐筆比對，並比對 driver 與 monitor 的 transaction）在 Verilator 上以 `python3 tools/run_uvm_tests.py ACE_Lite-UVM-VIP` 執行；agent 由 `tools/gen_uvm_agents.py` 依 `tools/uvm_agents/` 的協定 spec 產生。

| 項目 | 數量 | 名稱 |
|---|---|---|
| UVM tests | 2 | `ace_lite_base_test`, `ace_lite_func_test` |
| Sequences | 3 | `ace_lite_base_sequence`, `ace_lite_directed_sequence`, `ace_lite_transaction` |
| SVA（assert / cover property） | 3 / 2 | - |
| Covergroups / coverpoints | 1 / 3 | |

## 4. 充分度判定與缺口

判定：**✅ Sufficient**（27 個 check，mutation score 100%）。

無已知缺口。

