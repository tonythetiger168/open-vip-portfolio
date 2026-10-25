# eCPRI over Ethernet 測試套件（eCPRI-VIP）

> 由 `tools/gen_test_suite_docs.py` 依 VIP 內容、`func_report.csv` 與 `mutation_report.csv` 自動產生，請勿手動修改。

## 1. 概要

| 項目 | 內容 |
|---|---|
| 類別 | Telecom |
| 類型 | UVM VIP |
| 功能測試 | 1 個檔案，20 個 check，全部通過 |
| Mutation | 27/30 個 mutant 被偵測（90%） |
| 判定 | **✅ Sufficient**（20 個 check，mutation score 90%） |

## 2. 可執行的功能測試

執行：`python3 tools/run_func_tests.py eCPRI-VIP`（Icarus Verilog 或 Verilator 5.052）。

### `tb/func_ecpri_tb.sv`

結果：**PASS**（iverilog，20 checks）

模型合約與範圍（摘自測試檔頭）：

```text
func_ecpri_tb.sv -- self-checking functional test for the eCPRI endpoint
model (ecpri_endpoint_dut, flattened by smoke/flatten.py).
Run: python3 tools/run_func_tests.py eCPRI-VIP

Model contract (from ecpri_defs.sv / ecpri_driver.svh), 64-bit words with
valid/ready on both directions:
   frame = header {rev 1, 0, 0, msg_type[3:0], payload bytes, PC_ID, SEQ_ID},
   payload words (payload bytes / 8), FCS word {0, CRC-32 over header and
   payload, LSB byte first}. tx_ready is low one clock in five.
   A bad FCS pulses fcs_err. A Remote Memory Access request (type 4) with a
   good FCS is answered on rx: header with type 5 (same size, PC_ID,
   SEQ_ID), the payload echoed, and the response FCS.
```

| # | Check | 類型 |
|---|---|---|
| 1 | reference CRC-32 of \"12345678\" = 9AE0DAAF | check |
| 2 | reset: no response, no FCS error | check |
| 3 | tx_ready low exactly one clock in five | check |
| 4 | request (type 4): response type 5, same size/PC_ID/SEQ_ID, payload echoed, valid FCS | check |
| 5 | no FCS error on a good frame | check |
| 6 | (sender saw tx_ready back-pressure) | check |
| 7 | rx_valid drops after the response FCS word | check |
| 8 | %0d-word request answered | check |
| 9 | message types other than 4 (incl. unknown 8..F) are not answered | check |
| 10 | corrupted FCS: one fcs_err pulse | check |
| 11 | request with a bad FCS is not answered | check |
| 12 | FCS checked on IQ data frames too | check |
| 13 | next good request answered after an FCS error | check |
| 14 | rx_valid asserted without waiting for rx_ready | XFAIL（模型缺陷） |
| 15 | FCS beat held while rx_ready is low | XFAIL（模型缺陷） |
| 16 | request received while a response is pending is answered too | XFAIL（模型缺陷） |
| 17 | zero-length request is terminated by its FCS word and answered | XFAIL（模型缺陷） |
| 18 | reset clears the response path | check |
| 19 | request answered after reset | check |

## 3. UVM 測試平台內容

UVM 測試需商用模擬器（VCS / Xcelium / Questa）執行；開源流程只做 elaboration（L1a）。

| 項目 | 數量 | 名稱 |
|---|---|---|
| UVM tests | 3 | `ecpri_base_test`, `ecpri_random_test`, `ecpri_regression_test` |
| Sequences | 12 | `ecpri_base_sequence`, `ecpri_iq_data_seq`, `ecpri_cmd_seq`, `ecpri_req_rsp_seq`, `ecpri_sync_seq`, `ecpri_max_payload_seq`, `ecpri_back_to_back_seq`, `ecpri_error_inject_seq`, `ecpri_reset_seq`, `ecpri_random_sequence`, `ecpri_regression_sequence`, `ecpri_transaction` |
| SVA（assert / cover property） | 17 / 3 | `a_ecpri_l1_clk`, `a_ecpri_l1_rst`, `a_ecpri_l1_state`, `a_ecpri_l1_valid`, `a_ecpri_trans_idle`, `a_ecpri_trans_header`, `a_ecpri_trans_payload`, `a_ecpri_trans_fcs`, `a_ecpri_l3_reset_idle`, `a_ecpri_l3_valid_held`, `a_ecpri_l3_msg_start`, `a_ecpri_l3_msg_done` … |
| Covergroups / coverpoints | 3 / 8 | |

## 4. 充分度判定與缺口

判定：**✅ Sufficient**（20 個 check，mutation score 90%）。

未被偵測的 mutant（測試缺口或等價 mutant）：

- `dut_ecpri_endpoint_dut.sv:110 1'b1 inverted [vif_tx_ready <= 1'b1;]`
- `dut_ecpri_endpoint_dut.sv:114 0 -> 1 [rd_stall    <= 0;]`
- `dut_ecpri_endpoint_dut.sv:117 0 -> 1 [rsp_idx     <= 0;]`

DUT 模型缺陷（XFAIL check，修好模型後會變成 XPASS 提醒移除標記）：

- rx_valid asserted without waiting for rx_ready
- FCS beat held while rx_ready is low
- request received while a response is pending is answered too
- zero-length request is terminated by its FCS word and answered

