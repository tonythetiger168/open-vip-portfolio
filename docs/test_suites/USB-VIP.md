# USB 測試套件（USB-VIP）

> 由 `tools/gen_test_suite_docs.py` 依 VIP 內容、`func_report.csv` 與 `mutation_report.csv` 自動產生，請勿手動修改。

## 1. 概要

| 項目 | 內容 |
|---|---|
| 類別 | USB |
| 類型 | UVM VIP |
| 功能測試 | 5 個檔案，902 個 check，全部通過 |
| Mutation | 27/27 個 mutant 被偵測（100%） |
| 判定 | **✅ Sufficient**（902 個 check，mutation score 100%） |

## 2. 可執行的功能測試

執行：`python3 tools/run_func_tests.py USB-VIP`（Icarus Verilog 或 Verilator 5.054）。

### `tb/func_eusb2_tb.sv`

結果：**PASS**（iverilog，88 checks）

| # | Check | 類型 |
|---|---|---|
| 1 | native: SE0 for 16 clocks -> RESET | check |
| 2 | RESET lasts 8 clocks, then CHIRP | check |
| 3 | device chirp K, then HS_WAIT | check |
| 4 | chirp K ends | check |
| 5 | 3 host K-J pairs: L0 at HS | check |
| 6 | in reset: DISC, nothing sent | check |
| 7 | after rst_n: DISC, CTRL = lpm_en | check |
| 8 | J without attach: DISC | check |
| 9 | 3 clocks of J: not yet attached | check |
| 10 | J for 4 clocks with attach: ATTACHED | check |
| 11 | ATTACHED: packets and LPM ignored before reset | check |
| 12 | attach low: DISC, counted | check |
| 13 | re-attach | check |
| 14 | 15 clocks of SE0: no reset yet | check |
| 15 | one reset | check |
| 16 | packets every 21 clocks keep L0 | check |
| 17 | 23 idle clocks: L0 | check |
| 18 | 24 idle clocks: L2 (HS kept) | check |
| 19 | native mode: SE1 is not a control message | check |
| 20 | 3 clocks of K: no resume | check |
| 21 | K for 4 clocks: RESUME | check |
| 22 | L2 resume lasts 8 clocks | check |
| 23 | back to L0 at HS | check |
| 24 | LPM while busy: NYET, stay L0 | check |
| 25 | LPM answer is one clock | check |
| 26 | LPM: ACK, L1 | check |
| 27 | L1 does not time out to L2 | check |
| 28 | remote wake allowed by the LPM token: RWAKE | check |
| 29 | device K for 6 clocks, then L0 | check |
| 30 | wake K ends | check |
| 31 | second LPM: L1 | check |
| 32 | remote wake not allowed by this LPM: stays L1 | check |
| 33 | host K: RESUME | check |
| 34 | L1 resume with BESL 5: 14 clocks | check |
| 35 | L0 after 4 + 2 * BESL clocks | check |
| 36 | idle: L2 again | check |
| 37 | remote wake not enabled: stays L2 | check |
| 38 | DEVICE_REMOTE_WAKEUP set: RWAKE from L2 | check |
| 39 | L0 after the wake | check |
| 40 | SE0 in L1: reset, HS cleared | check |
| 41 | no HS capability: L0 at FS without a chirp | check |
| 42 | no host chirp: still waiting after 47 clocks | check |
| 43 | 48 clocks without a host chirp: L0 at FS | check |
| 44 | 1-clock K/J levels: FS | check |
| 45 | reset counted | check |
| 46 | SE0 held through RESET into L0: no second reset | check |
| 47 | disconnect in L0: DISC | check |
| 48 | repeater mode: attach | check |
| 49 | repeater mode: SE0 is not a reset | check |
| 50 | CM.RESET not decoded before its 4-clock end gap | check |
| 51 | CM.RESET: RESET | check |
| 52 | repeater: HS after the chirp | check |
| 53 | CM.SUSPEND: L2 | check |
| 54 | repeater mode: K does not resume | check |
| 55 | CM.RESUME: RESUME | check |
| 56 | L0 | check |
| 57 | CM.RESUME in L0: bad control message | check |
| 58 | 6 pulses: unknown control message | check |
| 59 | long SE1 pulses count once each: CM.SUSPEND | check |
| 60 | resumed | check |
| 61 | RAP read ID: 0xE2 | check |
| 62 | RAP answer is one clock | check |
| 63 | RAP read STATUS: {hs, L0} | check |
| 64 | write to the read-only ID: rejected | check |
| 65 | write to STATUS: rejected | check |
| 66 | address 9: rejected | check |
| 67 | scratch register write / read | check |
| 68 | tuning register keeps 6 bits | check |
| 69 | access 8 clocks after CM.RAP: dropped | check |
| 70 | access without CM.RAP: ignored | check |
| 71 | CTRL write keeps 3 bits | check |
| 72 | LPM disabled: STALL | check |
| 73 | CTRL = lpm_en \| rwake_en | check |
| 74 | CTRL.rwake_en: remote wake from L2 | check |
| 75 | LPM ACK: L1 | check |
| 76 | CM.RESUME from L1 | check |
| 77 | BESL 0: 4 clocks | check |
| 78 | CM.RESET | check |
| 79 | CM.SUSPEND during RESET: bad control message | check |
| 80 | CTRL.hs_dis: L0 at FS without a chirp | check |
| 81 | CM.RESET from L1 | check |
| 82 | registers survive a bus reset | check |
| 83 | rst_n clears everything | check |

### `tb/func_usb2_tb.sv`

結果：**PASS**（iverilog，230 checks）

| # | Check | 類型 |
|---|---|---|
| 1 | reset detected after 16 clocks of SE0 | check |
| 2 | device chirp K for 8 clocks | check |
| 3 | 3 host K-J pairs -> HS | check |
| 4 | : status ZLP DATA1 | check |
| 5 | enumerated: CONFIGURED | check |
| 6 | in reset: no answer, FS | check |
| 7 | after rst_n: FS, DEFAULT, address 0 | check |
| 8 | after rst_n: idle, counters 0 | check |
| 9 | 15 clocks of SE0: no reset yet | check |
| 10 | 16th clock: bus reset, FS (no hs_cap) | check |
| 11 | SE0 held on after the reset: no second reset | check |
| 12 | J then SE0 16 clocks: second reset | check |
| 13 | FS SOF: frame 5 | check |
| 14 | FS SOF: next frame, no miss | check |
| 15 | FS: repeated frame number -> sof_miss | check |
| 16 | FS: skipped frames -> sof_miss | check |
| 17 | babble counted | check |
| 18 | FS bulk IN: app length clamped to 64 | check |
| 19 | 23 idle clocks: still FS | check |
| 20 | 24 idle J clocks: suspend | check |
| 21 | 2-clock K: no resume | check |
| 22 | K >= 4 clocks then J: resume at FS, still CONFIGURED | check |
| 23 | reset returns the device to DEFAULT / address 0 | check |
| 24 | HS idle with SE0 -> reset, new chirp | check |
| 25 | no host chirp within 48 clocks: FS | check |
| 26 | 1-clock K/J levels: FS fallback | check |
| 27 | only 1.5 K-J pairs: FS fallback | check |
| 28 | address not applied before the status stage | check |
| 29 | status IN: ZLP DATA1 | check |
| 30 | address still 0 before the host ACK | check |
| 31 | status ZLP without ACK: timeout, address held | check |
| 32 | status ACK: ADDRESS 0x2A | check |
| 33 | CONFIGURED | check |
| 34 | address unchanged | check |
| 35 | GET_STATUS(device): DATA1, 2 bytes, self-powered | check |
| 36 | duplicate counted | check |
| 37 | after a new SETUP: data stage served | check |
| 38 | NYET counted | check |
| 39 | dup and NAK counted | check |
| 40 | CRC16 error counted | check |
| 41 | DATA2 counted as PID error | check |
| 42 | PID check error counted | check |
| 43 | CRC5 error counted | check |
| 44 | HS bulk IN: 600 clamped to 512, DATA0 | check |
| 45 | no host ACK: timeout | check |
| 46 | retry repeats DATA0 and the data | check |
| 47 | host NAK instead of ACK: not retired | check |
| 48 | a token instead of the ACK: not retired, served again | check |
| 49 | second packet: DATA1, 20 bytes (third app_wr dropped: FIFO full) | check |
| 50 | interrupt IN: DATA0, 4 bytes | check |
| 51 | next report: DATA1 | check |
| 52 | EP2 halted | check |
| 53 | GET_STATUS(EP2): halted | check |
| 54 | EP2 halt cleared | check |
| 55 | CLEAR_FEATURE resets the toggle to DATA0 | check |
| 56 | SET_CONFIGURATION clears halts | check |
| 57 | configuration 0: back to ADDRESS | check |
| 58 | HS: microframe advances within frame 100 | check |
| 59 | ninth microframe: sof_miss | check |
| 60 | next frame: microframe 0 | check |
| 61 | frame jump: sof_miss | check |
| 62 | frame number wraps 2047 -> 0 | check |
| 63 | SOF with bad CRC5: ignored | check |
| 64 | split completed | check |
| 65 | CSPLIT IN done: DATA0, 8 bytes | check |
| 66 | second split completed | check |
| 67 | split token CRC5 error counted once | check |
| 68 | stray data packet with a bad CRC: not counted | check |
| 69 | SOF after a SPLIT is still a SOF | check |
| 70 | HS: 23 clocks without packets | check |
| 71 | HS: 24 clocks idle with J -> suspend (FS termination) | check |
| 72 | resume K, then back to HS | check |
| 73 | suspend again | check |
| 74 | SE0 for 15 clocks in suspend: no reset yet | check |
| 75 | SE0 16 clocks in suspend: reset, chirp | check |
| 76 | HS again after the reset | check |
| 77 | reset without host chirp: FS | check |
| 78 | FS bulk IN clamp 64 | check |
| 79 | rst_n clears everything | check |

### `tb/func_usb3_tb.sv`

結果：**PASS**（iverilog，107 checks）

| # | Check | 類型 |
|---|---|---|
| 1 | %s (%0d commands) | check |
| 2 | %s: link commands (got %0d, want %0d) | check |
| 3 | %s: one header, HdrSeq %0d, CRC-16 and CRC-5 (got %0d) | check |
| 4 | in reset: RxDetect, outputs cleared | check |
| 5 | no far-end termination: stays in RxDetect | check |
| 6 | far-end termination: Polling.LFPS | check |
| 7 | 3 LFPS bursts are not enough | check |
| 8 | Polling.LFPS waits 128 clocks | check |
| 9 | Polling.LFPS timeout: back to RxDetect | check |
| 10 | 4 bursts, one without SCD2: Polling.Active at Gen1 | check |
| 11 | 7 TS1 stay in Polling.Active | check |
| 12 | 8 TS1/TS2: Polling.Configuration | check |
| 13 | TS1 does not count in Polling.Configuration | check |
| 14 | 7 TS2 stay in Polling.Configuration | check |
| 15 | 8 TS2: U0 | check |
| 16 | no header without a credit; 4 free buffers | check |
| 17 | the header used the credit | check |
| 18 | LGOOD outstanding for 4 clocks: still U0 | check |
| 19 | LGOOD_3 for header 0: Recovery | check |
| 20 | Recovery.Active 8 TS + Recovery.Configuration 8 TS2: U0 | check |
| 21 | LGOOD_0 acknowledges it | check |
| 22 | repeated LGOOD of the last acknowledged header is ignored | check |
| 23 | a good header takes a buffer | check |
| 24 | buffer still busy 3 clocks later | check |
| 25 | freed 4 clocks after it arrived | check |
| 26 | the response waits for a credit | check |
| 27 | CRC-16 error: no buffer | check |
| 28 | headers after LBAD are dropped until LRTY | check |
| 29 | TP for this device counted | check |
| 30 | TP for another address not counted | check |
| 31 | link command with a bad CRC-5 ignored | check |
| 32 | ITP timestamp latched | check |
| 33 | DPP: CRC-32 and length match the DPH | check |
| 34 | DPP with a bad CRC-32 | check |
| 35 | DPP length differs from the DPH | check |
| 36 | DPP without a DPH | check |
| 37 | 4 headers in 4 clocks: no buffer free yet | check |
| 38 | 5th header takes the buffer freed in the same clock | check |
| 39 | header with no free buffer: Recovery | check |
| 40 | app_busy: the 2 buffers stay taken | check |
| 41 | HdrSeq out of order: Recovery | check |
| 42 | LCRD out of order: Recovery | check |
| 43 | 4 credits | check |
| 44 | a 5th credit: Recovery | check |
| 45 | LBAD: the credit comes back, LRTY first | check |
| 46 | 62 clocks without LGOOD: still U0 | check |
| 47 | 64 clocks without LGOOD: Recovery | check |
| 48 | the advertisement acknowledged it: nothing resent | check |
| 49 | Set Link Function and U2 Inactivity Timeout LMPs | check |
| 50 | LPMA: U1 | check |
| 51 | U1 for 47 clocks | check |
| 52 | U2 inactivity timeout 2: U2 after (2 + 1) x 16 clocks | check |
| 53 | LFPS exits U2 through Recovery | check |
| 54 | LGO_U3, LAU, LPMA: U3 | check |
| 55 | U3 does not time out | check |
| 56 | LAU without LPMA for 31 clocks: U0 | check |
| 57 | no LPMA 32 clocks after LAU: Recovery | check |
| 58 | LGO_U0 is not a request | check |
| 59 | LPMA without LAU is ignored | check |
| 60 | a power-management command other than LPMA does not enter Ux | check |
| 61 | Recovery ends the DPP: a later DPP word has no DPH | check |
| 62 | and neither has its CRC word | check |
| 63 | LGOOD beyond the headers sent: Recovery | check |
| 64 | TS1 in U0: Recovery | check |
| 65 | TS1 with Hot Reset: Hot Reset | check |
| 66 | TS2 with Hot Reset still set | check |
| 67 | TS2 without Hot Reset: U0 | check |
| 68 | Recovery.Active waits 128 clocks | check |
| 69 | Recovery timeout: RxDetect | check |
| 70 | every burst with SCD2: Gen2 | check |
| 71 | a credit in the first U0 clock sends the header in that clock | check |
| 72 | Gen2: 1-bit block header corrected, 2-bit and wrong-kind blocks dropped (%0d %0d %0d st%0d free%0d) | check |
| 73 | TS1 in a data block: dropped | check |
| 74 | TS1 with a 1-bit control header: corrected, Recovery | check |
| 75 | Gen2: a DPP word in a dropped block spoils the DPP | check |
| 76 | Gen2: a corrected block keeps the DPP | check |
| 77 | Gen2: a dropped DPP word spoils it even when length and CRC fit the rest | check |
| 78 | reset clears the link | check |

### `tb/func_usb4_tb.sv`

結果：**PASS**（iverilog，213 checks）

| # | Check | 類型 |
|---|---|---|
| 1 | %s: ordered set lane %0d kind %0d (got %0d, %0d queued) | check |
| 2 | : no packet | check |
| 3 | %s: header %08h (want PDF %0h hop %03h %0d words), %0d words, w0 %08h w1 %08h w2 %08h | check |
| 4 | %s: route %08h word1 %08h (want %08h), CRC %08h (want %08h) | check |
| 5 | %s: data %0d = %08h (want %08h) | check |
| 6 | %s: Notification code %0d (got %08h) | check |
| 7 | %s: nothing sent (%0d packets) | check |
| 8 | in reset: both lanes CLd, nothing sent | check |
| 9 | no lane detected: CLd | check |
| 10 | lane 0 detected: Lock | check |
| 11 | SLOS interrupted: still Lock | check |
| 12 | two SLOS in a row: Training.TS1 | check |
| 13 | TS1 interrupted: still TS1 | check |
| 14 | TS1 without the Gen 3 bit: Gen 2 | check |
| 15 | TS2 interrupted by SLOS: still TS2 | check |
| 16 | two TS2 (a late TS1 between them is tolerated): CL0, one lane | check |
| 17 | one answer per training step | check |
| 18 | lane 1 detected: Lock | check |
| 19 | 62 clocks after the last SLOS: still Lock | check |
| 20 | 64 clocks without progress: training timeout | check |
| 21 | lane still detected: Lock again | check |
| 22 | lane 1 not detected: CLd | check |
| 23 | retransmission counted | check |
| 24 | 6 notifications | check |
| 25 | CRC error counted | check |
| 26 | HEC error counted | check |
| 27 | length errors counted | check |
| 28 | forward counted | check |
| 29 | unknown HopID counted | check |
| 30 | 5th packet with 4 buffers held: overflow | check |
| 31 | Gen 2: no correction | check |
| 32 | CLD ordered set: lane 0 down | check |
| 33 | TS1 with the Gen 3 bit: Gen 3 | check |
| 34 | 2 corrections, nothing lost | check |
| 35 | 3 uncorrectable packets: still CL0 | check |
| 36 | 4th uncorrectable packet: retrain from Lock | check |
| 37 | count restarts at CL0 entry | check |
| 38 | local port without Gen 3: Gen 2 even if the far end has it | check |
| 39 | lane 1 down: width 1 | check |
| 40 | both lanes CL0: bonded, width 2 | check |
| 41 | lane 1 CLD: width 1 | check |
| 42 | bonding disabled: width 1 | check |
| 43 | still CL0 | check |
| 44 | CL_REQ on lane 1: ignored | check |
| 45 | both lanes in CLx | check |
| 46 | no forward in CLx | check |
| 47 | WAKE on lane 0: Training.TS2 | check |
| 48 | both lanes CL0 again | check |
| 49 | lane 0 not detected: CLd, lane 1 stays | check |
| 50 | lane 0 down: nothing received | check |
| 51 | reset clears the adapter | check |
| 52 | every sent packet framed by first / last | check |
| 53 | nothing sent outside CL0 | check |

### `tb/func_usb_pd_tb.sv`

結果：**PASS**（iverilog，264 checks）

| # | Check | 類型 |
|---|---|---|
| 1 | %s: no packet from the sink | check |
| 2 | %s: type %0d ndo %0d id %0d (got kind %0d crc %0d hdr %04h obj %08h) | check |
| 3 | %s: Hard Reset ordered set | check |
| 4 | %s: nothing sent (%0d packets) | check |
| 5 | %s: GoodCRC starts 3 clocks after EOP (%0d) | check |
| 6 | : waiting for the response | check |
| 7 | : Transition_Sink | check |
| 8 | %s: explicit contract at %0d mV (pos %0d) | check |
| 9 | in reset: disabled, outputs cleared | check |
| 10 | no VBUS: disabled | check |
| 11 | VBUS: Wait_for_Capabilities at vSafe5V | check |
| 12 | SinkWaitCap: 399 clocks, still waiting | check |
| 13 | SinkWaitCap timeout: Hard Reset 1 (pe %0d hr %0d) | check |
| 14 | Hard Reset lasts 20 clocks | check |
| 15 | then Wait_for_Capabilities | check |
| 16 | second timeout: Hard Reset 2 | check |
| 17 | nHardResetCount reached: Error, no third Hard Reset | check |
| 18 | VBUS removed: disabled | check |
| 19 | VBUS back: Wait_for_Capabilities | check |
| 20 | 3 messages received, none bad, MessageIDCounter 1 | check |
| 21 | Ping: still Ready | check |
| 22 | Sink_Capabilities acknowledged: Ready, MessageIDCounter 2 | check |
| 23 | same MessageID again: duplicate, GoodCRC only | check |
| 24 | bad CRC, invalid symbol, odd nibbles, wrong length, over 34 bytes: dropped (%0d) | check |
| 25 | SOP' and SOP'' are for the cable | check |
| 26 | SOP' with one K-code wrong (3 of 4): still SOP' | check |
| 27 | Cable Reset is not for this port | check |
| 28 | Reject: Ready, 20 V contract kept | check |
| 29 | Wait: Ready | check |
| 30 | after Not_Supported: Ready | check |
| 31 | waiting for GoodCRC of Soft_Reset | check |
| 32 | Soft_Reset sent: waiting for Accept, MessageIDCounter 1 | check |
| 33 | Soft_Reset done: Wait_for_Capabilities, contract dropped | check |
| 34 | Soft_Reset accepted: Wait_for_Capabilities | check |
| 35 | nRetryCount = 2 | check |
| 36 | Request never acknowledged: Hard Reset | check |
| 37 | Hard Reset clears MessageIDCounter and the contract | check |
| 38 | GoodCRC on the 2nd try: MessageIDCounter 1 | check |
| 39 | SenderResponse: 99 clocks | check |
| 40 | no Accept within SenderResponse: Hard Reset | check |
| 41 | PSTransition: still waiting | check |
| 42 | no PS_RDY within PSTransition: Hard Reset | check |
| 43 | Transition_Sink | check |
| 44 | data message with the PS_RDY type code in Transition_Sink: Hard Reset | check |
| 45 | no Accept for the Soft_Reset: Hard Reset | check |
| 46 | Hard Reset received: contract dropped, vSafe5V | check |
| 47 | after Hard Reset: Wait_for_Capabilities, one Hard Reset | check |
| 48 | Soft_Reset never acknowledged: Hard Reset | check |
| 49 | VBUS lost: disabled | check |
| 50 | VBUS back: Wait_for_Capabilities | check |
| 51 | reset clears the port | check |
| 52 | reset with VBUS: Wait_for_Capabilities | check |
| 53 | Reject with no prior contract: Wait_for_Capabilities | check |
| 54 | MessageIDCounter after two Not_Supported | check |
| 55 | Not_Supported failed: Send_Soft_Reset | check |
| 56 | Soft_Reset acknowledged: waiting for Accept | check |
| 57 | Soft_Reset done | check |
| 58 | Accept never acknowledged: Hard Reset | check |
| 59 | every symbol the sink sent was a 4b5b code | check |

## 3. UVM 測試平台內容

UVM 測試需商用模擬器（VCS / Xcelium / Questa）執行；開源流程只做 elaboration（L1a）。

| 項目 | 數量 | 名稱 |
|---|---|---|
| UVM tests | 16 | `usb_base_test`, `usb_random_regression_test`, `usb_directed_test`, `usb_hs_test`, `usb_ss_test`, `usb_ssp_test`, `usb_ss20_test`, `usb4_test`, `usb_eusb2_test`, `usb_pd_test`, `eusb2_link_test`, `usb_family_test`, `usb2_link_test`, `usb3_link_test`, `usb4_link_test`, `usb_pd_link_test` |
| Sequences | 27 | `usb_base_sequence`, `usb_normal_seq`, `usb_error_inject_seq`, `usb_reset_seq`, `usb_back_to_back_seq`, `usb_stress_seq`, `usb_corner_seq`, `usb_sof_seq`, `usb_random_sequence`, `usb_regression_sequence`, `usb_directed_regression_sequence`, `usb_sequence_item`, `eusb2_item`, `eusb2_base_seq`, `eusb2_regression_seq`, `usb2_item`, `usb2_base_seq`, `usb2_regression_seq`, `usb3_item`, `usb3_base_seq` |
| SVA（assert / cover property） | 32 / 77 | `LBL`, `c_hs`, `c_fs`, `c_l1`, `c_l2`, `c_l1_wake`, `c_l2_wake`, `c_nyet`, `c_stall`, `c_rap_ok`, `c_rap_bad`, `c_cm_bad` … |
| Covergroups / coverpoints | 30 / 73 | |

## 4. 充分度判定與缺口

判定：**✅ Sufficient**（902 個 check，mutation score 100%）。

無已知缺口。

