# UFS 測試套件（UFS-VIP）

> 由 `tools/gen_test_suite_docs.py` 依 VIP 內容、`func_report.csv` 與 `mutation_report.csv` 自動產生，請勿手動修改。

## 1. 概要

| 項目 | 內容 |
|---|---|
| 類別 | Memory |
| 類型 | UVM VIP |
| 功能測試 | 1 個檔案，28 個 check，全部通過 |
| Mutation | 11/12 個 mutant 被偵測（92%） |
| 判定 | **✅ Sufficient**（28 個 check，mutation score 92%） |

## 2. 可執行的功能測試

執行：`python3 tools/run_func_tests.py UFS-VIP`（Icarus Verilog 或 Verilator 5.052）。

### `tb/func_ufs_tb.sv`

結果：**PASS**（verilator，28 checks）

模型合約與範圍（摘自測試檔頭）：

```text
func_ufs_tb.sv -- self-checking functional test for the UFS device model
(ufs_device_dut in tb_top.sv, flattened by smoke/flatten.py).
Run: python3 tools/run_func_tests.py UFS-VIP

Model contract (from tb_top.sv), byte stream on data_out/data_in:
   * request header, 10 bytes: UPIU transaction type, LUN, task tag, SCSI
     opcode, LBA (4 bytes, MSB first), data length in bytes (2, MSB first).
   * the device answers with a 3-byte response: type (NOP OUT 00 -> NOP IN
     20, COMMAND 01 -> RESPONSE 21, TASK MGMT 04 -> 24, QUERY 16 -> 36,
     other -> REJECT 3F), the task tag, and SCSI status (00 GOOD, 02 CHECK
     CONDITION); resp_valid marks it, resp_status is 001 good / 010 error.
   * errors: LUN > 7, a COMMAND with an opcode other than TEST UNIT READY
     00, REQUEST SENSE 03, INQUIRY 12, READ(10) 28, WRITE(10) 2A, or
     LBA*512 + length beyond the 1 MiB capacity (err, CHECK CONDITION).
   * WRITE(10): the device sends READY TO TRANSFER (0x31, transfer_ready),
     takes 'length' data bytes into LBA*512 onward, then responds.
   * READ(10): 'length' bytes from LBA*512 onward, then the response.
     Unwritten memory holds (address[7:0] ^ 0x5A).
```

| # | Check | 類型 |
|---|---|---|
| 1 | idle and ready, power state active | check |
| 2 | busy while handling a request | check |
| 3 | NOP OUT answered by NOP IN with the tag | check |
| 4 | good response status | check |
| 5 | ready again after the response | check |
| 6 | QUERY REQUEST answered by QUERY RESPONSE | check |
| 7 | TASK MANAGEMENT REQUEST answered | check |
| 8 | unknown transaction type answered by REJECT UPIU | check |
| 9 | TEST UNIT READY: GOOD, no data | check |
| 10 | INQUIRY on LUN 3: GOOD | check |
| 11 | READ(10) returns the initial pattern (%0d bytes) | check |
| 12 | READ(10) completes with GOOD | check |
| 13 | WRITE(10): READY TO TRANSFER sent | check |
| 14 | no response before the data phase | check |
| 15 | WRITE(10) completes with GOOD after the data | check |
| 16 | written data read back | check |
| 17 | write did not spill past its length | check |
| 18 | read of the last 512 bytes is in range | check |
| 19 | read past capacity: CHECK CONDITION, no data | check |
| 20 | error response status | check |
| 21 | write past capacity rejected without READY TO TRANSFER | check |
| 22 | LUN 8 rejected | check |
| 23 | unsupported SCSI opcode rejected | check |
| 24 | opcode not checked for NOP OUT | check |
| 25 | error counter | check |
| 26 | task tag echoed for each request | check |
| 27 | reset aborts the read | check |
| 28 | device works after reset | check |

## 3. UVM 測試平台內容

UVM 測試需商用模擬器（VCS / Xcelium / Questa）執行；開源流程只做 elaboration（L1a）。

| 項目 | 數量 | 名稱 |
|---|---|---|
| UVM tests | 10 | `memory_base_test`, `memory_coverage_regression_test`, `memory_random_test`, `ufs_regression_test`, `ufs_read_write_test`, `ufs_error_test`, `ufs_reset_test`, `ufs_b2b_test`, `ufs_corner_test`, `ufs_stress_test` |
| Sequences | 48 | `ddr_seq_item`, `ddr_base_seq`, `ddr_rw_seq`, `ddr_cov_cmd_seq`, `ddr_cov_bank_seq`, `ddr_cov_bl_seq`, `lpddr_seq_item`, `lpddr_base_seq`, `lpddr_rw_seq`, `lpddr_cov_cmd_seq`, `lpddr_cov_bank_seq`, `hbm_seq_item`, `hbm_base_seq`, `hbm_rw_seq`, `hbm_cov_cmd_seq`, `hbm_cov_ch_seq`, `unipro_seq_item`, `unipro_base_seq`, `unipro_rw_seq`, `unipro_cov_msg_seq` |
| SVA（assert / cover property） | 32 / 32 | `assert_p_ufs_cmd_valid`, `cover_p_ufs_cmd_valid`, `assert_p_ufs_addr_valid`, `cover_p_ufs_addr_valid`, `assert_p_ufs_data_valid`, `cover_p_ufs_data_valid`, `assert_p_ufs_no_x`, `cover_p_ufs_no_x`, `assert_p_ufs_transfer_ready`, `cover_p_ufs_transfer_ready`, `assert_p_ufs_resp_latency`, `cover_p_ufs_resp_latency` … |
| Covergroups / coverpoints | 12 / 28 | |

## 4. 充分度判定與缺口

判定：**✅ Sufficient**（28 個 check，mutation score 92%）。

未被偵測的 mutant（測試缺口或等價 mutant）：

- `dut_ufs_device_dut.sv:61 0 -> 1 [vif_transfer_ready <= 0; vif_ready <= 0; vif_busy <= 0; vif_]`

