# FC 測試套件（FC-VIP）

> 由 `tools/gen_test_suite_docs.py` 依 VIP 內容、`func_report.csv` 與 `mutation_report.csv` 自動產生，請勿手動修改。

## 1. 概要

| 項目 | 內容 |
|---|---|
| 類別 | Networking |
| 類型 | UVM VIP |
| 功能測試 | 1 個檔案，30 個 check，全部通過 |
| Mutation | 12/12 個 mutant 被偵測（100%） |
| 判定 | **✅ Sufficient**（30 個 check，mutation score 100%） |

## 2. 可執行的功能測試

執行：`python3 tools/run_func_tests.py FC-VIP`（Icarus Verilog 或 Verilator 5.052）。

### `tb/func_fc_tb.sv`

結果：**PASS**（verilator，30 checks）

| # | Check | 類型 |
|---|---|---|
| 1 | reference CRC-32 check value 0xCBF43926 | check |
| 2 | reset: link down, no credit ready, no R_RDY | check |
| 3 | virtual channel 0 | check |
| 4 | link state goes DOWN -> ANEG -> TRAINING -> UP | check |
| 5 | auto-negotiation and training last 8 clocks each | check |
| 6 | link leaves DOWN on the 6th clock after reset release | check |
| 7 | ready / credit_rdy / fc_rdy high once the link is up | check |
| 8 | 40-byte frame: one fcs_valid, crc_ok, no errors | check |
| 9 | second identical frame with a correct CRC accepted | check |
| 10 | 2084-byte frame with idle gaps: crc_ok | check |
| 11 | partial last beat (be = 0x03) honoured | check |
| 12 | corrupted CRC: crc_error pulse, crc_ok low | check |
| 13 | fcs_valid / crc_error are single-clock pulses | check |
| 14 | 32-byte frame (< 36) raises len_error | check |
| 15 | crc_ok recovers on the next good frame | check |
| 16 | 2152-byte frame: CRC still checked (good) | check |
| 17 | frame longer than 2148 bytes raises len_error | check |
| 18 | 2144-byte frame (within 2148): no len_error | check |
| 19 | EOP without SOP raises framing_error | check |
| 20 | EOP without SOP is not evaluated as a frame | check |
| 21 | fcs_error / fec_uncorrectable stay low | check |
| 22 | next frame (SOP) clears framing_error | check |
| 23 | 4 frames consume credits | check |
| 24 | 4 back-to-back SOPs exhaust BB_Credit: ready low | check |
| 25 | no SOP accepted with zero credit | check |
| 26 | 4 R_RDY pulses, 8 clocks apart, return the credits | check |
| 27 | all credits restored | check |
| 28 | frame without fc_valid consumes no credit | check |
| 29 | credit consumed in the R_RDY clock is counted (3 left) | check |
| 30 | reset drops the link, clears crc_ok and restores credits | check |

## 3. UVM 測試平台內容

UVM 測試需商用模擬器（VCS / Xcelium / Questa）執行；開源流程只做 elaboration（L1a）。

| 項目 | 數量 | 名稱 |
|---|---|---|
| UVM tests | 17 | `net_base_test`, `net_ethernet_100g_test`, `net_eth_100g_test`, `net_ethernet_1g_test`, `net_eth_1g_test`, `net_ethernet_1p6t_test`, `net_eth_1p6t_test`, `net_ethernet_400g_test`, `net_eth_400g_test`, `net_ethernet_800g_test`, `net_eth_800g_test`, `net_fc_test`, `net_fc_cls3_test`, `net_random_regression_test`, `net_rand_reg_test`, `net_uec_test`, `net_uec_ai_test` |
| Sequences | 14 | `net_base_sequence`, `net_unicast_sequence`, `net_vlan_sequence`, `net_pause_sequence`, `net_fc_class3_sequence`, `net_fc_els_sequence`, `net_random_sequence`, `net_back_to_back_sequence`, `net_max_frame_sequence`, `net_error_inject_sequence`, `net_reset_sequence`, `net_stress_sequence`, `net_regression_sequence`, `net_sequence_item` |
| SVA（assert / cover property） | 37 / 19 | `assert_valid_ready`, `assert_sop_eop`, `assert_link_state`, `assert_fcs_check`, `assert_p_fc_sof`, `cover_p_fc_sof`, `assert_p_fc_eof`, `cover_p_fc_eof`, `assert_p_fc_crc_valid`, `cover_p_fc_crc_valid`, `assert_p_fc_speed`, `cover_p_fc_speed` … |
| Covergroups / coverpoints | 5 / 14 | |

## 4. 充分度判定與缺口

判定：**✅ Sufficient**（30 個 check，mutation score 100%）。

無已知缺口。

