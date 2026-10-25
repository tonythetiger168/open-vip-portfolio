# LIN 測試套件（LIN-VIP）

> 由 `tools/gen_test_suite_docs.py` 依 VIP 內容、`func_report.csv` 與 `mutation_report.csv` 自動產生，請勿手動修改。

## 1. 概要

| 項目 | 內容 |
|---|---|
| 類別 | Automotive |
| 類型 | UVM VIP |
| 功能測試 | 1 個檔案，25 個 check，全部通過 |
| Mutation | 8/8 個 mutant 被偵測（100%） |
| 判定 | **✅ Sufficient**（25 個 check，mutation score 100%） |

## 2. 可執行的功能測試

執行：`python3 tools/run_func_tests.py LIN-VIP`（Icarus Verilog 或 Verilator 5.052）。

### `tb/func_lin_tb.sv`

結果：**PASS**（verilator，25 checks）

模型合約與範圍（摘自測試檔頭）：

```text
func_lin_tb.sv -- self-checking functional test for the LIN slave model
(tb/lin_slave_model.sv, flattened by smoke/flatten.py).
Run: python3 tools/run_func_tests.py LIN-VIP

Model contract (from tb/lin_slave_model.sv), 8 clocks per bit:
   * a header is a break (>= 10 dominant bits, then a recessive delimiter),
     the sync byte 0x55 and the protected identifier; bytes are UART frames
     (start 0, 8 data bits LSB first, stop 1). Data length follows the ID:
     ID[5:4] 00/01 -> 2 bytes, 10 -> 4, 11 -> 8, IDs 60-63 -> 8; a checksum
     byte follows the data.
   * PID parity: P0 = ID0^ID1^ID2^ID4, P1 = ~(ID1^ID3^ID4^ID5) (LIN 2.x).
   * after the frame the slave reports pid/parity/data_len/checksum and
     re-transmits the frame on lin_tx (13-bit break, delimiter, 0x55, PID,
     data, checksum); on a parity error it sends 0xFF after the sync.
   * errors: sync other than 0x55 -> bit_error; a 0 stop bit ->
     framing_error; no start bit within 24 bit times -> timeout_error.
   * a dominant pulse shorter than a break is a wake-up: the slave answers
     with a dominant pulse of the measured length (bit-sampled, so up to
     one bit longer) with wakeup_signal.
   * 24 recessive bit times on an idle bus -> sleep_mode.
   * the checksum byte is checked (checksum_error, cleared by the next
     break): enhanced over PID and data, classic (data only) for the
     diagnostic IDs 60-63; it is reported on checksum and re-transmitted.
```

| # | Check | 類型 |
|---|---|---|
| 1 | PID reference matches the LIN specification table | check |
| 2 | break field (13 dominant bits + delimiter) detected | check |
| 3 | sync byte 0x55 received without bit error | check |
| 4 | PID and parity decoded | check |
| 5 | 2-byte length from ID[5:4]=00, enhanced checksum accepted | check |
| 6 | checksum output carries the received checksum byte | check |
| 7 | re-transmitted break is 13 bits (%0d clocks) | check |
| 8 | frame re-transmitted: sync, PID, data (%0d bytes) | check |
| 9 | re-transmitted frame ends with the checksum | check |
| 10 | 4-byte frame (ID[5:4]=10) | check |
| 11 | 8-byte frame (ID 0x3C) | check |
| 12 | diagnostic ID 0x3C: classic checksum accepted and re-transmitted | check |
| 13 | PID parity error flagged | check |
| 14 | parity error answered with 0xFF after the sync | check |
| 15 | wrong checksum byte flagged | check |
| 16 | stop bit 0 flagged as framing error | check |
| 17 | sync byte other than 0x55 flagged as bit error | check |
| 18 | no timeout within 24 bit times after the break | check |
| 19 | timeout exactly 24 bit times after the break delimiter (%0d clocks) | check |
| 20 | short dominant pulse answered as a wake-up | check |
| 21 | wake-up answer as long as the pulse, to the bit sampling (%0d clocks) | check |
| 22 | 8-bit wake-up pulse answered with 9 sampled bit times (%0d clocks) | check |
| 23 | awake for 24 idle bit times | check |
| 24 | sleep exactly 24 idle bit times after reset (%0d clocks) | check |
| 25 | bus activity leaves sleep | check |

## 3. UVM 測試平台內容

UVM 測試需商用模擬器（VCS / Xcelium / Questa）執行；開源流程只做 elaboration（L1a）。

| 項目 | 數量 | 名稱 |
|---|---|---|
| UVM tests | 5 | `base_test`, `random_test`, `sleep_wakeup_test`, `error_inject_test`, `regression_test` |
| Sequences | 12 | `base_tx`, `lin_base_sequence`, `lin_random_sequence`, `lin_diagnostic_sequence`, `lin_sleep_wakeup_sequence`, `lin_error_inject_sequence`, `lin_back_to_back_sequence`, `lin_corner_sequence`, `lin_reset_sequence`, `lin_stress_sequence`, `lin_regression_sequence`, `lin_transaction` |
| SVA（assert / cover property） | 27 / 24 | `assert_p_lin_break`, `cover_p_lin_break`, `assert_p_lin_sync`, `cover_p_lin_sync`, `assert_p_lin_pid`, `cover_p_lin_pid`, `assert_p_lin_parity`, `cover_p_lin_parity`, `assert_p_lin_data_len`, `cover_p_lin_data_len`, `assert_p_lin_checksum`, `cover_p_lin_checksum` … |
| Covergroups / coverpoints | 4 / 8 | |

## 4. 充分度判定與缺口

判定：**✅ Sufficient**（25 個 check，mutation score 100%）。

無已知缺口。

