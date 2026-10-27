# USB2 測試套件（USB2-VIP）

> 由 `tools/gen_test_suite_docs.py` 依 VIP 內容、`func_report.csv` 與 `mutation_report.csv` 自動產生，請勿手動修改。

## 1. 概要

| 項目 | 內容 |
|---|---|
| 類別 | USB |
| 類型 | UVM VIP |
| 功能測試 | 1 個檔案，21 個 check，全部通過 |
| Mutation | 28/28 個 mutant 被偵測（100%） |
| 判定 | **✅ Sufficient**（21 個 check，mutation score 100%） |

## 2. 可執行的功能測試

執行：`python3 tools/run_func_tests.py USB2-VIP`（Icarus Verilog 或 Verilator 5.052）。

### `tb/smoke_func_tb.sv`

結果：**PASS**（iverilog，21 checks）

| # | Check | 類型 |
|---|---|---|
| 1 | reset: no IN data, no handshake | check |
| 2 | reset: DEFAULT state, addr 0, DATA0 expected | check |
| 3 | SOF updates frame_num | check |
| 4 | SOF produces no handshake | check |
| 5 | unaddressed device ignores a foreign address | check |
| 6 | SETUP resets data toggle to DATA0 | check |
| 7 | SETUP data stage ACKed | check |
| 8 | SET_ADDRESS accepted: addr=5, state=ADDRESS | check |
| 9 | OUT DATA0 ACKed | check |
| 10 | toggle flipped to DATA1 after accept | check |
| 11 | duplicate DATA0 ACKed without toggle flip | check |
| 12 | DATA1 accepted, toggle back to DATA0 | check |
| 13 | bad CRC: NAK, toggle held, nak_count=1 | check |
| 14 | endpoint 0xF STALLs | check |
| 15 | IN token: tx_valid=1, first payload byte | check |
| 16 | handshake PID without pid_valid ignored | check |
| 17 | tx_valid drops on the clock that takes the host ACK | check |
| 18 | host ACK consumed data: tx_valid cleared, toggle flipped | check |
| 19 | foreign address ignored (state untouched) | check |
| 20 | address-0 token ignored after SET_ADDRESS | check |
| 21 | DATA PID without pid_valid ignored; the valid DATA1 is ACKed | check |
| 22 | second SET_ADDRESS: state=CONFIGURED, toggle DATA1 | check |
| 23 | token during the data phase aborts the OUT (and is not decoded as SOF) | check |
| 24 | DATA without a token is ignored | check |
| 25 | data-phase timeout not yet expired | check |
| 26 | data-phase timeout: NAK, nak_count=2, toggle held | check |
| 27 | second IN: next payload byte | check |
| 28 | host NAK: tx_valid cleared, toggle held | check |
| 29 | IN still waiting for the handshake | check |
| 30 | IN timeout: tx_valid cleared, toggle held | check |

## 3. UVM 測試平台內容

UVM 測試需商用模擬器（VCS / Xcelium / Questa）執行；開源流程只做 elaboration（L1a）。

| 項目 | 數量 | 名稱 |
|---|---|---|
| UVM tests | 10 | `usb_base_test`, `usb_random_regression_test`, `usb_directed_test`, `usb_hs_test`, `usb_ss_test`, `usb_ssp_test`, `usb_ss20_test`, `usb4_test`, `usb_eusb2_test`, `usb_pd_test` |
| Sequences | 12 | `usb_base_sequence`, `usb_normal_seq`, `usb_error_inject_seq`, `usb_reset_seq`, `usb_back_to_back_seq`, `usb_stress_seq`, `usb_corner_seq`, `usb_sof_seq`, `usb_random_sequence`, `usb_regression_sequence`, `usb_directed_regression_sequence`, `usb_sequence_item` |
| SVA（assert / cover property） | 27 / 19 | `assert_p_usb2_linestate_j`, `cover_p_usb2_linestate_j`, `assert_p_usb2_rxactive`, `cover_p_usb2_rxactive`, `assert_p_usb2_op_mode`, `cover_p_usb2_op_mode`, `assert_p_usb2_xcvr_select`, `cover_p_usb2_xcvr_select`, `assert_p_usb2_utmi_txvalid`, `cover_p_usb2_utmi_txvalid`, `assert_p_usb2_linestate_se0`, `cover_p_usb2_linestate_se0` … |
| Covergroups / coverpoints | 14 / 49 | |

## 4. 充分度判定與缺口

判定：**✅ Sufficient**（21 個 check，mutation score 100%）。

無已知缺口。

