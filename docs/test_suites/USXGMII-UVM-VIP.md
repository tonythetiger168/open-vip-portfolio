# USXGMII (multi-rate 64b/66b) 測試套件（USXGMII-UVM-VIP）

> 由 `tools/gen_test_suite_docs.py` 依 VIP 內容、`func_report.csv` 與 `mutation_report.csv` 自動產生，請勿手動修改。

## 1. 概要

| 項目 | 內容 |
|---|---|
| 類別 | Networking |
| 類型 | UVM VIP |
| 功能測試 | 1 個檔案，29 個 check，全部通過 |
| Mutation | 46/46 個 mutant 被偵測（100%） |
| 判定 | **✅ Sufficient**（29 個 check，mutation score 100%） |

## 2. 可執行的功能測試

執行：`python3 tools/run_func_tests.py USXGMII-UVM-VIP`（Icarus Verilog 或 Verilator 5.052）。

### `tb/smoke_func_tb.sv`

結果：**PASS**（iverilog，29 checks）

模型合約與範圍（摘自測試檔頭）：

```text
Functional smoke testbench (USXGMII DUT model)
```

| # | Check | 類型 |
|---|---|---|
| 1 | no report in reset | check |
| 2 | scrambler taps (%h) | check |
| 3 | idles: no report | check |
| 4 | 10G frame of %0d bytes (terminate with %0d) | check |
| 5 | frame at rate %0d (%0d copies) | check |
| 6 | bad FCS reported | check |
| 7 | frame across a pause in valid | check |
| 8 | invalid sync header 00: code 1, 16 bytes kept | check |
| 9 | invalid sync header 11: code 1 | check |
| 10 | error block in a frame: code 4 | check |
| 11 | idle block in a frame: code 4 | check |
| 12 | second start: the open frame ends with code 4 | check |
| 13 | the new frame runs on (its own bytes) | check |
| 14 | SFD D4: code 8, frame still received | check |
| 15 | preamble byte 54: code 8 | check |
| 16 | third copy differs: code 2 after the block | check |
| 17 | last copy differs: code 2 | check |
| 18 | outside a frame: data, bad header, differing copy, terminate ignored | check |
| 19 | clean frame after the faults | check |
| 20 | 1G frame, then 10G frame | check |

## 3. UVM 測試平台內容

UVM agent test（`usxgmii_func_test`：directed + constrained-random 流量，scoreboard 以 DUT 模型的參考模型逐筆比對，並比對 driver 與 monitor 的 transaction）在 Verilator 上以 `python3 tools/run_uvm_tests.py USXGMII-UVM-VIP` 執行；agent 由 `tools/gen_uvm_agents.py` 依 `tools/uvm_agents/` 的協定 spec 產生。

| 項目 | 數量 | 名稱 |
|---|---|---|
| UVM tests | 2 | `usxgmii_base_test`, `usxgmii_func_test` |
| Sequences | 3 | `usxgmii_base_sequence`, `usxgmii_directed_sequence`, `usxgmii_transaction` |
| SVA（assert / cover property） | 3 / 3 | - |
| Covergroups / coverpoints | 1 / 4 | |

## 4. 充分度判定與缺口

判定：**✅ Sufficient**（29 個 check，mutation score 100%）。

無已知缺口。

