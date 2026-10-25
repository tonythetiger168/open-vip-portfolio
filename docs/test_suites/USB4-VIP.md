# USB4 測試套件（USB4-VIP）

> 由 `tools/gen_test_suite_docs.py` 依 VIP 內容、`func_report.csv` 與 `mutation_report.csv` 自動產生，請勿手動修改。

## 1. 概要

| 項目 | 內容 |
|---|---|
| 類別 | USB |
| 類型 | UVM VIP |
| 功能測試 | 1 個檔案，26 個 check，全部通過 |
| Mutation | 11/12 個 mutant 被偵測（92%） |
| 判定 | **✅ Sufficient**（26 個 check，mutation score 92%） |

## 2. 可執行的功能測試

執行：`python3 tools/run_func_tests.py USB4-VIP`（Icarus Verilog 或 Verilator 5.052）。

### `tb/func_usb4_tb.sv`

結果：**PASS**（verilator，26 checks）

| # | Check | 類型 |
|---|---|---|
| 1 | CLd after reset with 8 tunnel credits | check |
| 2 | link_disable keeps the link in CLd | check |
| 3 | inbound activity starts training | check |
| 4 | three SLOS headers are not enough | check |
| 5 | fourth SLOS header: CL0, link_ready | check |
| 6 | CL0 entry announced with a CTRL packet | check |
| 7 | CTRL echoed with the sync header inverted | check |
| 8 | DATA with good CRC looped back with data+1 | check |
| 9 | loopback data wraps at 0xFF | check |
| 10 | DATA with bad CRC answered by CTRL 0xEE, err_count++ | check |
| 11 | eight tunneled packets forwarded, credits used up | check |
| 12 | no credit: tunneled packet dropped, err_count++ | check |
| 13 | TIME_SYNC reflected and returns a credit | check |
| 14 | returned credit lets one more packet through | check |
| 15 | credit saturates at 15 | check |
| 16 | CL0 holds for 250 idle clocks | check |
| 17 | CL0 idle 256 clocks: low power | check |
| 18 | inbound traffic wakes the link to CL0 | check |
| 19 | the wake-up packet itself is not processed | check |
| 20 | link_disable in CL0 -> CLd | check |
| 21 | retrained | check |
| 22 | link_disable in low power -> CLd | check |
| 23 | training waits for SLOS | check |
| 24 | training timeout returns to CLd | check |
| 25 | link_disable aborts training | check |
| 26 | reset: CLd, credits and counters restored | check |

## 3. UVM 測試平台內容

UVM 測試需商用模擬器（VCS / Xcelium / Questa）執行；開源流程只做 elaboration（L1a）。

| 項目 | 數量 | 名稱 |
|---|---|---|
| UVM tests | 10 | `usb_base_test`, `usb_random_regression_test`, `usb_directed_test`, `usb_hs_test`, `usb_ss_test`, `usb_ssp_test`, `usb_ss20_test`, `usb4_test`, `usb_eusb2_test`, `usb_pd_test` |
| Sequences | 12 | `usb_base_sequence`, `usb_normal_seq`, `usb_error_inject_seq`, `usb_reset_seq`, `usb_back_to_back_seq`, `usb_stress_seq`, `usb_corner_seq`, `usb_sof_seq`, `usb_random_sequence`, `usb_regression_sequence`, `usb_directed_regression_sequence`, `usb_sequence_item` |
| SVA（assert / cover property） | 27 / 19 | `assert_p_usb4_sbtx_valid`, `cover_p_usb4_sbtx_valid`, `assert_p_usb4_domain_id`, `cover_p_usb4_domain_id`, `assert_p_usb4_path`, `cover_p_usb4_path`, `assert_p_usb4_router_config`, `cover_p_usb4_router_config`, `assert_p_usb4_tunnel_usb3`, `cover_p_usb4_tunnel_usb3`, `assert_p_usb4_tunnel_dp`, `cover_p_usb4_tunnel_dp` … |
| Covergroups / coverpoints | 14 / 49 | |

## 4. 充分度判定與缺口

判定：**✅ Sufficient**（26 個 check，mutation score 92%）。

未被偵測的 mutant（測試缺口或等價 mutant）：

- `dut_usb4_smoke_model.sv:100 1'b0 inverted [link_ready <= 1'b0;]`

