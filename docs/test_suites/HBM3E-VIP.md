# HBM3E 測試套件（HBM3E-VIP）

> 由 `tools/gen_test_suite_docs.py` 依 VIP 內容、`func_report.csv` 與 `mutation_report.csv` 自動產生，請勿手動修改。

## 1. 概要

| 項目 | 內容 |
|---|---|
| 類別 | Memory |
| 類型 | UVM VIP |
| 功能測試 | 3 個檔案，116 個 check，全部通過 |
| Mutation | 9/9 個 mutant 被偵測（100%） |
| 判定 | **✅ Sufficient**（116 個 check，mutation score 100%） |

## 2. 可執行的功能測試

執行：`python3 tools/run_func_tests.py HBM3E-VIP`（Icarus Verilog 或 Verilator 5.052）。

### `hbm_dev/tb/func_hbm_dev_tb.sv`

結果：**PASS**（verilator，96 checks）

模型合約與範圍（摘自測試檔頭）：

```text
FUNC_SIM: verilator

func_hbm_dev_tb.sv -- memory controller for hbm_dev_model, written from
the JESD238 pseudo-channel rules rather than from the model:
   * timing boundaries, one clock early rejected with the matching cause
     and no effect, on time accepted: tRCDRD, tRCDWR, tRAS, tRP, tRRD_S/L,
     tFAW, tCCD_S/L, tRTP, tWR, tWTR_S/L, RD->WR turnaround, tRFCab,
     tRFCpb, tRREFD, tMOD
   * row and column commands in the same clock; pseudo channels with
     their own banks, tFAW, refresh and latencies
   * REFpb (bank must be idle, only that bank busy), REFab, PREab,
     RDA / WRA auto precharge, MRS rules, missing write data
   * refresh credit: REFab or 16 REFpb per tREFI, postponed limit
   * 400 random commands on both buses from a timing-legal scheduler
     against a reference memory
Run: python3 tools/run_func_tests.py HBM3E-VIP
```

| # | Check | 類型 |
|---|---|---|
| 1 | ACT pc0 bank 0 | check |
| 2 | RD inside tRCDRD rejected | check |
| 3 | RD at tRCDRD accepted | check |
| 4 | WR inside the RD->WR turnaround rejected | check |
| 5 | WR at RL + 4 + 2 - WL accepted | check |
| 6 | RD inside tWTR_L rejected | check |
| 7 | RD at tWTR_L accepted | check |
| 8 | ACT pc0 bank group 1 | check |
| 9 | WR inside tRCDWR rejected | check |
| 10 | WR at tRCDWR accepted | check |
| 11 | WR other bank group inside tCCD_S rejected | check |
| 12 | WR other bank group at tCCD_S accepted | check |
| 13 | WR same bank group inside tCCD_L rejected | check |
| 14 | WR same bank group at tCCD_L accepted | check |
| 15 | PRE inside tWR rejected | check |
| 16 | PRE at tWR closes the bank | check |
| 17 | ACT inside tRP rejected | check |
| 18 | ACT at tRP accepted | check |
| 19 | PRE inside tRAS rejected | check |
| 20 | PRE at tRAS accepted | check |
| 21 | RD bank group 1 | check |
| 22 | PRE inside tRTP rejected | check |
| 23 | PRE at tRTP accepted | check |
| 24 | PRE to an idle bank is a no-op | check |
| 25 | RD to an idle bank rejected | check |
| 26 | no write data missing so far | check |
| 27 | read data and latency RL 20 (cnt %0d bad %0d extra %0d) | check |
| 28 | ACT and WR in the same clock both accepted | check |
| 29 | ACT to the bank opened on the row bus rejected | check |
| 30 | pc1 ACT same bank group inside tRRD_L rejected | check |
| 31 | pc1 ACT at tRRD_L | check |
| 32 | pc1 ACT other bank group inside tRRD_S rejected | check |
| 33 | four ACTs on pc1 | check |
| 34 | pc0 ACT not limited by pc1's tFAW window | check |
| 35 | fifth pc1 ACT inside tFAW rejected | check |
| 36 | fifth pc1 ACT at tFAW accepted | check |
| 37 | REFpb to an open bank rejected | check |
| 38 | REFpb to an idle bank accepted | check |
| 39 | REFpb inside tRREFD of the previous REFpb rejected | check |
| 40 | ACT to another bank inside tRREFD rejected | check |
| 41 | ACT to another bank at tRREFD accepted | check |
| 42 | ACT to the refreshing bank inside tRFCpb rejected | check |
| 43 | ACT to the refreshed bank at tRFCpb accepted | check |
| 44 | REFab with pc1 banks open rejected | check |
| 45 | MRS with pc1 banks open rejected | check |
| 46 | PREab closes every pc1 bank | check |
| 47 | PREab pc1 leaves pc0 banks open | check |
| 48 | REFab inside tRP rejected | check |
| 49 | REFab pc1 accepted | check |
| 50 | pc0 column command during pc1 refresh accepted | check |
| 51 | pc1 ACT inside tRFCab rejected | check |
| 52 | pc1 ACT at tRFCab accepted | check |
| 53 | column command to a bank with auto precharge pending rejected | check |
| 54 | RDA: bank open until ACT + tRAS | check |
| 55 | RDA: auto precharge at ACT + tRAS | check |
| 56 | ACT inside tRP of the auto precharge rejected | check |
| 57 | WRA: bank open until write recovery ends | check |
| 58 | WRA: auto precharge at WRA + WL + 4 + tWR | check |
| 59 | PREab pc0 | check |
| 60 | MRS RL 4 (below the supported range) rejected | check |
| 61 | MRS pc0 RL 30 | check |
| 62 | command inside tMOD rejected | check |
| 63 | MRS pc0 WL 12 | check |
| 64 | pc1 column command one clock after pc0's (no shared tCCD) | check |
| 65 | pc0 at RL 30 / WL 12 and pc1 at RL 20 / WL 8 (bad %0d extra %0d) | check |
| 66 | pc1 WR at its own turnaround | check |
| 67 | write data missing on pc1 flagged | check |
| 68 | only pc1 reports missing write data | check |
| 69 | reserved row command rejected | check |
| 70 | reserved column command rejected | check |
| 71 | 400 legal random commands raise no error (%0d) | check |
| 72 | random traffic read data and latency (reads %0d bad %0d extra %0d) | check |
| 73 | 16 REFpb on pc1 accepted | check |
| 74 | postponed refresh limit flagged once per pseudo channel (%0d, %0d) | check |
| 75 | 16 REFpb count as one refresh (pc1 flagged %0d clocks after pc0) | check |
| 76 | PREab inside tRAS rejected | check |
| 77 | PREab pc0 leaves the open pc1 bank 0 | check |
| 78 | REFab pc1 with only its bank 0 open rejected | check |
| 79 | MRS pc1 with only its bank 0 open rejected | check |
| 80 | REFab pc0 with a pc1 bank open | check |
| 81 | MRS WL 30 (above the range) rejected | check |
| 82 | MRS WL 1 (below the range) rejected | check |
| 83 | MRS pc0 with a pc1 bank open | check |
| 84 | REFpb pc0 bank 5 | check |
| 85 | REFpb to a bank still inside tRFCpb rejected | check |
| 86 | PREab inside tRTP of bank 8 (bank 12 inside tRAS): only tRTP reported | check |
| 87 | WR bank 12 after the turnaround | check |
| 88 | PREab inside tWR of bank 12 rejected | check |
| 89 | RDA bank 8 | check |
| 90 | PREab with an auto precharge pending rejected | check |
| 91 | PREab pc0 after the auto precharge | check |
| 92 | reads around the PREab checks | check |
| 93 | first ACT after reset accepted | check |
| 94 | RD after reset accepted | check |
| 95 | memory reads zero after reset, at the reset RL 20 | check |
| 96 | no refresh after reset: flagged at exactly (REF_POSTPONE + 1) * tREFI (%0d) | check |

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

UVM agent test（`hbm3e_func_test`：directed + constrained-random 流量，scoreboard 以 DUT 模型的參考模型逐筆比對，並比對 driver 與 monitor 的 transaction）在 Verilator 上以 `python3 tools/run_uvm_tests.py HBM3E-VIP` 執行；agent 由 `tools/gen_uvm_agents.py` 依 `tools/uvm_agents/` 的協定 spec 產生。

| 項目 | 數量 | 名稱 |
|---|---|---|
| UVM tests | 2 | `hbm3e_base_test`, `hbm3e_func_test` |
| Sequences | 3 | `hbm3e_base_sequence`, `hbm3e_directed_sequence`, `hbm3e_transaction` |
| SVA（assert / cover property） | 3 / 2 | - |
| Covergroups / coverpoints | 1 / 3 | |

## 4. 充分度判定與缺口

判定：**✅ Sufficient**（116 個 check，mutation score 100%）。

模型未實作的功能（不在測試範圍）：

- Not modelled (limitations, not tested): ACT/PRE/REF timing, bank state, burst length and the real HBM3E command encoding.

