# Avalon-ST 測試套件（Avalon_ST-UVM-VIP）

> 由 `tools/gen_test_suite_docs.py` 依 VIP 內容、`func_report.csv` 與 `mutation_report.csv` 自動產生，請勿手動修改。

## 1. 概要

| 項目 | 內容 |
|---|---|
| 類別 | Interconnect |
| 類型 | UVM VIP |
| 功能測試 | 2 個檔案，31 個 check，全部通過 |
| Mutation | 17/17 個 mutant 被偵測（100%） |
| 判定 | **✅ Sufficient**（31 個 check，mutation score 100%） |

## 2. 可執行的功能測試

執行：`python3 tools/run_func_tests.py Avalon_ST-UVM-VIP`（Icarus Verilog 或 Verilator 5.052）。

### `tb/func_avalon_st_tb.sv`

結果：**PASS**（iverilog，12 checks）

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
and reset in the middle of a packet. Downstream back-pressure: the source
holds a beat while aso_ready is low, a one-beat skid buffer absorbs the
beat in flight, and asi_ready drops while it is full.

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
| 9 | beats held while aso_ready is low (no data lost) | check |
| 10 | asi_ready drops while the skid buffer is full | check |
| 11 | pipeline drained and sink ready again after back-pressure | check |
| 12 | random back-pressure with input gaps: %0d of %0d beats in order, none extra | check |

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

UVM agent test（`avalon_st_func_test`：directed + constrained-random 流量，scoreboard 以 DUT 模型的參考模型逐筆比對，並比對 driver 與 monitor 的 transaction）在 Verilator 上以 `python3 tools/run_uvm_tests.py Avalon_ST-UVM-VIP` 執行；agent 由 `tools/gen_uvm_agents.py` 依 `tools/uvm_agents/` 的協定 spec 產生。

| 項目 | 數量 | 名稱 |
|---|---|---|
| UVM tests | 2 | `avalon_st_base_test`, `avalon_st_func_test` |
| Sequences | 3 | `avalon_st_base_sequence`, `avalon_st_directed_sequence`, `avalon_st_transaction` |
| SVA（assert / cover property） | 3 / 2 | - |
| Covergroups / coverpoints | 1 / 1 | |

## 4. 充分度判定與缺口

判定：**✅ Sufficient**（31 個 check，mutation score 100%）。

無已知缺口。

