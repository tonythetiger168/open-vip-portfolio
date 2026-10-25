# HBM3E 測試套件（HBM3E-VIP）

> 由 `tools/gen_test_suite_docs.py` 依 VIP 內容、`func_report.csv` 與 `mutation_report.csv` 自動產生，請勿手動修改。

## 1. 概要

| 項目 | 內容 |
|---|---|
| 類別 | Memory |
| 類型 | UVM VIP |
| 功能測試 | 2 個檔案，20 個 check，全部通過 |
| Mutation | 18/18 個 mutant 被偵測（100%） |
| 判定 | **✅ Sufficient**（20 個 check，mutation score 100%） |

## 2. 可執行的功能測試

執行：`python3 tools/run_func_tests.py HBM3E-VIP`（Icarus Verilog 或 Verilator 5.052）。

### `tb/func_hbm3e_tb.sv`

結果：**PASS**（iverilog，14 checks）

模型合約與範圍（摘自測試檔頭）：

```text
func_hbm3e_tb.sv -- pipelined-read memory functional test for the HBM3E
model (hbm3e_model, flattened by smoke/flatten.py); complements smoke_func_tb.sv
(single write / read per stack / pseudo channel).
Run: python3 tools/run_func_tests.py HBM3E-VIP

Model contract (from tb/top_tb.sv): a command is issued when cs_n = 0 and
act_n = 1; addr[0] = 0 writes wr_data to word addr[13:1] of stack[1:0] / pseudo channel pchan,
addr[0] = 1 reads it. Read data return with a one-clock rd_valid pulse
4 clocks after the command (fully pipelined, one read per clock);
rd_data holds the last read value. Unwritten words read 0.
Checked against a reference memory with 600 random commands.

Not modelled (limitations, not tested): ACT/PRE/REF timing, bank
state, burst length and the real HBM3E command encoding.
```

| # | Check | 類型 |
|---|---|---|
| 1 | reset: rd_valid low, rd_data 0 | check |
| 2 | no rd_valid after reset release without a read | check |
| 3 | unwritten words read 0 (first, last, odd words of each stack / pseudo channel) | check |
| 4 | read data valid exactly 4 clocks after the read command | check |
| 5 | read right after a write returns the new data | check |
| 6 | same word in each stack / pseudo channel is independent | check |
| 7 | 24 back-to-back reads: data in order, fixed latency | check |
| 8 | rd_data holds the last read value while idle | check |
| 9 | read with cs_n high or act_n low returns nothing | check |
| 10 | write with cs_n high or act_n low is ignored | check |
| 11 | 600 random writes / reads match the reference memory | check |
| 12 | reset clears rd_valid and rd_data | check |
| 13 | reads in flight at reset return nothing | check |
| 14 | memory contents survive reset | check |

### `tb/smoke_func_tb.sv`

結果：**PASS**（iverilog，6 checks）

| # | Check | 類型 |
|---|---|---|
| 1 | rd_valid quiet in reset | check |
| 2 | read latency respected | check |
| 3 | pchan0 data | check |
| 4 | pchan1 data independent | check |
| 5 | rd_valid is a pulse | check |

## 3. UVM 測試平台內容

UVM 測試需商用模擬器（VCS / Xcelium / Questa）執行；開源流程只做 elaboration（L1a）。

| 項目 | 數量 | 名稱 |
|---|---|---|
| UVM tests | 1 | `hbm3e_base_test` |
| Sequences | 2 | `hbm3e_base_sequence`, `hbm3e_transaction` |
| SVA（assert / cover property） | 3 / 2 | - |
| Covergroups / coverpoints | 1 / 6 | |

## 4. 充分度判定與缺口

判定：**✅ Sufficient**（20 個 check，mutation score 100%）。

模型未實作的功能（不在測試範圍）：

- Not modelled (limitations, not tested): ACT/PRE/REF timing, bank state, burst length and the real HBM3E command encoding.

