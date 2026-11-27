# HBM3 測試套件（hbm3-VIP）

> 由 `tools/gen_test_suite_docs.py` 依 VIP 內容、`func_report.csv` 與 `mutation_report.csv` 自動產生，請勿手動修改。

## 1. 概要

| 項目 | 內容 |
|---|---|
| 類別 | Memory |
| 類型 | UVM VIP |
| 功能測試 | 1 個檔案，118 個 check，全部通過 |
| Mutation | 7/12 個 mutant 被偵測（58%） |
| 判定 | **🟡 Partial**（mutation score 58%） |

## 2. 可執行的功能測試

執行：`python3 tools/run_func_tests.py hbm3-VIP`（Icarus Verilog 或 Verilator 5.054）。

### `hbm3_vip/tb/func_hbm3_dev_tb.sv`

結果：**PASS**（verilator，118 checks）

模型合約與範圍（摘自測試檔頭）：

```text
FUNC_SIM: verilator

func_hbm3_dev_tb.sv -- HBM3 row / column command buses (JESD238) driven
pin by pin into hbm3_dev_model, with the commands encoded here from the
command tables (rising and falling half of each clock, "valid" bits
random):
   * ACT over 1.5 clocks, RD / RDA / WR / WRA, PREpb / PREab (also in the
     falling half), REFab / REFpb, RFMab / RFMpb, PDE / SRE, RNOP / CNOP
   * two pseudo-channels on shared buses: independent bank state, data and
     timing (PC1 works while PC0 refreshes)
   * MRS: RL / WL from MR2 / MR1 (data latency follows), MRS with a bank
     open, MA4 set, RL out of range, tMOD
   * timing at the boundary (one clock early rejected, on time accepted):
     tRCDRD, tRCDWR, tRAS, tRP, tRRDL / tRRDS, tFAW, tCCDL / tCCDS, tRTP,
     tWR, tWTRL, tRTW, tPPD, tRFCab, tRREFD
   * bus errors: reserved row and column codes, a row command other than
     PRE in the falling half, broken ACT halves, PDE halves that differ
   * CA parity (MR0 OP6): even parity on every edge, a bad edge pulses AERR
     PARAC clocks later and the command still executes
   * missing write data; 60 random bursts on both pseudo-channels against
     a reference memory
Run: python3 tools/run_func_tests.py hbm3-VIP
```

| # | Check | 類型 |
|---|---|---|
| 1 | PREab closes PC%0d (err %h) | check |
| 2 | %s: accepted (err %h) | check |
| 3 | %s: rejected with bit %0d (err %h) | check |
| 4 | ACT / WR / RD on both pseudo-channels accepted (%0d %0d %0d) | check |
| 5 | bank 3 open in each pseudo-channel | check |
| 6 | PC0 read data = written data (RL 14, WL 4, BL8 in two clocks) | check |
| 7 | PC1 read data = written data, the PCs keep their own data at the same bank / row / column | check |
| 8 | MRS MR2 = 20 and MR1 = 6 accepted | check |
| 9 | MRS inside tMOD rejected on both PCs | check |
| 10 | MRS with a bank open rejected | check |
| 11 | data at the new latencies (RL 20, WL 6) | check |
| 12 | MRS with MA4 = 1 or RL = 2 flagged | check |
| 13 | only bank 8 open | check |
| 14 | RFMpb / RFMab decoded without bus error | check |
| 15 | WRA closes the bank by itself | check |
| 16 | RDA returns the data and closes the bank | check |
| 17 | PREab in the falling half | check |
| 18 | reserved row code (be %h) | check |
| 19 | REFab in the falling half (be %h) | check |
| 20 | reserved column code (be %h) | check |
| 21 | ACT with a broken falling half not executed (be %h) | check |
| 22 | PDE / SRE halves differ (be %h) | check |
| 23 | PDE and SRE decoded | check |
| 24 | bad CA parity flagged (be %h) | check |
| 25 | AERR one clock, PARAC after the bad edge (%0d) | check |
| 26 | the command with bad parity still executes | check |
| 27 | no AERR with good parity | check |
| 28 | write data missing flagged | check |
| 29 | random traffic: %0d reads match the reference memory (%0d bad) | check |

## 3. UVM 測試平台內容

UVM 測試需商用模擬器（VCS / Xcelium / Questa）執行；開源流程只做 elaboration（L1a）。

| 項目 | 數量 | 名稱 |
|---|---|---|
| UVM tests | 2 | `hbm3_base_test`, `hbm3_func_test` |
| Sequences | 5 | `hbm3_seq_base`, `hbm3_base_sequence`, `hbm3_directed_sequence`, `hbm3_transaction`, `hbm3_cmd_item` |
| SVA（assert / cover property） | 13 / 4 | `a_x_rise`, `a_x_fall`, `a_par_rise`, `a_par_fall`, `a_act_half2`, `a_act_half3`, `a_fall_cmd`, `a_rd0_burst`, `a_rd1_burst`, `a_wd0_burst`, `a_wd1_burst`, `a_rd_x` … |
| Covergroups / coverpoints | 4 / 8 | |

## 4. 充分度判定與缺口

判定：**🟡 Partial**（mutation score 58%）。

未被偵測的 mutant（測試缺口或等價 mutant）：

- `dut_hbm3_dev_model.sv:9 14 -> 15 [parameter int tRCDRD = 14, tRCDWR = 10, tRAS = 28, tRP = 14,]`
- `dut_hbm3_dev_model.sv:12 4 -> 5 [parameter int RL_RST = 14, WL_RST = 4, PARAC = 4) (]`
- `dut_hbm3_dev_model.sv:191 64 -> 65 [for (int b = 0; b < 64; b++) begin]`
- `dut_hbm3_dev_model.sv:236 1'b1 inverted [if (ap_at[p][i] >= 0) e1[0] = 1'b1;]`
- `dut_hbm3_dev_model.sv:252 > -> >= in condition [if (SIDS > 1 && int'(x[5:4]) >= SIDS && ({x[0], x[1], x[2]} ]`

