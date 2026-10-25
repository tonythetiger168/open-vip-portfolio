# Ethernet 測試套件（Ethernet-VIP）

> 由 `tools/gen_test_suite_docs.py` 依 VIP 內容、`func_report.csv` 與 `mutation_report.csv` 自動產生，請勿手動修改。

## 1. 概要

| 項目 | 內容 |
|---|---|
| 類別 | Networking |
| 類型 | UVM VIP |
| 功能測試 | 2 個檔案，37 個 check，全部通過 |
| Mutation | 24/26 個 mutant 被偵測（92%） |
| 判定 | **✅ Sufficient**（37 個 check，mutation score 92%） |

## 2. 可執行的功能測試

執行：`python3 tools/run_func_tests.py Ethernet-VIP`（Icarus Verilog 或 Verilator 5.052）。

### `tb/func_ethernet_tb.sv`

結果：**PASS**（iverilog，18 checks）

| # | Check | 類型 |
|---|---|---|
| 1 | link down and not ready in reset | check |
| 2 | status flags clear in reset | check |
| 3 | link training: DOWN 6, ANEG 10, TRAIN 10 clocks (%0d+1/%0d/%0d) | check |
| 4 | ready one clock after link up | check |
| 5 | ready with link up | check |
| 6 | link stays up | check |
| 7 | 64-byte frame over 2 beats (partial BE): crc_ok | check |
| 8 | fcs_valid is a one-clock pulse | check |
| 9 | corrupted FCS: crc_error, crc_ok cleared | check |
| 10 | 56-byte frame (under the 64-byte minimum) gives len_error | check |
| 11 | 48-byte frame gives len_error | check |
| 12 | PAUSE frame drops ready for 4 clocks (%0d) | check |
| 13 | PAUSE frame itself is a good frame | check |
| 14 | 40 random multi-beat frames with gaps: one fcs_valid each, CRC verdict correct | check |
| 15 | no len_error for frames of 64 bytes or more | check |
| 16 | stray beat outside a frame does not corrupt the next frame | check |
| 17 | framing / FEC / FCS error flags stay low | check |
| 18 | reset drops link, ready and crc_ok | check |

### `tb/smoke_func_tb.sv`

結果：**PASS**（iverilog，19 checks）

| # | Check | 類型 |
|---|---|---|
| 1 | ready low out of reset | check |
| 2 | link down out of reset | check |
| 3 | flags quiet out of reset | check |
| 4 | link came up after training | check |
| 5 | passed through autonegotiation | check |
| 6 | passed through training | check |
| 7 | ready high with link up | check |
| 8 | fcs_valid strobe at end of frame | check |
| 9 | good frame CRC accepted | check |
| 10 | no error flags on good frame | check |
| 11 | no pause for ethertype 0x0800 | check |
| 12 | pause frame still CRC-valid | check |
| 13 | pause frame dropped ready for 4 cycles | check |
| 14 | fcs_valid on short frame | check |
| 15 | short frame raised len_error | check |
| 16 | short frame not CRC-ok | check |
| 17 | fcs_valid on bad frame | check |
| 18 | corrupted FCS raised crc_error | check |
| 19 | bad frame not CRC-ok | check |

## 3. UVM 測試平台內容

UVM 測試需商用模擬器（VCS / Xcelium / Questa）執行；開源流程只做 elaboration（L1a）。

| 項目 | 數量 | 名稱 |
|---|---|---|
| UVM tests | 17 | `net_base_test`, `net_ethernet_100g_test`, `net_eth_100g_test`, `net_ethernet_1g_test`, `net_eth_1g_test`, `net_ethernet_1p6t_test`, `net_eth_1p6t_test`, `net_ethernet_400g_test`, `net_eth_400g_test`, `net_ethernet_800g_test`, `net_eth_800g_test`, `net_fc_test`, `net_fc_cls3_test`, `net_random_regression_test`, `net_rand_reg_test`, `net_uec_test`, `net_uec_ai_test` |
| Sequences | 12 | `net_base_sequence`, `net_unicast_sequence`, `net_vlan_sequence`, `net_pause_sequence`, `net_random_sequence`, `net_back_to_back_sequence`, `net_max_frame_sequence`, `net_error_inject_sequence`, `net_reset_sequence`, `net_stress_sequence`, `net_regression_sequence`, `net_sequence_item` |
| SVA（assert / cover property） | 37 / 19 | `assert_valid_ready`, `assert_sop_eop`, `assert_link_state`, `assert_fcs_check`, `assert_p_eth_preamble`, `cover_p_eth_preamble`, `assert_p_eth_sfd`, `cover_p_eth_sfd`, `assert_p_eth_fcs_valid`, `cover_p_eth_fcs_valid`, `assert_p_eth_speed_valid`, `cover_p_eth_speed_valid` … |
| Covergroups / coverpoints | 5 / 14 | |

## 4. 充分度判定與缺口

判定：**✅ Sufficient**（37 個 check，mutation score 92%）。

未被偵測的 mutant（測試缺口或等價 mutant）：

- `dut_net_mac_model.sv:117 0 -> 1 [in_frame <= 0;]`
- `dut_net_mac_model.sv:132 && flipped [if (frame_q.size() > 22 && frame_q[20] == 8'h88 && frame_q[2]`

