# MIPI SLIMbus 測試套件（SLIMbus-VIP）

> 由 `tools/gen_test_suite_docs.py` 依 VIP 內容、`func_report.csv` 與 `mutation_report.csv` 自動產生，請勿手動修改。

## 1. 概要

| 項目 | 內容 |
|---|---|
| 類別 | MIPI |
| 類型 | UVM VIP |
| 功能測試 | 1 個檔案，14 個 check，全部通過 |
| Mutation | 23/23 個 mutant 被偵測（100%） |
| 判定 | **✅ Sufficient**（14 個 check，mutation score 100%） |

## 2. 可執行的功能測試

執行：`python3 tools/run_func_tests.py SLIMbus-VIP`（Icarus Verilog 或 Verilator 5.052）。

### `tb/func_slimbus_tb.sv`

結果：**PASS**（iverilog，14 checks）

模型合約與範圍（摘自測試檔頭）：

```text
func_slimbus_tb.sv -- self-checking functional test for the SLIMbus codec
slave model (slimbus_codec_slave, flattened by smoke/flatten.py).
Run: python3 tools/run_func_tests.py SLIMbus-VIP

Model contract (from tb/top_tb.sv and slimbus_defs_pkg):
   the manager drives DATA on the rising edge, the slave samples on the
   falling edge. A frame is SYNC (0x5A) followed by a 32-bit header
   {opcode, logical address, channel, data}. The slave answers with one
   byte on the following 8 rising edges (data_oe high): ENUM -> presence
   0xC3, ASSIGN_LA / CHAN_SETUP / PAUSE / RESUME -> ACK 0xA5, STREAM ->
   echoes the sample byte, unknown opcodes -> 0x00. ASSIGN_LA sets the
   slave's logical address; SETUP/PAUSE/RESUME act only when addressed to it.
```

| # | Check | 類型 |
|---|---|---|
| 1 | ENUM answered with the presence byte 0xC3 | check |
| 2 | response occupies exactly 8 cells with data_oe high | check |
| 3 | ASSIGN_LA ACKed and sets the logical address | check |
| 4 | CHAN_SETUP to own LA ACKed and activates the channel | check |
| 5 | CHAN_SETUP to another LA does not activate the channel | check |
| 6 | STREAM echoes the sample byte | check |
| 7 | STREAM echoes an all-zero sample | check |
| 8 | PAUSE to own LA ACKed and pauses | check |
| 9 | RESUME addressed to another LA is ignored | check |
| 10 | RESUME to own LA ACKed and resumes | check |
| 11 | unknown opcode answered with 0x00 | check |
| 12 | no response without the SYNC byte | check |
| 13 | reset clears the logical address | check |
| 14 | reset clears the pause state and the frame receiver | check |

## 3. UVM 測試平台內容

UVM 測試需商用模擬器（VCS / Xcelium / Questa）執行；開源流程只做 elaboration（L1a）。

| 項目 | 數量 | 名稱 |
|---|---|---|
| UVM tests | 3 | `slimbus_base_test`, `slimbus_random_test`, `slimbus_regression_test` |
| Sequences | 11 | `slimbus_base_sequence`, `slimbus_enumeration_seq`, `slimbus_channel_setup_seq`, `slimbus_audio_stream_seq`, `slimbus_pause_resume_seq`, `slimbus_back_to_back_seq`, `slimbus_error_inject_seq`, `slimbus_reset_seq`, `slimbus_random_sequence`, `slimbus_regression_sequence`, `slimbus_transaction` |
| SVA（assert / cover property） | 20 / 2 | `a_slimbus_l1_clk`, `a_slimbus_l1_rst`, `a_slimbus_l1_state`, `a_slimbus_l1_valid`, `a_slimbus_trans_idle`, `a_slimbus_trans_enumeration`, `a_slimbus_trans_channel_setup`, `a_slimbus_trans_streaming`, `a_slimbus_trans_paused`, `a_slimbus_trans_aligned`, `a_slimbus_l3_reset_idle`, `a_slimbus_l3_no_stuck` … |
| Covergroups / coverpoints | 3 / 9 | |

## 4. 充分度判定與缺口

判定：**✅ Sufficient**（14 個 check，mutation score 100%）。

無已知缺口。

