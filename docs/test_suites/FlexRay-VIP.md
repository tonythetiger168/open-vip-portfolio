# FlexRay 測試套件（FlexRay-VIP）

> 由 `tools/gen_test_suite_docs.py` 依 VIP 內容、`func_report.csv` 與 `mutation_report.csv` 自動產生，請勿手動修改。

## 1. 概要

| 項目 | 內容 |
|---|---|
| 類別 | Automotive |
| 類型 | UVM VIP |
| 功能測試 | 1 個檔案，38 個 check，全部通過 |
| Mutation | 20/20 個 mutant 被偵測（100%） |
| 判定 | **✅ Sufficient**（38 個 check，mutation score 100%） |

## 2. 可執行的功能測試

執行：`python3 tools/run_func_tests.py FlexRay-VIP`（Icarus Verilog 或 Verilator 5.052）。

### `tb/func_flexray_tb.sv`

結果：**PASS**（iverilog，38 checks）

模型合約與範圍（摘自測試檔頭）：

```text
func_flexray_tb.sv -- self-checking functional test for the FlexRay node
model (flexray_node_model, flattened by smoke/flatten.py).
Run: python3 tools/run_func_tests.py FlexRay-VIP

Model contract (from tb/flexray_node_model.sv), 8 clocks per bit on rxd_a:
   a dominant TSS (2..5 bits; a 6th dominant bit is a syntax error that
   drives txd_a low for 48 clocks) and the FSS (one recessive bit) start
   capture of a FlexRay 2.1 frame, MSB first, without byte start sequences:
     [0] reserved, [1] payload preamble, [2] null frame, [3] sync,
     [4] startup, [5:15] frame ID, [16:22] payload length (2-byte words,
     the model captures up to 4), [23:33] header CRC, [34:39] cycle count,
     payload, 24-bit frame CRC, FES (0, 1).
   Header CRC: CRC-11 (poly 0x385, init 0x01A) over sync, startup, ID and
   length; frame CRC: CRC-24 (poly 0x5D6DCB, init 0xFEDCBA, channel A)
   over header and payload. A mismatch sets content_error. The node then
   echoes 000 1 + the frame on txd_a/txd_b with txen_a high. macrotick
   counts clocks; slot advances every 64 and cycle every 1024 clocks.
```

| # | Check | 類型 |
|---|---|---|
| 1 | reset: network idle, transmitter off, bus recessive | check |
| 2 | slot 1 starts at macrotick 64 | check |
| 3 | macrotick counts one per clock | check |
| 4 | slot advances every 64 macroticks | check |
| 5 | cycle 1 starts at macrotick 1024 (slot 16) | check |
| 6 | cycle advances every 1024 macroticks | check |
| 7 | frame ID, payload length and cycle count decoded | check |
| 8 | valid header and frame CRC: no content error, header_crc output = CRC[4:0] | check |
| 9 | echo length = 4 + captured frame bits | check |
| 10 | frame echoed on txd_a as 000 1 + captured bits | check |
| 11 | txd_b mirrors txd_a during the echo | check |
| 12 | static_segment high during the echo, back to idle after | check |
| 13 | 2-word (4-byte) payload frame decoded | check |
| 14 | payload frame captured in full (header + payload + CRC + FES) | check |
| 15 | bus released (recessive) after the echo | check |
| 16 | frame ID 0x7A5 (MSB set): decoded, header CRC good | check |
| 17 | bus released after the second echo | check |
| 18 | payload length output 3 words | check |
| 19 | 3-word payload: whole frame captured | check |
| 20 | 5-bit TSS accepted | check |
| 21 | 2-bit TSS accepted | check |
| 22 | 1-bit dominant glitch ignored | check |
| 23 | corrupted header CRC sets content_error | check |
| 24 | content_error clears on the next good frame | check |
| 25 | corrupted frame CRC flagged | check |
| 26 | same frame with its CRC: accepted | check |
| 27 | corrupted payload bit flagged by the frame CRC | check |
| 28 | sync + startup frame: indicators decoded, header CRC good | check |
| 29 | indicator bit change detected by the header CRC | check |
| 30 | 6 dominant TSS bits raise syntax_error | check |
| 31 | syntax error drives txd_a dominant for 48 clocks | check |
| 32 | syntax_error clears and the bus is released | check |
| 33 | node receives again after a syntax error | check |
| 34 | normal frame: sync / startup indicators low; coldstart / wakeup stay low (no startup support) | check |
| 35 | sync + startup indicators set before the reset | check |
| 36 | reset clears the sync / startup indicators | check |
| 37 | reset clears timebase and status | check |
| 38 | reset: not in a segment, transmitter off and recessive | check |

## 3. UVM 測試平台內容

UVM 測試需商用模擬器（VCS / Xcelium / Questa）執行；開源流程只做 elaboration（L1a）。

| 項目 | 數量 | 名稱 |
|---|---|---|
| UVM tests | 4 | `base_test`, `random_test`, `error_inject_test`, `regression_test` |
| Sequences | 13 | `base_tx`, `flexray_base_sequence`, `flexray_random_sequence`, `flexray_static_sequence`, `flexray_sync_sequence`, `flexray_wakeup_sequence`, `flexray_error_inject_sequence`, `flexray_back_to_back_sequence`, `flexray_corner_sequence`, `flexray_reset_sequence`, `flexray_stress_sequence`, `flexray_regression_sequence`, `flexray_transaction` |
| SVA（assert / cover property） | 32 / 29 | `assert_p_fr_channel`, `cover_p_fr_channel`, `assert_p_fr_frame_id`, `cover_p_fr_frame_id`, `assert_p_fr_payload_len`, `cover_p_fr_payload_len`, `assert_p_fr_cycle`, `cover_p_fr_cycle`, `assert_p_fr_header_crc`, `cover_p_fr_header_crc`, `assert_p_fr_sync`, `cover_p_fr_sync` … |
| Covergroups / coverpoints | 3 / 14 | |

## 4. 充分度判定與缺口

判定：**✅ Sufficient**（38 個 check，mutation score 100%）。

無已知缺口。

