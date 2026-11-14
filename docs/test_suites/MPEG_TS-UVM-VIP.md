# MPEG-2 TS / TSI (ISO/IEC 13818-1) 測試套件（MPEG_TS-UVM-VIP）

> 由 `tools/gen_test_suite_docs.py` 依 VIP 內容、`func_report.csv` 與 `mutation_report.csv` 自動產生，請勿手動修改。

## 1. 概要

| 項目 | 內容 |
|---|---|
| 類別 | Video |
| 類型 | UVM VIP |
| 功能測試 | 1 個檔案，29 個 check，全部通過 |
| Mutation | 27/27 個 mutant 被偵測（100%） |
| 判定 | **✅ Sufficient**（29 個 check，mutation score 100%） |

## 2. 可執行的功能測試

執行：`python3 tools/run_func_tests.py MPEG_TS-UVM-VIP`（Icarus Verilog 或 Verilator 5.054）。

### `tb/smoke_func_tb.sv`

結果：**PASS**（iverilog，29 checks）

模型合約與範圍（摘自測試檔頭）：

```text
Functional smoke testbench (TSI DUT model)
```

| # | Check | 類型 |
|---|---|---|
| 1 | nothing out in reset | check |
| 2 | nothing out after reset without input | check |
| 3 | PAT, first packet: any CC, 184 bytes | check |
| 4 | CC + 1 with ts_valid gaps | check |
| 5 | adaptation length 0 | check |
| 6 | adaptation length 182 | check |
| 7 | same CC: duplicate dropped | check |
| 8 | then CC + 1 | check |
| 9 | CC 9 after 2: discontinuity, delivered | check |
| 10 | tracking restarted at 9 | check |
| 11 | discontinuity_indicator: any CC | check |
| 12 | duplicate with an adaptation field (no discontinuity flag) | check |
| 13 | adaptation only: no payload | check |
| 14 | control 10 with length 100 | check |
| 15 | control 11 with length 183 | check |
| 16 | control 00 | check |
| 17 | TEI set: dropped | check |
| 18 | ts_err on byte 77: dropped | check |
| 19 | sync byte 0x46 | check |
| 20 | cut after 100 bytes: timeout | check |
| 21 | null packet | check |
| 22 | PID not filtered | check |
| 23 | PID 0x101 first packet after the faults | check |
| 24 | PID 0x111 CC 15 | check |
| 25 | CC wraps 15 -> 0 | check |
| 26 | 50-byte packet | check |
| 27 | PAT CC 7 | check |
| 28 | out_last only on the last payload byte, with the report | check |
| 29 | one out_last per delivered packet (%0d) | check |

## 3. UVM 測試平台內容

UVM agent test（`tsi_func_test`：directed + constrained-random 流量，scoreboard 以 DUT 模型的參考模型逐筆比對，並比對 driver 與 monitor 的 transaction）在 Verilator 上以 `python3 tools/run_uvm_tests.py MPEG_TS-UVM-VIP` 執行；agent 由 `tools/gen_uvm_agents.py` 依 `tools/uvm_agents/` 的協定 spec 產生。

| 項目 | 數量 | 名稱 |
|---|---|---|
| UVM tests | 2 | `tsi_base_test`, `tsi_func_test` |
| Sequences | 3 | `tsi_base_sequence`, `tsi_directed_sequence`, `tsi_transaction` |
| SVA（assert / cover property） | 5 / 2 | - |
| Covergroups / coverpoints | 1 / 3 | |

## 4. 充分度判定與缺口

判定：**✅ Sufficient**（29 個 check，mutation score 100%）。

無已知缺口。

