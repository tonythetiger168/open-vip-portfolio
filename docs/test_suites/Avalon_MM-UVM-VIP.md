# Avalon-MM 測試套件（Avalon_MM-UVM-VIP）

> 由 `tools/gen_test_suite_docs.py` 依 VIP 內容、`func_report.csv` 與 `mutation_report.csv` 自動產生，請勿手動修改。

## 1. 概要

| 項目 | 內容 |
|---|---|
| 類別 | Interconnect |
| 類型 | UVM VIP |
| 功能測試 | 1 個檔案，70 個 check，全部通過 |
| Mutation | 27/27 個 mutant 被偵測（100%） |
| 判定 | **✅ Sufficient**（70 個 check，mutation score 100%） |

## 2. 可執行的功能測試

執行：`python3 tools/run_func_tests.py Avalon_MM-UVM-VIP`（Icarus Verilog 或 Verilator 5.054）。

### `tb/smoke_func_tb.sv`

結果：**PASS**（iverilog，70 checks）

模型合約與範圍（摘自測試檔頭）：

```text
Functional smoke testbench (Avalon-MM DUT model)
```

| # | Check | 類型 |
|---|---|---|
| 1 | %0d responses arrived | check |
| 2 | idle in reset | check |
| 3 | no waitrequest in reset | check |
| 4 | no waitrequest without a command | check |
| 5 | write response OKAY | check |
| 6 | read back the word | check |
| 7 | neighbour word still 0 | check |
| 8 | byte-enable merge, no-byte write ignored (%h) | check |
| 9 | lanes 0 and 2 | check |
| 10 | one write response for the 8-beat burst | check |
| 11 | 8 read beats, sequential words | check |
| 12 | 3-beat burst from the middle | check |
| 13 | last word of the burst | check |
| 14 | word after the burst untouched | check |
| 15 | per-beat byteenable | check |
| 16 | burstcount 0 write: one beat, one response | check |
| 17 | burstcount 0 read: one beat | check |
| 18 | 0x3FC is memory | check |
| 19 | 0x400..0x7FF: SLVERR, data 0 | check |
| 20 | 0x800..0xFFF: DECODEERROR | check |
| 21 | write responses SLVERR / DECODEERROR | check |
| 22 | an error-region write lands nowhere (0x400 does not alias 0x000) | check |
| 23 | write burst into SLVERR: first error response | check |
| 24 | read burst into SLVERR: in-range beats OKAY, the rest SLVERR | check |
| 25 | SLVERR beat then DECODEERROR beat | check |
| 26 | SLVERR, SLVERR, DECODEERROR, DECODEERROR: the first error is reported | check |
| 27 | write wrapping 0xFFC -> 0x000: first beat DECODEERROR | check |
| 28 | the wrapped beat lands at 0x000 | check |
| 29 | a fifth read waits for the first burst (%0d, %0d) | check |
| 30 | five bursts of 8 beats | check |
| 31 | write waits while a read is pending | check |
| 32 | the write is accepted only after the 8 read beats (%0d) | check |
| 33 | read returned the old word | check |
| 34 | the write landed after the read | check |
| 35 | wait states %0d for %0d accepted beats | check |
| 36 | reset clears the responses | check |
| 37 | reset clears the memory | check |
| 38 | a new burst after reset starts at beat 0 | check |
| 39 | burst after reset at the right words | check |

## 3. UVM 測試平台內容

UVM agent test（`avalon_mm_func_test`：directed + constrained-random 流量，scoreboard 以 DUT 模型的參考模型逐筆比對，並比對 driver 與 monitor 的 transaction）在 Verilator 上以 `python3 tools/run_uvm_tests.py Avalon_MM-UVM-VIP` 執行；agent 由 `tools/gen_uvm_agents.py` 依 `tools/uvm_agents/` 的協定 spec 產生。

| 項目 | 數量 | 名稱 |
|---|---|---|
| UVM tests | 3 | `avalon_mm_base_test`, `avalon_mm_func_test`, `avalon_mm_ral_test` |
| Sequences | 3 | `avalon_mm_base_sequence`, `avalon_mm_directed_sequence`, `avalon_mm_transaction` |
| SVA（assert / cover property） | 8 / 3 | - |
| Covergroups / coverpoints | 1 / 10 | |

## 4. 充分度判定與缺口

判定：**✅ Sufficient**（70 個 check，mutation score 100%）。

無已知缺口。

