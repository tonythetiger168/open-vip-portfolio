# MIPI SoundWire 測試套件（SoundWire-VIP）

> 由 `tools/gen_test_suite_docs.py` 依 VIP 內容、`func_report.csv` 與 `mutation_report.csv` 自動產生，請勿手動修改。

## 1. 概要

| 項目 | 內容 |
|---|---|
| 類別 | MIPI |
| 類型 | UVM VIP |
| 功能測試 | 1 個檔案，18 個 check，全部通過 |
| Mutation | 6/7 個 mutant 被偵測（86%） |
| 判定 | **✅ Sufficient**（18 個 check，mutation score 86%） |

## 2. 可執行的功能測試

執行：`python3 tools/run_func_tests.py SoundWire-VIP`（Icarus Verilog 或 Verilator 5.052）。

### `tb/func_soundwire_tb.sv`

結果：**PASS**（verilator，18 checks）

模型合約與範圍（摘自測試檔頭）：

```text
func_soundwire_tb.sv -- self-checking functional test for the MIPI
SoundWire audio peripheral model (soundwire_audio_peripheral, flattened by
smoke/flatten.py). Run: python3 tools/run_func_tests.py SoundWire-VIP

Model contract (from tb/top_tb.sv and soundwire_defs_pkg):
   DATA is sampled on both clock edges (double data rate). A frame is SYNC
   (0xC7) + 32 header bits {device[3:0], opcode[3:0], address[15:0],
   data[7:0]}. The addressed peripheral (DEV_NUM = 1) answers with a status
   byte over the next 8 edges: WRITE / BLOCK -> 0xAB (0xAA with a bus
   request armed), READ -> register data, PING (any device) -> 0x5B / 0x5A
   with a bus request. Writing 1 to register 0x00F0 arms a bus request;
   BRA_GRANT clears it. Frames for other devices get no response.
```

| # | Check | 類型 |
|---|---|---|
| 1 | register WRITE answered with the write status 0xAB | check |
| 2 | register WRITE stores the data | check |
| 3 | register READ returns the written byte | check |
| 4 | READ of an unwritten register returns 0 | check |
| 5 | WRITE to another device: no response, no update | check |
| 6 | READ to another device gets no response | check |
| 7 | PING (broadcast) answered with status 0x5B | check |
| 8 | writing 1 to 0x00F0 arms a bus request | check |
| 9 | PING reports the pending bus request (0x5A) | check |
| 10 | WRITE status reports the pending bus request (0xAA) | check |
| 11 | BRA grant clears the request (no response) | check |
| 12 | PING status back to no-request after the grant | check |
| 13 | BLOCK_FIRST + BLOCK frames store the data block | check |
| 14 | unknown opcode gets no response | check |
| 15 | frame without SYNC is ignored | check |
| 16 | reset releases the line and clears the bus request | check |
| 17 | frame after a reset in the middle of a header is decoded | check |
| 18 | PING after reset: no bus request pending | check |

## 3. UVM 測試平台內容

UVM 測試需商用模擬器（VCS / Xcelium / Questa）執行；開源流程只做 elaboration（L1a）。

| 項目 | 數量 | 名稱 |
|---|---|---|
| UVM tests | 3 | `soundwire_base_test`, `soundwire_random_test`, `soundwire_regression_test` |
| Sequences | 11 | `soundwire_base_sequence`, `soundwire_write_seq`, `soundwire_read_seq`, `soundwire_block_transfer_seq`, `soundwire_ping_seq`, `soundwire_bra_seq`, `soundwire_error_inject_seq`, `soundwire_reset_seq`, `soundwire_random_sequence`, `soundwire_regression_sequence`, `soundwire_transaction` |
| SVA（assert / cover property） | 20 / 2 | `a_soundwire_l1_clk`, `a_soundwire_l1_rst`, `a_soundwire_l1_state`, `a_soundwire_l1_valid`, `a_soundwire_trans_idle`, `a_soundwire_trans_command`, `a_soundwire_trans_ping`, `a_soundwire_trans_data_block`, `a_soundwire_trans_bra`, `a_soundwire_trans_aligned`, `a_soundwire_l3_reset_idle`, `a_soundwire_l3_no_stuck` … |
| Covergroups / coverpoints | 3 / 10 | |

## 4. 充分度判定與缺口

判定：**✅ Sufficient**（18 個 check，mutation score 86%）。

未被偵測的 mutant（測試缺口或等價 mutant）：

- `dut_soundwire_audio_peripheral.sv:31 0 -> 1 [w <= 0; h32 <= 0; bcnt <= 0; rcnt <= 0; skip <= 0; respond <]`

