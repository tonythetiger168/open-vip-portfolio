# DDR5 測試套件（DDR5-VIP）

> 由 `tools/gen_test_suite_docs.py` 依 VIP 內容、`func_report.csv` 與 `mutation_report.csv` 自動產生，請勿手動修改。

## 1. 概要

| 項目 | 內容 |
|---|---|
| 類別 | Memory |
| 類型 | UVM VIP |
| 功能測試 | 3 個檔案，103 個 check，全部通過 |
| Mutation | 33/33 個 mutant 被偵測（100%） |
| 判定 | **✅ Sufficient**（103 個 check，mutation score 100%） |

## 2. 可執行的功能測試

執行：`python3 tools/run_func_tests.py DDR5-VIP`（Icarus Verilog 或 Verilator 5.052）。

### `ddr5_dev/tb/func_ddr5_dev_tb.sv`

結果：**PASS**（verilator，80 checks）

模型合約與範圍（摘自測試檔頭）：

```text
FUNC_SIM: verilator

func_ddr5_dev_tb.sv -- memory controller for ddr5_dev_model, written from
the JESD79-5 rules rather than from the model:
   * every timing parameter at its boundary: one clock early is rejected
     with the matching error and has no effect, on time is accepted
     (tRCD, tRAS, tRP, tRRD_S/L, tFAW, tCCD_S/L, tRTP, tWR, tWTR_S/L,
     RD->WR turnaround, tRFC, tMRD)
   * bank state: ACT to an open bank, RD / WR to an idle bank, PREpb to
     an idle bank (no-op), PREab, auto precharge timing of RDA / WRA
   * RL / CWL from MR0 (CL 22 and CL 28), MRR data and latency, illegal
     burst length, column alignment, missing write data
   * refresh: REF with a bank open, tRFC, postponed refresh limit
   * 300 random commands from a timing-legal scheduler against a
     reference memory (data and latency of every burst)
Run: python3 tools/run_func_tests.py DDR5-VIP
```

| # | Check | 類型 |
|---|---|---|
| 1 | %s: one clock early rejected (err=%h) | check |
| 2 | %s: on time accepted (err=%h) | check |
| 3 | MRR MR0 accepted | check |
| 4 | command inside tMRR rejected | check |
| 5 | MRW MR10 after tMRR accepted | check |
| 6 | MRR inside tMRD rejected | check |
| 7 | MRR MR10 accepted | check |
| 8 | MR0 burst length BC8 rejected (only BL16 modelled) | check |
| 9 | MRR data at RL=22 (cnt %0d bad %0d) | check |
| 10 | ACT bank 0.1 opens it | check |
| 11 | ACT to an open bank rejected | check |
| 12 | column not BL16-aligned rejected | check |
| 13 | RD to an idle bank rejected | check |
| 14 | PRE inside tWR rejected, bank stays open | check |
| 15 | PRE after tWR closes the bank | check |
| 16 | RD of the reopened row | check |
| 17 | PREpb to an idle bank is a no-op | check |
| 18 | burst data and RL (cnt %0d bad %0d extra %0d) | check |
| 19 | four banks open | check |
| 20 | fifth ACT inside tFAW rejected | check |
| 21 | fifth ACT at tFAW accepted | check |
| 22 | PRE inside tRAS rejected | check |
| 23 | PRE at tRAS accepted | check |
| 24 | RD same group inside tWTR_L rejected (err=%h) | check |
| 25 | RD other group inside tWTR_S rejected (err=%h) | check |
| 26 | RD other group at tWTR_S accepted (err=%h) | check |
| 27 | REFab with banks open rejected | check |
| 28 | MRW with banks open rejected | check |
| 29 | PREab closes all banks | check |
| 30 | RDA accepted | check |
| 31 | PRE to a bank with auto precharge pending rejected | check |
| 32 | bank open until ACT + tRAS | check |
| 33 | auto precharge after RDA | check |
| 34 | ACT inside tRP of the auto precharge rejected | check |
| 35 | ACT at tRP after auto precharge | check |
| 36 | bank open until write recovery ends | check |
| 37 | auto precharge after WRA + CWL + 8 + tWR | check |
| 38 | MRW MR0 CL code 3 | check |
| 39 | WR / RD at CL 28 | check |
| 40 | RD to a bank closed by WRA rejected | check |
| 41 | bursts at CL 22 and CL 28 (bad %0d extra %0d) | check |
| 42 | write data missing flagged | check |
| 43 | reserved command rejected | check |
| 44 | 300 legal random commands raise no error (%0d) | check |
| 45 | random traffic read data and latency (reads %0d bad %0d extra %0d) | check |
| 46 | PREab inside tRTP of a read rejected, banks stay open | check |
| 47 | MRR inside tCCD_S of a read rejected | check |
| 48 | MRR at tCCD_S accepted | check |
| 49 | WR after the MRR turnaround | check |
| 50 | PREab inside tWR of a write rejected, banks stay open | check |
| 51 | RDA accepted | check |
| 52 | PREab with an auto precharge pending rejected | check |
| 53 | PREab after the auto precharge closes the rest | check |
| 54 | MRR data and reads around the PREab checks | check |
| 55 | REFab after PREab | check |
| 56 | refreshes pulled in delay the overdue flag by REF_POSTPONE intervals | check |
| 57 | postponed refresh limit flagged once (%0d) | check |
| 58 | reset drops every read in flight (%0d bursts issued, %0d beats after reset) | check |

### `tb/func_ddr5_tb.sv`

結果：**PASS**（iverilog，14 checks）

模型合約與範圍（摘自測試檔頭）：

```text
func_ddr5_tb.sv -- pipelined-read memory functional test for the DDR5
model (ddr5_model, flattened by smoke/flatten.py); complements smoke_func_tb.sv
(single write / read per bank).
Run: python3 tools/run_func_tests.py DDR5-VIP

Model contract (from tb/top_tb.sv): a command is issued when cs_n = 0 and
act_n = 1; addr[0] = 0 writes wr_data to word addr[13:1] of bank[1:0],
addr[0] = 1 reads it. Read data return with a one-clock rd_valid pulse
5 clocks after the command (fully pipelined, one read per clock);
rd_data holds the last read value. Unwritten words read 0.
Checked against a reference memory with 600 random commands.

Not modelled (limitations, not tested): ACT/PRE/REF timing, bank
state, burst length and the real DDR5 command encoding.
```

| # | Check | 類型 |
|---|---|---|
| 1 | reset: rd_valid low, rd_data 0 | check |
| 2 | no rd_valid after reset release without a read | check |
| 3 | unwritten words read 0 (first, last, odd words of each bank) | check |
| 4 | read data valid exactly 5 clocks after the read command | check |
| 5 | read right after a write returns the new data | check |
| 6 | same word in each bank is independent | check |
| 7 | 24 back-to-back reads: data in order, fixed latency | check |
| 8 | rd_data holds the last read value while idle | check |
| 9 | read with cs_n high or act_n low returns nothing | check |
| 10 | write with cs_n high or act_n low is ignored | check |
| 11 | 600 random writes / reads match the reference memory | check |
| 12 | reset clears rd_valid and rd_data | check |
| 13 | reads in flight at reset return nothing | check |
| 14 | memory contents survive reset | check |

### `tb/smoke_func_tb.sv`

結果：**PASS**（iverilog，9 checks）

| # | Check | 類型 |
|---|---|---|
| 1 | rd_valid quiet in reset | check |
| 2 | read latency respected | check |
| 3 | rd_valid after RL | check |
| 4 | read data matches write | check |
| 5 | rd_valid is a pulse | check |
| 6 | second address data | check |
| 7 | bank isolation | check |

## 3. UVM 測試平台內容

UVM agent test（`ddr5_func_test`：directed + constrained-random 流量，scoreboard 以 DUT 模型的參考模型逐筆比對，並比對 driver 與 monitor 的 transaction）在 Verilator 上以 `python3 tools/run_uvm_tests.py DDR5-VIP` 執行；agent 由 `tools/gen_uvm_agents.py` 依 `tools/uvm_agents/` 的協定 spec 產生。

| 項目 | 數量 | 名稱 |
|---|---|---|
| UVM tests | 2 | `ddr5_base_test`, `ddr5_func_test` |
| Sequences | 3 | `ddr5_base_sequence`, `ddr5_directed_sequence`, `ddr5_transaction` |
| SVA（assert / cover property） | 4 / 2 | - |
| Covergroups / coverpoints | 1 / 3 | |

## 4. 充分度判定與缺口

判定：**✅ Sufficient**（103 個 check，mutation score 100%）。

模型未實作的功能（不在測試範圍）：

- Not modelled (limitations, not tested): ACT/PRE/REF timing, bank state, burst length and the real DDR5 command encoding.

