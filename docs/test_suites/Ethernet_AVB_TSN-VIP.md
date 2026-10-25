# Ethernet-AVB-TSN 測試套件（Ethernet_AVB_TSN-VIP）

> 由 `tools/gen_test_suite_docs.py` 依 VIP 內容、`func_report.csv` 與 `mutation_report.csv` 自動產生，請勿手動修改。

## 1. 概要

| 項目 | 內容 |
|---|---|
| 類別 | Automotive |
| 類型 | UVM VIP |
| 功能測試 | 1 個檔案，23 個 check，全部通過 |
| Mutation | 24/24 個 mutant 被偵測（100%） |
| 判定 | **✅ Sufficient**（23 個 check，mutation score 100%） |

## 2. 可執行的功能測試

執行：`python3 tools/run_func_tests.py Ethernet_AVB_TSN-VIP`（Icarus Verilog 或 Verilator 5.052）。

### `tb/func_avb_tsn_tb.sv`

結果：**PASS**（iverilog，23 checks）

模型合約與範圍（摘自測試檔頭）：

```text
func_avb_tsn_tb.sv -- self-checking functional test for the AVB/TSN bridge
model (eth_avb_tsn_dut, flattened by smoke/flatten.py).
Run: python3 tools/run_func_tests.py Ethernet_AVB_TSN-VIP

Model contract (from tb/top_tb.sv):
   gPTP time base: local_clock (reset 1_0000_0000h) and ts_nsec advance
   8 ns per clock, ts_nsec (always < 1e9) carries into ts_sec at 1 s; sync_valid pulses
   every 1024 clocks, ptp_pulse 512 clocks later.
   Store-and-forward: rx_ready = (rx_gate_ctrl != 0) && egress idle. A
   frame starts with rx_sof and ends when rx_valid drops (not on an
   rx_ready stall) or at the next rx_sof; it is then sent
   on tx in 8-byte beats (tx_sof first, tx_eof last, tx_data_valid FFh)
   after a fixed delay, with tx_gate_state = the gate control at that time.
   Not modelled: Qbv gate scheduling, credit-based shaping, preemption.
```

| # | Check | 類型 |
|---|---|---|
| 1 | reset: clocks at their reset values, no tx, gates open | check |
| 2 | reset: no sync / PTP pulse, no tx framing | check |
| 3 | first sync_valid on the first clock after reset (gPTP count 0) | check |
| 4 | local_clock and ts_nsec advance 8 ns per clock | check |
| 5 | sync_valid every 1024 clocks, ptp_pulse 512 clocks after it (single-clock pulses) | check |
| 6 | ts_sec increments at the 1 s boundary | check |
| 7 | ts_nsec stays below 1e9 and advances 8 ns per clock across the second | check |
| 8 | 4-beat frame forwarded intact, SOF / EOF on the first / last beat | check |
| 9 | tx_data_valid = FFh on every beat, no SOF / EOF without data | check |
| 10 | tx_gate_state reports the gate control of the forwarded frame | check |
| 11 | fixed store-and-forward delay: tx SOF 10 clocks after the last rx beat | check |
| 12 | single-beat frame forwarded with SOF and EOF together | check |
| 13 | 32-beat frame forwarded intact | check |
| 14 | beats without a preceding SOF are dropped | check |
| 15 | all gates closed: rx_ready low | check |
| 16 | frame held off while the gates are closed | check |
| 17 | frame accepted and forwarded once a gate opens | check |
| 18 | rx_ready low while the previous frame is being forwarded | check |
| 19 | frame sent during egress is accepted afterwards | check |
| 20 | back-to-back frames (SOF directly after the last beat) both forwarded | check |
| 21 | frame stalled by a gate closure is forwarded whole once the gate reopens | check |
| 22 | reset stops forwarding and reloads the time base | check |
| 23 | no stale frame after reset | check |

## 3. UVM 測試平台內容

UVM 測試需商用模擬器（VCS / Xcelium / Questa）執行；開源流程只做 elaboration（L1a）。

| 項目 | 數量 | 名稱 |
|---|---|---|
| UVM tests | 8 | `base_test`, `avb_stream_test`, `tsn_preempt_test`, `ptp_sync_test`, `error_inject_test`, `gate_control_test`, `corner_test`, `regression_test` |
| Sequences | 23 | `base_tx`, `eth_avb_tsn_base_sequence`, `eth_avb_tsn_random_sequence`, `eth_avb_stream_sequence`, `eth_tsn_preempt_sequence`, `eth_ptp_sync_sequence`, `eth_vlan_sequence`, `eth_error_inject_sequence`, `eth_avb_tsn_transaction`, `eth_avb_tsn_base_sequence`, `eth_avb_tsn_random_sequence`, `eth_avb_stream_sequence`, `eth_tsn_preempt_sequence`, `eth_ptp_sync_sequence`, `eth_vlan_sequence`, `eth_error_inject_sequence`, `eth_back_to_back_sequence`, `eth_max_frame_sequence`, `eth_min_frame_sequence`, `eth_reset_sequence` |
| SVA（assert / cover property） | 59 / 59 | `assert_p_avb_pcp`, `cover_p_avb_pcp`, `assert_p_avb_vid`, `cover_p_avb_vid`, `assert_p_avb_sr_class`, `cover_p_avb_sr_class`, `assert_p_avb_ethertype`, `cover_p_avb_ethertype`, `assert_p_avb_fcs`, `cover_p_avb_fcs`, `assert_p_avb_stream`, `cover_p_avb_stream` … |
| Covergroups / coverpoints | 5 / 25 | |

## 4. 充分度判定與缺口

判定：**✅ Sufficient**（23 個 check，mutation score 100%）。

模型未實作的功能（不在測試範圍）：

- Not modelled: Qbv gate scheduling, credit-based shaping, preemption.

