# BoW die-to-die PHY v2.0 (OCP ODSA Bunch of Wires) 測試套件（BoW-UVM-VIP）

> 由 `tools/gen_test_suite_docs.py` 依 VIP 內容、`func_report.csv` 與 `mutation_report.csv` 自動產生，請勿手動修改。

## 1. 概要

| 項目 | 內容 |
|---|---|
| 類別 | Interconnect |
| 類型 | UVM VIP |
| 功能測試 | 1 個檔案，34 個 check，全部通過 |
| Mutation | 21/21 個 mutant 被偵測（100%） |
| 判定 | **✅ Sufficient**（34 個 check，mutation score 100%） |

## 2. 可執行的功能測試

執行：`python3 tools/run_func_tests.py BoW-UVM-VIP`（Icarus Verilog 或 Verilator 5.052）。

### `tb/smoke_func_tb.sv`

結果：**PASS**（iverilog，34 checks）

模型合約與範圍（摘自測試檔頭）：

```text
Functional smoke testbench (BoW DUT model)
```

| # | Check | 類型 |
|---|---|---|
| 1 | reset: not ready, nothing out | check |
| 2 | no PHYReady without the training pattern | check |
| 3 | wrong training pattern: not ready | check |
| 4 | 31 UI of pattern: not yet ready | check |
| 5 | ready after 32 UI with the last 16 equal to the pattern | check |
| 6 | first word = first 4 UI of the pattern | check |
| 7 | UI k lands in P_D[16k+15:16k], AUX / FEC bit k | check |
| 8 | IDLE postamble / preamble around a gate: no error | check |
| 9 | the IDLE postamble is delivered as a word | check |
| 10 | gate after a non-IDLE word: postamble error | check |
| 11 | first word after a gate not IDLE (AUX set): preamble error | check |
| 12 | clock stopped after 2 UI of a word: error 2 | check |
| 13 | the next words start at a word boundary again | check |
| 14 | clock gated high (mid-word): errors 3 and 2 | check |
| 15 | 512 UI gated: no error | check |
| 16 | 513th gated UI: error 0, one clock later | check |
| 17 | error 0 once per gate | check |
| 18 | training ignores the defective lines | check |
| 19 | D4, D6 defective: logical D[4:0] on {D[3:0], AUX}, D[15:6] on {FEC, D[15:7]} | check |
| 20 | redundancy on: PAUX / PFEC are 0 | check |
| 21 | AUX carries logical D0, FEC D15, physical D5 / D3 carry D5 / D4 | check |
| 22 | D10 defective: D10 on physical D9, D11 stays | check |
| 23 | AUX and FEC defective: no shift | check |
| 24 | AUX and D3 defective: D3 on D4 ... D15 on FEC | check |
| 25 | FEC alone defective: no shift | check |
| 26 | AUX alone defective (second defect field): no shift | check |
| 27 | redundancy on: noise on the line in bad_a is ignored in training | check |
| 28 | redundancy off: bad_a is ignored, the noisy line keeps PHYReady low | check |
| 29 | PRBS-9 (x^9 + x^5 + 1) on 16 lanes: no error | check |
| 30 | one flipped bit: PRBS error | check |
| 31 | no PRBS check before 9 UI of data | check |
| 32 | checker off: no PRBS error | check |
| 33 | PHYResetB low: PHYReady low on the next clock | check |
| 34 | after reset no words until retrained | check |

## 3. UVM 測試平台內容

UVM agent test（`bow_func_test`：directed + constrained-random 流量，scoreboard 以 DUT 模型的參考模型逐筆比對，並比對 driver 與 monitor 的 transaction）在 Verilator 上以 `python3 tools/run_uvm_tests.py BoW-UVM-VIP` 執行；agent 由 `tools/gen_uvm_agents.py` 依 `tools/uvm_agents/` 的協定 spec 產生。

| 項目 | 數量 | 名稱 |
|---|---|---|
| UVM tests | 2 | `bow_base_test`, `bow_func_test` |
| Sequences | 3 | `bow_base_sequence`, `bow_directed_sequence`, `bow_transaction` |
| SVA（assert / cover property） | 6 / 7 | - |
| Covergroups / coverpoints | 1 / 9 | |

## 4. 充分度判定與缺口

判定：**✅ Sufficient**（34 個 check，mutation score 100%）。

無已知缺口。

