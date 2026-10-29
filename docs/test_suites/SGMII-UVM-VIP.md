# SGMII 測試套件（SGMII-UVM-VIP）

> 由 `tools/gen_test_suite_docs.py` 依 VIP 內容、`func_report.csv` 與 `mutation_report.csv` 自動產生，請勿手動修改。

## 1. 概要

| 項目 | 內容 |
|---|---|
| 類別 | Networking |
| 類型 | UVM VIP |
| 功能測試 | 1 個檔案，23 個 check，全部通過 |
| Mutation | 28/28 個 mutant 被偵測（100%） |
| 判定 | **✅ Sufficient**（23 個 check，mutation score 100%） |

## 2. 可執行的功能測試

執行：`python3 tools/run_func_tests.py SGMII-UVM-VIP`（Icarus Verilog 或 Verilator 5.052）。

### `tb/smoke_func_tb.sv`

結果：**PASS**（verilator，23 checks）

模型合約與範圍（摘自測試檔頭）：

```text
Functional smoke testbench (SGMII DUT model)
```

| # | Check | 類型 |
|---|---|---|
| 1 | /I2/ idle ordered set | check |
| 2 | idle repeats with RD- at every ordered set | check |
| 3 | /S/ (K27.7 RD-) at an even position | check |
| 4 | preamble 0x55 = D21.2 | check |
| 5 | /T/ (K29.7) after the frame | check |
| 6 | /R/ (K23.7) after /T/ | check |
| 7 | second /R/ when /T/ is odd | check |
| 8 | idle comma at an even position after /R/ | check |
| 9 | /V/ (K30.7) for tx_er | check |
| 10 | /C1/ = K28.5 D21.5 | check |
| 11 | the first configuration ordered set after reset is /C1/ | check |
| 12 | config word low byte 0x01 = D1.0 | check |
| 13 | /C2/ = K28.5 D2.2 | check |
| 14 | all 256 data bytes match the Clause 36 tables (%0d mismatches) | check |
| 15 | alternate D.x.A7 encodings exercised | check |
| 16 | /R/ after /T/ | check |
| 17 | second /R/ (K23.7) when /T/ is odd | check |
| 18 | /T/ seen at both parities | check |
| 19 | /I1/ and /I2/ chosen by the comma disparity (%0d bad) | check |
| 20 | first code groups after reset: K28.5 RD- then D16.2 RD+ | check |
| 21 | config word sampled with its comma (%0d of %0d bad) | check |
| 22 | /C1/ and /C2/ alternate | check |

## 3. UVM 測試平台內容

UVM agent test（`sgmii_func_test`：directed + constrained-random 流量，scoreboard 以 DUT 模型的參考模型逐筆比對，並比對 driver 與 monitor 的 transaction）在 Verilator 上以 `python3 tools/run_uvm_tests.py SGMII-UVM-VIP` 執行；agent 由 `tools/gen_uvm_agents.py` 依 `tools/uvm_agents/` 的協定 spec 產生。

| 項目 | 數量 | 名稱 |
|---|---|---|
| UVM tests | 2 | `sgmii_base_test`, `sgmii_func_test` |
| Sequences | 3 | `sgmii_base_sequence`, `sgmii_directed_sequence`, `sgmii_transaction` |
| SVA（assert / cover property） | 3 / 3 | - |
| Covergroups / coverpoints | 1 / 6 | |

## 4. 充分度判定與缺口

判定：**✅ Sufficient**（23 個 check，mutation score 100%）。

無已知缺口。

