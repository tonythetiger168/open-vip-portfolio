# CAN 測試套件（CAN-VIP）

> 由 `tools/gen_test_suite_docs.py` 依 VIP 內容、`func_report.csv` 與 `mutation_report.csv` 自動產生，請勿手動修改。

## 1. 概要

| 項目 | 內容 |
|---|---|
| 類別 | Automotive |
| 類型 | UVM VIP |
| 功能測試 | 1 個檔案，19 個 check，全部通過 |
| Mutation | 10/10 個 mutant 被偵測（100%） |
| 判定 | **✅ Sufficient**（19 個 check，mutation score 100%） |

## 2. 可執行的功能測試

執行：`python3 tools/run_func_tests.py CAN-VIP`（Icarus Verilog 或 Verilator 5.052）。

### `tb/func_can_tb.sv`

結果：**PASS**（verilator，19 checks）

模型合約與範圍（摘自測試檔頭）：

```text
func_can_tb.sv -- self-checking functional test for the CAN node model
(tb/top_tb.sv can_node_model, flattened by smoke/flatten.py).
Run: python3 tools/run_func_tests.py CAN-VIP

The frames are built here from ISO 11898-1: SOF, identifier (11 bits, or
11 + SRR + IDE + 18 for extended), RTR, IDE/r0, r0/FDF, DLC, data, CRC-15
(x^15+x^14+x^10+x^8+x^7+x^4+x^3+1 over SOF..data), bit stuffing after 5
equal bits over SOF..CRC (a stuff bit starts the next run), then CRC
delimiter, ACK slot, ACK delimiter, 7-bit EOF and 3-bit intermission, all
recessive. 8 clocks per bit.
Model contract (from tb/top_tb.sv): the node receives a frame while
can_en, checks the CRC (crc_ok), latches id/ide/rtr/dlc/fdf, pulses sof
and re-transmits the frame on can_tx; a CRC or stuff error sends a 6-bit
dominant error flag (error_frame, error_count_rx++). The error counters
are not cleared by reset.
The receiver destuffs SOF..CRC only (a stuff bit starts the next run),
then takes CRC delimiter, ACK slot, ACK delimiter and EOF unstuffed; a
dominant delimiter/EOF bit is a form error.
```

| # | Check | 類型 |
|---|---|---|
| 1 | compliant standard frame received without error | check |
| 2 | a frame the model rejects is counted as a receive error | check |
| 3 | ID, IDE, RTR, DLC decoded, CRC good | check |
| 4 | re-transmission repeats the frame bit for bit (%0d of %0d bits) | check |
| 5 | frame accepted after the last EOF bit (%0d clocks) | check |
| 6 | crc output is the frame CRC | check |
| 7 | extended remote frame decoded | check |
| 8 | extended remote frame re-transmitted without data bytes | check |
| 9 | 8-byte extended data frame received and re-transmitted | check |
| 10 | standard remote frame, DLC 3, no data field | check |
| 11 | dominant ACK slot accepted | check |
| 12 | dominant EOF bit is a form error, frame not accepted | check |
| 13 | CRC error answered with an error flag, no re-transmission | check |
| 14 | stuff bit counted as the first bit of the next run | check |
| 15 | six equal bits: stuff error, error flag, error_count_rx++ | check |
| 16 | error flag is 6 dominant bits (%0d clocks) | check |
| 17 | error frame ends after the delimiter | check |
| 18 | node disabled: bus activity ignored | check |
| 19 | reset: idle, recessive | check |

## 3. UVM 測試平台內容

UVM 測試需商用模擬器（VCS / Xcelium / Questa）執行；開源流程只做 elaboration（L1a）。

| 項目 | 數量 | 名稱 |
|---|---|---|
| UVM tests | 5 | `base_test`, `random_test`, `can_2_0_test`, `error_inject_test`, `regression_test` |
| Sequences | 14 | `can_base_sequence`, `can_random_sequence`, `can_2_0_sequence`, `can_fd_sequence`, `can_tt_sequence`, `can_error_inject_sequence`, `can_back_to_back_sequence`, `can_remote_sequence`, `can_arbitration_sequence`, `can_reset_sequence`, `can_stress_sequence`, `can_regression_sequence`, `can_transaction`, `base_tx` |
| SVA（assert / cover property） | 34 / 31 | `assert_p_can_sof`, `cover_p_can_sof`, `assert_p_can_id_std`, `cover_p_can_id_std`, `assert_p_can_id_ext`, `cover_p_can_id_ext`, `assert_p_can_dlc`, `cover_p_can_dlc`, `assert_p_can_crc`, `cover_p_can_crc`, `assert_p_can_ack`, `cover_p_can_ack` … |
| Covergroups / coverpoints | 4 / 15 | |

## 4. 充分度判定與缺口

判定：**✅ Sufficient**（19 個 check，mutation score 100%）。

無已知缺口。

