# PCIe 測試套件（PCIe-VIP）

> 由 `tools/gen_test_suite_docs.py` 依 VIP 內容、`func_report.csv` 與 `mutation_report.csv` 自動產生，請勿手動修改。

## 1. 概要

| 項目 | 內容 |
|---|---|
| 類別 | Interconnect |
| 類型 | UVM VIP |
| 功能測試 | 3 個檔案，128 個 check，全部通過 |
| Mutation | 91/91 個 mutant 被偵測（100%） |
| 判定 | **✅ Sufficient**（128 個 check，mutation score 100%） |

## 2. 可執行的功能測試

執行：`python3 tools/run_func_tests.py PCIe-VIP`（Icarus Verilog 或 Verilator 5.052）。

### `pcie_dl/tb/func_pcie_dl_tb.sv`

結果：**PASS**（verilator，88 checks）

| # | Check | 類型 |
|---|---|---|
| 1 | InitFC1 P, NP and Cpl sent in DL_Init | check |
| 2 | DL not up before the partner's InitFC | check |
| 3 | InitFC1-P advertises PH 4 / PD 32 | check |
| 4 | InitFC1-NP advertises NPH 4 / NPD 4 | check |
| 5 | InitFC1-Cpl advertises infinite completion credits | check |
| 6 | InitFC2 sent after all InitFC1 received | check |
| 7 | no InitFC1 after FC_INIT2 starts | check |
| 8 | DL not up until an InitFC2 is received | check |
| 9 | DL_Active after the partner's InitFC2 | check |
| 10 | no ACK / NAK before any TLP | check |
| 11 | InitFC2 received in FC_INIT1: model moves to FC_INIT2, DL not up yet | check |
| 12 | InitFC1 received in FC_INIT2 does not complete it | check |
| 13 | no ACK / NAK after the link-down reset | check |
| 14 | a TLP received in FC_INIT2 completes it and is ACKed | check |
| 15 | Polling.Active sends TS1 after receiver detect | check |
| 16 | Polling times out to Detect without a partner | check |
| 17 | LTSSM left Polling.Active for Detect on timeout | check |
| 18 | Detect.Quiet holds without receiver detect | check |
| 19 | LTSSM Detect -> Polling.Active -> Polling.Configuration -> Configuration -> L0 | check |
| 20 | at least 16 TS1 sent before Polling.Configuration (%0d) | check |
| 21 | at least 16 TS2 sent in Polling.Configuration (%0d) | check |
| 22 | L0: link up, no training ordered sets | check |
| 23 | first TLP from the model: seq 0, good LCRC | check |
| 24 | CfgRd0 completes with 1 DW, byte count 4 | check |
| 25 | completer ID captured from the configuration request | check |
| 26 | Vendor / Device ID | check |
| 27 | CfgWr0 completes without data | check |
| 28 | BAR0: 4 KB, low 12 bits read-only zero | check |
| 29 | Command: only IO / Memory / Bus Master writable | check |
| 30 | CfgWr0 byte enables | check |
| 31 | completion sequence numbers increment | check |
| 32 | ACK carries the last received sequence number | check |
| 33 | 96-byte read starting at 0x20 returns two completions (64-byte RCB) | check |
| 34 | first completion: 8 DW, byte count 93, lower address 0x21 | check |
| 35 | second completion: 16 DW, remaining byte count 62, lower address 0x40 | check |
| 36 | read data matches the written bytes and byte enables (%0d bad) | check |
| 37 | a Message TLP is accepted without error | check |
| 38 | bytes without a start of TLP are ignored | check |
| 39 | zero-length read: one DW, byte count 1 | check |
| 40 | 1-DW read with one byte enabled: byte count 1, lower address 0x7E | check |
| 41 | read crossing no RCB boundary: one completion | check |
| 42 | everything ACKed: the replay timer does not expire while idle | check |
| 43 | UpdateFC-NP returns the headers of the 11 non-posted requests so far | check |
| 44 | read outside BAR0: UR completion | check |
| 45 | IOWr: UR completion | check |
| 46 | poisoned and malformed TLPs flagged | check |
| 47 | poisoned and malformed writes are dropped | check |
| 48 | bad LCRC flagged | check |
| 49 | NAK with the last good sequence number | check |
| 50 | out-of-sequence TLP dropped, no second NAK while NAK_SCHEDULED | check |
| 51 | replayed TLP accepted and ACKed | check |
| 52 | duplicate TLP ACKed but not executed | check |
| 53 | ACK after the duplicate | check |
| 54 | out-of-sequence TLP alone schedules a NAK | check |
| 55 | next in-sequence TLP clears NAK_SCHEDULED and is ACKed | check |
| 56 | bad DLLP CRC and out-of-range ACK flagged | check |
| 57 | no UpdateFC-P before the credits are freed | check |
| 58 | UpdateFC-P after posted credits are freed | check |
| 59 | UpdateFC-P header limit %0d = initial 4 + %0d freed | check |
| 60 | a fifth posted TLP within the credit window: receiver overflow | check |
| 61 | the overflowing TLP is not executed | check |
| 62 | NAK: TLP replayed with its sequence number | check |
| 63 | replayed TLP is bit-identical, LCRC included | check |
| 64 | replay timer expiry replays (after %0d clocks) | check |
| 65 | REPLAY_NUM rollover on the fourth replay | check |
| 66 | rollover sends the LTSSM to Recovery | check |
| 67 | Recovery returns to L0 with the Data Link Layer up | check |
| 68 | ACK purges the replay buffer: no further replays | check |
| 69 | TS1 in L0 enters Recovery.RcvrLock | check |
| 70 | after Recovery: sequence numbers continue, config state kept | check |
| 71 | EIOS in L0: Detect, Data Link Layer down | check |
| 72 | Cpl credits 1 header / 2 data: one completion, then the transmitter waits | check |
| 73 | a header credit alone does not release an 8-DW completion | check |
| 74 | UpdateFC-Cpl releases the next completion | check |
| 75 | second retrain: sequence numbers restart, config read completes | check |
| 76 | every DLLP from the model has a good CRC | check |
| 77 | tx_valid only inside TLP frames | check |
| 78 | every TLP from the model has a good LCRC | check |

### `pcie_flit/tb/func_pcie_flit_tb.sv`

結果：**PASS**（iverilog，28 checks）

| # | Check | 類型 |
|---|---|---|
| 1 | payload flit 0 delivered, no Ack yet | check |
| 2 | Ack after 4 unacknowledged flits | check |
| 3 | flits 0-3 delivered in order | check |
| 4 | no Ack before the Ack timer | check |
| 5 | Ack for the single flit after ACK_TMO clocks | check |
| 6 | NOP flit: Ack field passed on, no TLP | check |
| 7 | Nak field on a payload flit passed on | check |
| 8 | Ack field type 3 ignored | check |
| 9 | one bad byte in each interleave: corrected (3) | check |
| 10 | bad parity bytes corrected | check |
| 11 | bad CRC and sequence bytes corrected | check |
| 12 | two bad bytes in one interleave: dropped, Nak | check |
| 13 | next flit out of sequence: no second Nak while one is scheduled | check |
| 14 | replayed flit accepted, its Ack field passed on | check |
| 15 | a new gap sends a new Nak | check |
| 16 | bad flit: dropped, Ack field ignored, Nak | check |
| 17 | flit CRC failure: dropped, Nak | check |
| 18 | duplicate: dropped, Ack at once | check |
| 19 | 512 behind is a duplicate | check |
| 20 | 511 ahead is a gap | check |
| 21 | flit type 2 dropped | check |
| 22 | sequence wraps 1023 -> 0 | check |
| 23 | directed flits: every output as the reference | check |
| 24 | %0d random flits: deliveries, Ack / Nak, corrections and errors as the reference (%0d TLPs, %0d Acks, %0d Naks) | check |
| 25 | random flits exercised Naks and corrections | check |
| 26 | reset clears outputs, counter and errors | check |
| 27 | after reset no Nak is scheduled: a gap sends one | check |
| 28 | after reset the expected sequence is 0 | check |

### `tb/smoke_func_tb.sv`

結果：**PASS**（verilator，12 checks）

| # | Check | 類型 |
|---|---|---|
| 1 | TLP beat during reset is ignored | check |
| 2 | no transfer in progress after reset | check |
| 3 | single-beat write TLP counted once | check |
| 4 | single-beat write TLP data stored at TLP address | check |
| 5 | in_tlp set between SOP and EOP | check |
| 6 | multi-beat write TLP counted once at EOP | check |
| 7 | in_tlp cleared after EOP | check |
| 8 | payload DW0 at addr+0 | check |
| 9 | payload DW1 at addr+4 | check |
| 10 | payload DW2 at addr+8 | check |
| 11 | subsequent TLP increments write count | check |
| 12 | posted write overwrites previous contents | check |

## 3. UVM 測試平台內容

UVM 測試需商用模擬器（VCS / Xcelium / Questa）執行；開源流程只做 elaboration（L1a）。

| 項目 | 數量 | 名稱 |
|---|---|---|
| UVM tests | 6 | `mp_base_test`, `mp_error_inject_test`, `mp_pcie_gen5_test`, `mp_pcie_gen6_test`, `mp_power_mgmt_test`, `mp_random_regression_test` |
| Sequences | 10 | `mp_base_sequence`, `mp_back_to_back_sequence`, `mp_stress_sequence`, `mp_corner_case_sequence`, `mp_reset_sequence`, `mp_error_inject_sequence`, `mp_power_mgmt_sequence`, `mp_random_sequence`, `mp_regression_sequence`, `mp_sequence_item` |
| SVA（assert / cover property） | 28 / 25 | `assert_valid_ready`, `assert_sop_eop`, `assert_link_state`, `assert_p_pcie_tlp_fmt`, `cover_p_pcie_tlp_fmt`, `assert_p_pcie_tlp_type`, `cover_p_pcie_tlp_type`, `assert_p_pcie_tag_range`, `cover_p_pcie_tag_range`, `assert_p_pcie_tc_range`, `cover_p_pcie_tc_range`, `assert_p_pcie_length_dw` … |
| Covergroups / coverpoints | 7 / 20 | |

## 4. 充分度判定與缺口

判定：**✅ Sufficient**（128 個 check，mutation score 100%）。

無已知缺口。

