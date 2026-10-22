# SAS-4 (Serial Attached SCSI) 測試套件（SAS-VIP）

> 由 `tools/gen_test_suite_docs.py` 依 VIP 內容、`func_report.csv` 與 `mutation_report.csv` 自動產生，請勿手動修改。

## 1. 概要

| 項目 | 內容 |
|---|---|
| 類別 | Storage |
| 類型 | UVM VIP |
| 功能測試 | 1 個檔案，37 個 check，全部通過 |
| Mutation | 9/12 個 mutant 被偵測（75%） |
| 判定 | **🟡 Partial**（mutation score 75%） |

## 2. 可執行的功能測試

執行：`python3 tools/run_func_tests.py SAS-VIP`（Icarus Verilog 或 Verilator 5.052）。

### `tb/func_sas_tb.sv`

結果：**PASS**（verilator，37 checks）

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

Model defect: the zero-run counter is not cleared on entering speed
negotiation, so a zero run longer than 32 clocks bounces SN -> DOWN and
the link only comes up when the run is 32 (mod 34) clocks long. The VIP
driver's COMRESET (48 clocks low, then toggles) never brings it up (XFAIL).
The target is single-threaded: it listens again only after the trailing
idle bit of its own response, so a frame started right after the response
(as sas_driver does) is missed; the test leaves an 8-clock gap and checks
the back-to-back case as XFAIL.
```

| # | Check | 類型 |
|---|---|---|
| 1 | reset: PHY not ready, rxp idle high, no credits | check |
| 2 | 20-clock zero run is not an OOB signal | check |
| 3 | VIP driver OOB (48 zero clocks, 32 toggles) brings the PHY ready | XFAIL（模型缺陷） |
| 4 | 32-clock zero run enters speed negotiation; 16 toggles are not enough | check |
| 5 | 30 toggles complete speed negotiation: PHY ready | check |
| 6 | IDENTIFY answered with IDENTIFY from the target address | check |
| 7 | response bytes have valid stop bits | check |
| 8 | frame sent right after the response's stop bit is received | XFAIL（模型缺陷） |
| 9 | DATA without an open connection is ignored | check |
| 10 | OPEN to another address -> REJECT | check |
| 11 | OPEN with a bad checksum -> REJECT | check |
| 12 | OPEN_WRITE to the target -> ACCEPT | check |
| 13 | ACCEPT grants 4 credits | check |
| 14 | DATA (4 words) echoed with its address and payload | check |
| 15 | CREDIT frame follows the echo | check |
| 16 | last_payload_len = 4, data_frame_active pulsed | check |
| 17 | one credit consumed by DATA, returned with CREDIT | check |
| 18 | 1-word DATA echoed | check |
| 19 | CREDIT, last_payload_len = 1 | check |
| 20 | empty DATA echoed | check |
| 21 | CREDIT, last_payload_len = 0 | check |
| 22 | DATA with a bad checksum -> NAK, credits unchanged | check |
| 23 | no echo / CREDIT after a NAK | check |
| 24 | DATA with more than 4 words is not echoed | check |
| 25 | remainder of an oversize DATA frame is not parsed as new frames | XFAIL（模型缺陷） |
| 26 | link re-established: OPEN_READ accepted | check |
| 27 | byte with a bad stop bit is dropped (no response) | check |
| 28 | connection open before CLOSE | check |
| 29 | CLOSE clears the credits | check |
| 30 | DATA after CLOSE is ignored | check |
| 31 | OPEN_READ re-opens the connection | check |
| 32 | 33+ zero clocks while up drop phy_ready | check |
| 33 | OOB brings the link back; the connection is closed | check |
| 34 | IDENTIFY after link recovery | check |
| 35 | link up after a full 32-toggle speed negotiation | check |
| 36 | first frame after 32 SN toggles is received correctly | XFAIL（模型缺陷） |
| 37 | reset drops phy_ready | check |

## 3. UVM 測試平台內容

UVM 測試需商用模擬器（VCS / Xcelium / Questa）執行；開源流程只做 elaboration（L1a）。

| 項目 | 數量 | 名稱 |
|---|---|---|
| UVM tests | 3 | `sas_base_test`, `sas_random_test`, `sas_regression_test` |
| Sequences | 11 | `sas_base_sequence`, `sas_ssp_read_seq`, `sas_ssp_write_seq`, `sas_max_payload_seq`, `sas_single_word_seq`, `sas_open_reject_seq`, `sas_crc_error_seq`, `sas_reset_seq`, `sas_random_sequence`, `sas_regression_sequence`, `sas_transaction` |
| SVA（assert / cover property） | 21 / 2 | `a_sas_l1_clk`, `a_sas_l1_rst`, `a_sas_l1_state`, `a_sas_l1_valid`, `a_sas_trans_oob_reset`, `a_sas_trans_speed_neg`, `a_sas_trans_identify`, `a_sas_trans_open_address`, `a_sas_trans_data_xfer`, `a_sas_trans_close`, `a_sas_l3_reset_idle`, `a_sas_l3_no_stuck` … |
| Covergroups / coverpoints | 3 / 10 | |

## 4. 充分度判定與缺口

判定：**🟡 Partial**（mutation score 75%）。

未被偵測的 mutant（測試缺口或等價 mutant）：

- `dut_sas_target_model.sv:24 0 -> 1 [int zero_cnt   = 0;]`
- `dut_sas_target_model.sv:49 1'b0 inverted [if (vif_txp == 1'b0)      zero_cnt   <= zero_cnt + 1;]`
- `dut_sas_target_model.sv:88 0 -> 1 [int io_nwords = 0;]`

DUT 模型缺陷（XFAIL check，修好模型後會變成 XPASS 提醒移除標記）：

- VIP driver OOB (48 zero clocks, 32 toggles) brings the PHY ready
- frame sent right after the response's stop bit is received
- remainder of an oversize DATA frame is not parsed as new frames
- first frame after 32 SN toggles is received correctly

