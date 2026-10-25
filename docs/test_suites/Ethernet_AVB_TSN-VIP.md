# Ethernet-AVB-TSN 測試套件（Ethernet_AVB_TSN-VIP）

> 由 `tools/gen_test_suite_docs.py` 依 VIP 內容、`func_report.csv` 與 `mutation_report.csv` 自動產生，請勿手動修改。

## 1. 概要

| 項目 | 內容 |
|---|---|
| 類別 | Automotive |
| 類型 | UVM VIP |
| 功能測試 | 1 個檔案，21 個 check，全部通過 |
| Mutation | 24/30 個 mutant 被偵測（80%） |
| 判定 | **✅ Sufficient**（21 個 check，mutation score 80%） |

## 2. 可執行的功能測試

執行：`python3 tools/run_func_tests.py Ethernet_AVB_TSN-VIP`（Icarus Verilog 或 Verilator 5.052）。

### `tb/func_avb_tsn_tb.sv`

結果：**PASS**（iverilog，21 checks）

模型合約與範圍（摘自測試檔頭）：

```text
func_avb_tsn_tb.sv -- self-checking functional test for the AVB/TSN bridge
model (eth_avb_tsn_dut, flattened by smoke/flatten.py).
Run: python3 tools/run_func_tests.py Ethernet_AVB_TSN-VIP

Model contract (from tb/top_tb.sv):
   gPTP time base: local_clock (reset 1_0000_0000h) and ts_nsec advance
   8 ns per clock, ts_nsec wraps into ts_sec at 1 s; sync_valid pulses
   every 1024 clocks, ptp_pulse 512 clocks later.
   Store-and-forward: rx_ready = (rx_gate_ctrl != 0) && egress idle. A
   frame starts with rx_sof and ends when rx_valid drops; it is then sent
   on tx in 8-byte beats (tx_sof first, tx_eof last, tx_data_valid FFh)
   after a fixed delay, with tx_gate_state = the gate control at that time.
   Not modelled: Qbv gate scheduling, credit-based shaping, preemption.
```

| # | Check | 類型 |
|---|---|---|
| 1 | reset: clocks at their reset values, no tx, gates open | check |
| 2 | local_clock and ts_nsec advance 8 ns per clock | check |
| 3 | sync_valid every 1024 clocks, ptp_pulse 512 clocks after it (single-clock pulses) | check |
| 4 | ts_sec increments at the 1 s boundary | check |
| 5 | ts_nsec stays below 1e9 and advances 8 ns per clock across the second | XFAIL（模型缺陷） |
| 6 | 4-beat frame forwarded intact, SOF / EOF on the first / last beat | check |
| 7 | tx_data_valid = FFh on every beat | check |
| 8 | tx_gate_state reports the gate control of the forwarded frame | check |
| 9 | fixed store-and-forward delay: tx SOF 10 clocks after the last rx beat | check |
| 10 | single-beat frame forwarded with SOF and EOF together | check |
| 11 | 32-beat frame forwarded intact | check |
| 12 | beats without a preceding SOF are dropped | check |
| 13 | all gates closed: rx_ready low | check |
| 14 | frame held off while the gates are closed | check |
| 15 | frame accepted and forwarded once a gate opens | check |
| 16 | rx_ready low while the previous frame is being forwarded | check |
| 17 | frame sent during egress is accepted afterwards | check |
| 18 | back-to-back frames (SOF directly after the last beat) both forwarded | XFAIL（模型缺陷） |
| 19 | frame interrupted by gate closure is not forwarded truncated | XFAIL（模型缺陷） |
| 20 | reset stops forwarding and reloads the time base | check |
| 21 | no stale frame after reset | check |

## 3. UVM 測試平台內容

UVM 測試需商用模擬器（VCS / Xcelium / Questa）執行；開源流程只做 elaboration（L1a）。

| 項目 | 數量 | 名稱 |
|---|---|---|
| UVM tests | 8 | `base_test`, `avb_stream_test`, `tsn_preempt_test`, `ptp_sync_test`, `error_inject_test`, `gate_control_test`, `corner_test`, `regression_test` |
| Sequences | 23 | `base_tx`, `eth_avb_tsn_base_sequence`, `eth_avb_tsn_random_sequence`, `eth_avb_stream_sequence`, `eth_tsn_preempt_sequence`, `eth_ptp_sync_sequence`, `eth_vlan_sequence`, `eth_error_inject_sequence`, `eth_avb_tsn_transaction`, `eth_avb_tsn_base_sequence`, `eth_avb_tsn_random_sequence`, `eth_avb_stream_sequence`, `eth_tsn_preempt_sequence`, `eth_ptp_sync_sequence`, `eth_vlan_sequence`, `eth_error_inject_sequence`, `eth_back_to_back_sequence`, `eth_max_frame_sequence`, `eth_min_frame_sequence`, `eth_reset_sequence` |
| SVA（assert / cover property） | 59 / 59 | `assert_p_avb_pcp`, `cover_p_avb_pcp`, `assert_p_avb_vid`, `cover_p_avb_vid`, `assert_p_avb_sr_class`, `cover_p_avb_sr_class`, `assert_p_avb_ethertype`, `cover_p_avb_ethertype`, `assert_p_avb_fcs`, `cover_p_avb_fcs`, `assert_p_avb_stream`, `cover_p_avb_stream` … |
| Covergroups / coverpoints | 5 / 25 | |

## 4. 充分度判定與缺口

判定：**✅ Sufficient**（21 個 check，mutation score 80%）。

未被偵測的 mutant（測試缺口或等價 mutant）：

- `dut_eth_avb_tsn_dut.sv:41 0 -> 1 [gptp_cnt        <= 0;]`
- `dut_eth_avb_tsn_dut.sv:46 1'b0 inverted [vif_ptp_pulse   <= 1'b0;]`
- `dut_eth_avb_tsn_dut.sv:94 0 -> 1 [eg_total          <= 0;]`
- `dut_eth_avb_tsn_dut.sv:106 1'b0 inverted [vif_tx_eof   <= 1'b0;]`
- `dut_eth_avb_tsn_dut.sv:127 8 -> 9 [n = (eg_total - eg_idx < 8) ? (eg_total - eg_idx) : 8;]`
- `dut_eth_avb_tsn_dut.sv:127 < -> <= in condition [n = (eg_total - eg_idx < 8) ? (eg_total - eg_idx) : 8;]`

DUT 模型缺陷（XFAIL check，修好模型後會變成 XPASS 提醒移除標記）：

- ts_nsec stays below 1e9 and advances 8 ns per clock across the second
- back-to-back frames (SOF directly after the last beat) both forwarded
- frame interrupted by gate closure is not forwarded truncated

模型未實作的功能（不在測試範圍）：

- Not modelled: Qbv gate scheduling, credit-based shaping, preemption.

