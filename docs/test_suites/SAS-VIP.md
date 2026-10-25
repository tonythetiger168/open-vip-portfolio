# SAS-4 (Serial Attached SCSI) 測試套件（SAS-VIP）

> 由 `tools/gen_test_suite_docs.py` 依 VIP 內容、`func_report.csv` 與 `mutation_report.csv` 自動產生，請勿手動修改。

## 1. 概要

| 項目 | 內容 |
|---|---|
| 類別 | Storage |
| 類型 | UVM VIP |
| 功能測試 | 1 個檔案，42 個 check，全部通過 |
| Mutation | 10/10 個 mutant 被偵測（100%） |
| 判定 | **✅ Sufficient**（42 個 check，mutation score 100%） |

## 2. 可執行的功能測試

執行：`python3 tools/run_func_tests.py SAS-VIP`（Icarus Verilog 或 Verilator 5.052）。

### `tb/func_sas_tb.sv`

結果：**PASS**（verilator，42 checks）

模型合約與範圍（摘自測試檔頭）：

```text
func_sas_tb.sv -- self-checking functional test for the SAS target model
(sas_target_model, flattened by smoke/flatten.py).
Run: python3 tools/run_func_tests.py SAS-VIP

Model contract (from tb/top_tb.sv and sas_defs.sv), an abstracted SAS link:
   OOB: a 32-clock zero run on txp, then 24+ toggles, raises phy_ready;
   a 33-clock zero run while up drops it. Bytes are serial,
   2 clocks per bit: start 0, 8 data bits LSB first, stop 1.
   Frame: type, address (8 bytes LSB first), word count (<= 4), words
   (4 bytes LSB first each), XOR checksum of all previous bytes.
   Target address 0x5A5A_0000_0000_0001. IDENTIFY -> IDENTIFY;
   OPEN_READ/WRITE to the target with a good checksum -> ACCEPT and
   credit_cnt = 4, otherwise REJECT; DATA on an open connection -> echo of
   the DATA frame then CREDIT (bad checksum -> NAK), last_payload_len =
   word count; DATA without a connection is ignored; CLOSE closes.

A zero run of any length >= 32 clocks starts speed negotiation (the VIP
driver's COMRESET is 48 clocks low, then 32 toggles). The byte receiver
runs alongside the frame server, so a frame may start right after a
response's stop bit; it arms once txp has idled high after negotiation,
so toggles sent after phy_ready rises are ignored. An oversize DATA frame
is consumed whole and not answered.
```

| # | Check | 類型 |
|---|---|---|
| 1 | reset: PHY not ready, rxp idle high, no credits | check |
| 2 | 20-clock zero run is not an OOB signal | check |
| 3 | VIP driver OOB (48 zero clocks, 32 toggles) brings the PHY ready | check |
| 4 | 32-clock zero run enters speed negotiation; 16 toggles are not enough | check |
| 5 | a 32-clock zero run during speed negotiation restarts the toggle count | check |
| 6 | a full set of toggles then completes speed negotiation: PHY ready | check |
| 7 | IDENTIFY answered with IDENTIFY from the target address | check |
| 8 | response bytes have valid stop bits | check |
| 9 | frame sent right after the response's stop bit is received | check |
| 10 | DATA without an open connection is ignored | check |
| 11 | OPEN to another address -> REJECT | check |
| 12 | OPEN with a bad checksum -> REJECT | check |
| 13 | OPEN_WRITE to the target -> ACCEPT | check |
| 14 | ACCEPT grants 4 credits | check |
| 15 | DATA (4 words) echoed with its address and payload | check |
| 16 | CREDIT frame follows the echo | check |
| 17 | last_payload_len = 4, data_frame_active pulsed | check |
| 18 | one credit consumed by DATA, returned with CREDIT | check |
| 19 | 1-word DATA echoed | check |
| 20 | CREDIT, last_payload_len = 1 | check |
| 21 | empty DATA echoed | check |
| 22 | CREDIT, last_payload_len = 0 | check |
| 23 | DATA with a bad checksum -> NAK, credits unchanged | check |
| 24 | no echo / CREDIT after a NAK | check |
| 25 | DATA with more than 4 words is not echoed | check |
| 26 | remainder of an oversize DATA frame is not parsed as new frames | check |
| 27 | link re-established: OPEN_READ accepted | check |
| 28 | byte with a bad stop bit is dropped (no response) | check |
| 29 | connection open before CLOSE | check |
| 30 | CLOSE clears the credits | check |
| 31 | DATA after CLOSE is ignored | check |
| 32 | OPEN_READ re-opens the connection | check |
| 33 | OPEN to another address while open -> REJECT | check |
| 34 | DATA after a rejected OPEN is ignored | check |
| 35 | OPEN_READ accepted again | check |
| 36 | dropping to speed negotiation starts with no toggles counted | check |
| 37 | 33+ zero clocks while up drop phy_ready | check |
| 38 | OOB brings the link back; the connection is closed | check |
| 39 | IDENTIFY after link recovery | check |
| 40 | link up after a full 32-toggle speed negotiation | check |
| 41 | first frame after 32 SN toggles is received correctly | check |
| 42 | reset drops phy_ready | check |

## 3. UVM 測試平台內容

UVM 測試需商用模擬器（VCS / Xcelium / Questa）執行；開源流程只做 elaboration（L1a）。

| 項目 | 數量 | 名稱 |
|---|---|---|
| UVM tests | 3 | `sas_base_test`, `sas_random_test`, `sas_regression_test` |
| Sequences | 11 | `sas_base_sequence`, `sas_ssp_read_seq`, `sas_ssp_write_seq`, `sas_max_payload_seq`, `sas_single_word_seq`, `sas_open_reject_seq`, `sas_crc_error_seq`, `sas_reset_seq`, `sas_random_sequence`, `sas_regression_sequence`, `sas_transaction` |
| SVA（assert / cover property） | 21 / 2 | `a_sas_l1_clk`, `a_sas_l1_rst`, `a_sas_l1_state`, `a_sas_l1_valid`, `a_sas_trans_oob_reset`, `a_sas_trans_speed_neg`, `a_sas_trans_identify`, `a_sas_trans_open_address`, `a_sas_trans_data_xfer`, `a_sas_trans_close`, `a_sas_l3_reset_idle`, `a_sas_l3_no_stuck` … |
| Covergroups / coverpoints | 3 / 10 | |

## 4. 充分度判定與缺口

判定：**✅ Sufficient**（42 個 check，mutation score 100%）。

無已知缺口。

