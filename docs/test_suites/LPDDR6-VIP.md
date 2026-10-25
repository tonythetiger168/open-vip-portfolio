# LPDDR6 測試套件（LPDDR6-VIP）

> 由 `tools/gen_test_suite_docs.py` 依 VIP 內容、`func_report.csv` 與 `mutation_report.csv` 自動產生，請勿手動修改。

## 1. 概要

| 項目 | 內容 |
|---|---|
| 類別 | Memory |
| 類型 | UVM VIP |
| 功能測試 | 2 個檔案，36 個 check，全部通過 |
| Mutation | 21/21 個 mutant 被偵測（100%） |
| 判定 | **✅ Sufficient**（36 個 check，mutation score 100%） |

## 2. 可執行的功能測試

執行：`python3 tools/run_func_tests.py LPDDR6-VIP`（Icarus Verilog 或 Verilator 5.052）。

### `tb/func_lpddr6_tb.sv`

結果：**PASS**（iverilog，16 checks）

模型合約與範圍（摘自測試檔頭）：

```text
func_lpddr6_tb.sv -- pipelined-read memory functional test for the LPDDR6
model (lpddr6_model, flattened by smoke/flatten.py); complements smoke_func_tb.sv
(single write / read per bank).
Run: python3 tools/run_func_tests.py LPDDR6-VIP

Model contract (from tb/top_tb.sv): a command is issued when cs_n = 0 and
act_n = 1; addr[0] = 0 writes wr_data to word addr[13:1] of bank[1:0],
addr[0] = 1 reads it. Read data return with a one-clock rd_valid pulse
7 clocks after the command (fully pipelined, one read per clock);
rd_data holds the last read value. Unwritten words read 0.
While self_ref is high commands are ignored and reads in flight are
dropped.
Checked against a reference memory with 600 random commands.

Not modelled (limitations, not tested): ACT/PRE/REF timing, bank
state, burst length and the real LPDDR6 command encoding.
```

| # | Check | 類型 |
|---|---|---|
| 1 | reset: rd_valid low, rd_data 0 | check |
| 2 | no rd_valid after reset release without a read | check |
| 3 | unwritten words read 0 (first, last, odd words of each bank) | check |
| 4 | read data valid exactly 7 clocks after the read command | check |
| 5 | read right after a write returns the new data | check |
| 6 | same word in each bank is independent | check |
| 7 | 24 back-to-back reads: data in order, fixed latency | check |
| 8 | rd_data holds the last read value while idle | check |
| 9 | read with cs_n high or act_n low returns nothing | check |
| 10 | write with cs_n high or act_n low is ignored | check |
| 11 | 600 random writes / reads match the reference memory | check |
| 12 | self refresh: no read data, reads in flight dropped | check |
| 13 | write during self refresh ignored, memory retained | check |
| 14 | reset clears rd_valid and rd_data | check |
| 15 | reads in flight at reset return nothing | check |
| 16 | memory contents survive reset | check |

### `tb/smoke_func_tb.sv`

結果：**PASS**（iverilog，20 checks）

| # | Check | 類型 |
|---|---|---|
| 1 | rd_valid quiet in reset | check |
| 2 | read latency respected | check |
| 3 | rd_valid after RL | check |
| 4 | read data matches write | check |
| 5 | rd_valid is a pulse | check |
| 6 | no rd_valid in self-refresh | check |
| 7 | data survives self-refresh | check |

## 3. UVM 測試平台內容

UVM agent test（`lpddr6_func_test`：directed + constrained-random 流量，scoreboard 以 DUT 模型的參考模型逐筆比對，並比對 driver 與 monitor 的 transaction）在 Verilator 上以 `python3 tools/run_uvm_tests.py LPDDR6-VIP` 執行；agent 由 `tools/gen_uvm_agents.py` 依 `tools/uvm_agents/` 的協定 spec 產生。

| 項目 | 數量 | 名稱 |
|---|---|---|
| UVM tests | 2 | `lpddr6_base_test`, `lpddr6_func_test` |
| Sequences | 3 | `lpddr6_base_sequence`, `lpddr6_directed_sequence`, `lpddr6_transaction` |
| SVA（assert / cover property） | 4 / 2 | - |
| Covergroups / coverpoints | 1 / 4 | |

## 4. 充分度判定與缺口

判定：**✅ Sufficient**（36 個 check，mutation score 100%）。

模型未實作的功能（不在測試範圍）：

- Not modelled (limitations, not tested): ACT/PRE/REF timing, bank state, burst length and the real LPDDR6 command encoding.

