# CAN XL 測試套件（CAN_XL-UVM-VIP）

> 由 `tools/gen_test_suite_docs.py` 依 VIP 內容、`func_report.csv` 與 `mutation_report.csv` 自動產生，請勿手動修改。

## 1. 概要

| 項目 | 內容 |
|---|---|
| 類別 | Automotive |
| 類型 | UVM VIP |
| 功能測試 | 1 個檔案，38 個 check，全部通過 |
| Mutation | 28/28 個 mutant 被偵測（100%） |
| 判定 | **✅ Sufficient**（38 個 check，mutation score 100%） |

## 2. 可執行的功能測試

執行：`python3 tools/run_func_tests.py CAN_XL-UVM-VIP`（Icarus Verilog 或 Verilator 5.052）。

### `tb/smoke_func_tb.sv`

結果：**PASS**（verilator，38 checks）

模型合約與範圍（摘自測試檔頭）：

```text
Functional smoke testbench (CAN XL DUT model)
```

| # | Check | 類型 |
|---|---|---|
| 1 | tx recessive while idle | check |
| 2 | tx recessive in reset | check |
| 3 | good frame ACKed and reported | check |
| 4 | fields reported | check |
| 5 | data sum and SDT reported | check |
| 6 | a good frame drives exactly one dominant bit (ACK) | check |
| 7 | frame reported after ACK delimiter and 7-bit EOF (%0d) | check |
| 8 | FCRC error flagged, no ACK | check |
| 9 | six-bit error flag (%0d dominant bits) | check |
| 10 | receive error counter +1 | check |
| 11 | PCRC error flagged | check |
| 12 | good frame after errors, counter -1 | check |
| 13 | VCID field boundary (PCRC ends at bit 37) | check |
| 14 | SBC error flagged | check |
| 15 | ADH | check |
| 16 | dynamic stuff error in arbitration | check |
| 17 | VCID filtered: ACKed, not reported | check |

## 3. UVM 測試平台內容

UVM agent test（`can_xl_func_test`：directed + constrained-random 流量，scoreboard 以 DUT 模型的參考模型逐筆比對，並比對 driver 與 monitor 的 transaction）在 Verilator 上以 `python3 tools/run_uvm_tests.py CAN_XL-UVM-VIP` 執行；agent 由 `tools/gen_uvm_agents.py` 依 `tools/uvm_agents/` 的協定 spec 產生。

| 項目 | 數量 | 名稱 |
|---|---|---|
| UVM tests | 2 | `can_xl_base_test`, `can_xl_func_test` |
| Sequences | 3 | `can_xl_base_sequence`, `can_xl_directed_sequence`, `can_xl_transaction` |
| SVA（assert / cover property） | 5 / 2 | - |
| Covergroups / coverpoints | 1 / 4 | |

## 4. 充分度判定與缺口

判定：**✅ Sufficient**（38 個 check，mutation score 100%）。

無已知缺口。

