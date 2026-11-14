# ISO 7816-3 smartcard (T = 0, PPS) 測試套件（Smartcard_ISO7816-UVM-VIP）

> 由 `tools/gen_test_suite_docs.py` 依 VIP 內容、`func_report.csv` 與 `mutation_report.csv` 自動產生，請勿手動修改。

## 1. 概要

| 項目 | 內容 |
|---|---|
| 類別 | Security |
| 類型 | UVM VIP |
| 功能測試 | 1 個檔案，34 個 check，全部通過 |
| Mutation | 30/30 個 mutant 被偵測（100%） |
| 判定 | **✅ Sufficient**（34 個 check，mutation score 100%） |

## 2. 可執行的功能測試

執行：`python3 tools/run_func_tests.py Smartcard_ISO7816-UVM-VIP`（Icarus Verilog 或 Verilator 5.054）。

### `tb/smoke_func_tb.sv`

結果：**PASS**（verilator，34 checks）

模型合約與範圍（摘自測試檔頭）：

```text
Functional smoke testbench (SCD DUT model)
```

| # | Check | 類型 |
|---|---|---|
| 1 | card off I/O in reset | check |
| 2 | no RST yet: the card stays off | check |
| 3 | RST low: the card stays silent | check |
| 4 | ATR 3B 02 53 43 | check |
| 5 | ATR starts 400 clocks after RST | check |
| 6 | ATR characters 12 etu apart | check |
| 7 | PPS 372 / 8: no answer | check |
| 8 | PPS with a bad PCK: no answer | check |
| 9 | PPS 94 echoed | check |
| 10 | after a PPS no second PPS: 6E 00 | check |
| 11 | READ BINARY at the new etu: B0, data, 90 00 | check |
| 12 | card answers 16 etu after the last leading edge | check |
| 13 | after the first exchange FF is a class byte: 6E 00 | check |
| 14 | UPDATE BINARY: procedure byte D6 | check |
| 15 | UPDATE: 90 00 | check |
| 16 | read-back | check |
| 17 | past the end: 6B 00 | check |
| 18 | up to the last byte | check |
| 19 | P1 = 1: 6B 00 | check |
| 20 | CLA 80: 6E 00 | check |
| 21 | INS CA: 6D 00 | check |
| 22 | bad parity: error signal, the repeat is taken | check |
| 23 | a refused character is sent again | check |
| 24 | and the response goes on | check |
| 25 | after 4 refused tries the card gives up | check |
| 26 | and takes the next command | check |
| 27 | P3 = 0 reads all 256 bytes | check |
| 28 | RST: off I/O | check |
| 29 | ATR again at 372 | check |
| 30 | PPS 13: 372 / 4 | check |
| 31 | data kept across RST, etu 93 | check |
| 32 | PPS without PPS1 echoed | check |
| 33 | still 372 | check |
| 34 | parity error on the first byte | check |

## 3. UVM 測試平台內容

UVM agent test（`scd_func_test`：directed + constrained-random 流量，scoreboard 以 DUT 模型的參考模型逐筆比對，並比對 driver 與 monitor 的 transaction）在 Verilator 上以 `python3 tools/run_uvm_tests.py Smartcard_ISO7816-UVM-VIP` 執行；agent 由 `tools/gen_uvm_agents.py` 依 `tools/uvm_agents/` 的協定 spec 產生。

| 項目 | 數量 | 名稱 |
|---|---|---|
| UVM tests | 2 | `scd_base_test`, `scd_func_test` |
| Sequences | 3 | `scd_base_sequence`, `scd_directed_sequence`, `scd_transaction` |
| SVA（assert / cover property） | 2 / 1 | - |
| Covergroups / coverpoints | 1 / 2 | |

## 4. 充分度判定與缺口

判定：**✅ Sufficient**（34 個 check，mutation score 100%）。

無已知缺口。

