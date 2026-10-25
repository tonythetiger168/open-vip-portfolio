# ARM Serial Wire Debug 測試套件（SWD-VIP）

> 由 `tools/gen_test_suite_docs.py` 依 VIP 內容、`func_report.csv` 與 `mutation_report.csv` 自動產生，請勿手動修改。

## 1. 概要

| 項目 | 內容 |
|---|---|
| 類別 | Debug |
| 類型 | UVM VIP |
| 功能測試 | 1 個檔案，23 個 check，全部通過 |
| Mutation | 11/12 個 mutant 被偵測（92%） |
| 判定 | **✅ Sufficient**（23 個 check，mutation score 92%） |

## 2. 可執行的功能測試

執行：`python3 tools/run_func_tests.py SWD-VIP`（Icarus Verilog 或 Verilator 5.052）。

### `tb/func_swd_tb.sv`

結果：**PASS**（verilator，23 checks）

模型合約與範圍（摘自測試檔頭）：

```text
func_swd_tb.sv -- self-checking functional test for the Arm SWD debug port
model (swd_dp_model, flattened by smoke/flatten.py).
Run: python3 tools/run_func_tests.py SWD-VIP

Model contract (from tb/top_tb.sv), ADIv5 SWD wire protocol:
   the host drives SWDIO on the falling edge, the target samples on the
   rising edge. Packet header (LSB first): Start=1, APnDP, RnW, A[3:2],
   parity(APnDP,RnW,A), Stop=0, Park=1; one turnaround cell; 3-bit ACK
   (OK=001, WAIT=010, FAULT=100) driven by the target; then 32 data bits LSB
   first + parity (read: target drives, then turnaround; write: turnaround,
   then the host drives). DP: 0x0 DPIDR (RO, 0x2BA01477), 0x4 CTRL/STAT,
   0x8 SELECT, 0xC RDBUFF (RO, write FAULTs). AP: 0x0 IDR (0x04770031),
   0x4 TAR (an AP read also latches TAR into RDBUFF), 0x8 WAIT, 0xC FAULT.
   A header with bad parity/stop/park is ignored (no ACK). Write data with
   bad parity is ACKed but not applied.
```

| # | Check | 類型 |
|---|---|---|
| 1 | DP DPIDR read ACKed OK | check |
| 2 | DPIDR value read LSB first | check |
| 3 | read data parity correct | check |
| 4 | target releases SWDIO after the read turnaround | check |
| 5 | CTRL/STAT reads 0 after power-up | check |
| 6 | SELECT reads 0 after power-up | check |
| 7 | TAR and RDBUFF read 0 after power-up | check |
| 8 | DP CTRL/STAT write ACKed OK | check |
| 9 | target does not drive SWDIO during the write data phase | check |
| 10 | CTRL/STAT reads back the written value (power-up request) | check |
| 11 | SELECT write / read-back | check |
| 12 | CTRL/STAT and TAR writes leave SELECT unchanged | check |
| 13 | write to read-only RDBUFF FAULTs | check |
| 14 | AP IDR read | check |
| 15 | AP TAR write ACKed OK | check |
| 16 | AP TAR read returns the written address | check |
| 17 | RDBUFF returns the result of the last AP read | check |
| 18 | AP register 0x8 answers WAIT | check |
| 19 | AP register 0xC answers FAULT | check |
| 20 | header with bad parity is ignored (no ACK) | check |
| 21 | target resynchronises on the next good header | check |
| 22 | write with bad data parity is still ACKed | check |
| 23 | write with bad data parity is not applied | check |

## 3. UVM 測試平台內容

UVM 測試需商用模擬器（VCS / Xcelium / Questa）執行；開源流程只做 elaboration（L1a）。

| 項目 | 數量 | 名稱 |
|---|---|---|
| UVM tests | 3 | `swd_base_test`, `swd_random_test`, `swd_regression_test` |
| Sequences | 11 | `swd_base_sequence`, `swd_read_idr_seq`, `swd_write_read_seq`, `swd_rdbuff_seq`, `swd_wait_resp_seq`, `swd_fault_resp_seq`, `swd_parity_err_seq`, `swd_back_to_back_seq`, `swd_random_sequence`, `swd_regression_sequence`, `swd_transaction` |
| SVA（assert / cover property） | 20 / 2 | `a_swd_l1_clk`, `a_swd_l1_rst`, `a_swd_l1_state`, `a_swd_l1_valid`, `a_swd_trans_idle`, `a_swd_trans_header`, `a_swd_trans_ack_turn`, `a_swd_trans_data`, `a_swd_trans_parity`, `a_swd_l3_reset_idle`, `a_swd_l3_no_stuck`, `a_swd_l3_full_cycle` … |
| Covergroups / coverpoints | 3 / 9 | |

## 4. 充分度判定與缺口

判定：**✅ Sufficient**（23 個 check，mutation score 92%）。

未被偵測的 mutant（測試缺口或等價 mutant）：

- `dut_swd_dp_model.sv:21 0 -> 1 [bit [31:0] ctrlstat = 0, select_reg = 0, tar = 0, rdbuff = 0]`

