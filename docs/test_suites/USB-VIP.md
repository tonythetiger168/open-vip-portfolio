# USB 測試套件（USB-VIP）

> 由 `tools/gen_test_suite_docs.py` 依 VIP 內容、`func_report.csv` 與 `mutation_report.csv` 自動產生，請勿手動修改。

## 1. 概要

| 項目 | 內容 |
|---|---|
| 類別 | USB |
| 類型 | UVM VIP |
| 功能測試 | 1 個檔案，29 個 check，全部通過 |
| Mutation | 26/30 個 mutant 被偵測（87%） |
| 判定 | **✅ Sufficient**（29 個 check，mutation score 87%） |

## 2. 可執行的功能測試

執行：`python3 tools/run_func_tests.py USB-VIP`（Icarus Verilog 或 Verilator 5.052）。

### `tb/func_usb_tb.sv`

結果：**PASS**（iverilog，29 checks）

| # | Check | 類型 |
|---|---|---|
| 1 | reset state | check |
| 2 | mac_ready follows mac_valid | check |
| 3 | mac_ready drops with mac_valid | check |
| 4 | SETUP+DATA0 to address 0 is ACKed and assigns address 0x15 | check |
| 5 | accepted DATA0 flips the toggle to DATA1 | check |
| 6 | token to address 0 is ignored once addressed (data in IDLE not taken) | check |
| 7 | token to another address is ignored | check |
| 8 | OUT DATA1 ACKed, toggle back to DATA0 | check |
| 9 | retransmitted DATA1 (toggle mismatch) ACKed without flipping | check |
| 10 | next DATA0 ACKed and flips | check |
| 11 | bad CRC NAKed, nak_count++, toggle kept | check |
| 12 | halted endpoint 15 returns STALL | check |
| 13 | still waiting for data 15 clocks after OUT | check |
| 14 | missing data phase times out with NAK | check |
| 15 | a token in the data phase aborts back to idle | check |
| 16 | IN token raises tx_valid | check |
| 17 | host ACK ends the IN and flips the toggle | check |
| 18 | next IN offers a new data byte | check |
| 19 | host NAK ends the IN without flipping | check |
| 20 | tx_valid held while waiting for the handshake | check |
| 21 | IN without handshake times out | check |
| 22 | SOF sets frame_num from the token fields | check |
| 23 | SOF uses endpoint bits [2:0] as frame[2:0] | check |
| 24 | toggle at DATA1 before SETUP | check |
| 25 | SETUP resets the toggle to DATA0 | check |
| 26 | second SETUP moves to CONFIGURED | check |
| 27 | SETUP data with bad CRC NAKed, address kept | check |
| 28 | promiscuous mode takes a token to any address | check |
| 29 | reset returns to DEFAULT, address 0 | check |

## 3. UVM 測試平台內容

UVM 測試需商用模擬器（VCS / Xcelium / Questa）執行；開源流程只做 elaboration（L1a）。

| 項目 | 數量 | 名稱 |
|---|---|---|
| UVM tests | 10 | `usb_base_test`, `usb_random_regression_test`, `usb_directed_test`, `usb_hs_test`, `usb_ss_test`, `usb_ssp_test`, `usb_ss20_test`, `usb4_test`, `usb_eusb2_test`, `usb_pd_test` |
| Sequences | 12 | `usb_base_sequence`, `usb_normal_seq`, `usb_error_inject_seq`, `usb_reset_seq`, `usb_back_to_back_seq`, `usb_stress_seq`, `usb_corner_seq`, `usb_sof_seq`, `usb_random_sequence`, `usb_regression_sequence`, `usb_directed_regression_sequence`, `usb_sequence_item` |
| SVA（assert / cover property） | 27 / 19 | `assert_p_usb_pid_valid`, `cover_p_usb_pid_valid`, `assert_p_usb_token_crc5`, `cover_p_usb_token_crc5`, `assert_p_usb_data_crc16`, `cover_p_usb_data_crc16`, `assert_p_usb_addr_range`, `cover_p_usb_addr_range`, `assert_p_usb_ep_range`, `cover_p_usb_ep_range`, `assert_p_usb_sop_eop`, `cover_p_usb_sop_eop` … |
| Covergroups / coverpoints | 14 / 49 | |

## 4. 充分度判定與缺口

判定：**✅ Sufficient**（29 個 check，mutation score 87%）。

未被偵測的 mutant（測試缺口或等價 mutant）：

- `dut_usb_smoke_model.sv:59 == flipped [((mac_addr == 7'h00) && (dev_addr == 7'h00));]`
- `dut_usb_smoke_model.sv:62 && flipped [wire pid_is_hs    = mac_valid && (mac_pid[1:0] == PID_CLS_HS]`
- `dut_usb_smoke_model.sv:71 1'b0 inverted [setup_pending <= 1'b0;]`
- `dut_usb_smoke_model.sv:129 1'b0 inverted [setup_pending <= 1'b0;]`

