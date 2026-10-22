# Avalon-ST 測試套件（Avalon_ST-UVM-VIP）

> 由 `tools/gen_test_suite_docs.py` 依 VIP 內容、`func_report.csv` 與 `mutation_report.csv` 自動產生，請勿手動修改。

## 1. 概要

| 項目 | 內容 |
|---|---|
| 類別 | Interconnect |
| 類型 | UVM VIP |
| 功能測試 | 2 個檔案，28 個 check，全部通過 |
| Mutation | 7/7 個 mutant 被偵測（100%） |
| 判定 | **✅ Sufficient**（28 個 check，mutation score 100%） |

## 2. 可執行的功能測試

執行：`python3 tools/run_func_tests.py Avalon_ST-UVM-VIP`（Icarus Verilog 或 Verilator 5.052）。

### `tb/func_avalon_st_tb.sv`

結果：**PASS**（iverilog，9 checks）

模型合約與範圍（摘自測試檔頭）：

```text
func_avalon_st_tb.sv -- Avalon-ST streaming functional test for the
pass-through model (avalon_st_model, flattened by smoke/flatten.py);
complements smoke_func_tb.sv (one 4-beat packet).
Run: python3 tools/run_func_tests.py Avalon_ST-UVM-VIP

Model contract (from tb/top_tb.sv): sink ready (asi_ready) rises one
clock after reset; every accepted beat (asi_valid && asi_ready) appears
on the source one clock later with its startofpacket / endofpacket.
Checked with 200 random packets (1..16 beats) and random valid gaps,
and reset in the middle of a packet.

Model defect (XFAIL): aso_ready is ignored (readyLatency 0 requires the
source to hold a beat until ready), and asi_ready never drops, so
back-pressure loses data.
```

| # | Check | 類型 |
|---|---|---|
| 1 | reset: sink not ready, source idle, SOP / EOP / data 0 | check |
| 2 | asi_ready still low right after reset release | check |
| 3 | asi_ready one clock after reset release | check |
| 4 | 200 random packets: every beat, SOP and EOP passed through in order | check |
| 5 | one clock latency, no beat while the sink is idle | check |
| 6 | source valid low after the last beat | check |
| 7 | single-beat packet: SOP and EOP together | check |
| 8 | reset clears the source and sink ready | check |
| 9 | beats held while aso_ready is low (no data lost) | XFAIL（模型缺陷） |

### `tb/smoke_func_tb.sv`

結果：**PASS**（iverilog，19 checks）

| # | Check | 類型 |
|---|---|---|
| 1 | source valid reset low | check |
| 2 | sink ready asserted after reset | check |
| 3 | source valid during packet | check |
| 4 | packet data integrity | check |
| 5 | SOP only on first beat | check |
| 6 | EOP only on last beat | check |
| 7 | source idle after packet | check |

## 3. UVM 測試平台內容

UVM 測試需商用模擬器（VCS / Xcelium / Questa）執行；開源流程只做 elaboration（L1a）。

| 項目 | 數量 | 名稱 |
|---|---|---|
| UVM tests | 1 | `avalon_st_base_test` |
| Sequences | 2 | `avalon_st_base_sequence`, `avalon_st_transaction` |
| SVA（assert / cover property） | 3 / 2 | - |
| Covergroups / coverpoints | 1 / 5 | |

## 4. 充分度判定與缺口

判定：**✅ Sufficient**（28 個 check，mutation score 100%）。

DUT 模型缺陷（XFAIL check，修好模型後會變成 XPASS 提醒移除標記）：

- beats held while aso_ready is low (no data lost)

