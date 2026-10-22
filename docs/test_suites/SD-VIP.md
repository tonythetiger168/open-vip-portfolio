# SD 測試套件（SD-VIP）

> 由 `tools/gen_test_suite_docs.py` 依 VIP 內容、`func_report.csv` 與 `mutation_report.csv` 自動產生，請勿手動修改。

## 1. 概要

| 項目 | 內容 |
|---|---|
| 類別 | Memory |
| 類型 | UVM VIP |
| 功能測試 | 1 個檔案，33 個 check，全部通過 |
| Mutation | 9/12 個 mutant 被偵測（75%） |
| 判定 | **🟡 Partial**（mutation score 75%） |

## 2. 可執行的功能測試

執行：`python3 tools/run_func_tests.py SD-VIP`（Icarus Verilog 或 Verilator 5.052）。

### `tb/func_sd_tb.sv`

結果：**PASS**（verilator，33 checks）

模型合約與範圍（摘自測試檔頭）：

```text
func_sd_tb.sv -- self-checking functional test for the SD card model
(sd_card_dut in tb_top.sv, flattened by smoke/flatten.py).
Run: python3 tools/run_func_tests.py SD-VIP

Model contract (from tb_top.sv):
   * commands: 48 bits on cmd, MSB first, one per clock with cmd_valid
     {0, 1, index, argument, CRC7, 1}; other lengths are ignored.
   * responses on resp/resp_valid: R1 {0, 0, index, status, CRC7, 1}
     (ADDRESS_OUT_OF_RANGE 31, COM_CRC_ERROR 23, ILLEGAL_COMMAND 22,
     CURRENT_STATE 12:9), R2 (CID/CSD), R3 (OCR C0FF8000), R6 (RCA 0x0001),
     R7 (CMD8 echoes argument[11:0]).
   * identification: CMD0 -> idle, CMD8, CMD55 + ACMD41 -> ready, CMD2 ->
     ident, CMD3 -> stby, CMD7 -> tran; CMD9 returns the CSD.
   * 4-bit data, high nibble first: CMD17/18 read 512 bytes of block arg
     (unwritten byte = address[7:0] ^ 0xA5), CMD6 returns 64 status bytes
     (byte i = i). CMD24/25 take 512 bytes and one XOR checksum byte (bad
     checksum -> err, data_crc_ok low), then busy 32 clocks. CMD38 erases
     blocks 0-15 (busy 64), CMD12 busy 32. Block address >= 2048 is out of
     range; unknown indices and ACMD41 without CMD55 are illegal.
Known defect (XFAIL): the command CRC7 is computed over {00, index,
argument} instead of {0, 1, index, argument}; after checking that the test
sends the CRC the model expects.
Known deviations (XFAIL): R2 loses its transmission bit (137-bit frame in
a 136-bit register); R6 puts CURRENT_STATE in bits 15:12 of its 16-bit
status field instead of 12:9.
```

| # | Check | 類型 |
|---|---|---|
| 1 | ready, idle state after reset | check |
| 2 | CMD13 answered with R1 | check |
| 3 | command with the specified CRC7 is accepted | XFAIL（模型缺陷） |
| 4 | CMD0: no response, idle | check |
| 5 | CMD8: R7 echoes voltage and check pattern 0x1AA | check |
| 6 | ACMD41 without CMD55 is rejected (ILLEGAL_COMMAND) | check |
| 7 | CMD55 sets APP_CMD | check |
| 8 | ACMD41: R3 with OCR | check |
| 9 | ACMD41 moves to ready, APP_CMD cleared | check |
| 10 | CMD2: R2 with the CID | check |
| 11 | R2 starts with 0, 0, 111111 | XFAIL（模型缺陷） |
| 12 | CMD2 moves to ident | check |
| 13 | CMD3: R6 publishes RCA 0x0001 | check |
| 14 | R6 reports CURRENT_STATE (ident) in bits 12:9 | XFAIL（模型缺陷） |
| 15 | CMD3 moves to stby | check |
| 16 | CMD9: R2 with the CSD | check |
| 17 | CMD7: R1 from stby, card selected (tran) | check |
| 18 | CMD6: 64-byte switch status on DAT, high nibble first | check |
| 19 | CMD17 reads block 7 (initial pattern) | check |
| 20 | CMD24: good checksum, busy ~32 clocks (%0d) | check |
| 21 | back to tran after programming | check |
| 22 | written block read back through 4-bit DAT | check |
| 23 | bad data checksum flags err | check |
| 24 | CMD38: busy ~64 clocks (%0d) | check |
| 25 | erased block reads 0xFF | check |
| 26 | erase stops at block 15 | check |
| 27 | CMD12: R1b, busy ~32 clocks | check |
| 28 | read beyond capacity: ADDRESS_OUT_OF_RANGE | check |
| 29 | erase start beyond capacity: ADDRESS_OUT_OF_RANGE | check |
| 30 | CMD1 is illegal for SD | check |
| 31 | bad CRC: COM_CRC_ERROR | check |
| 32 | 47-bit burst ignored | check |
| 33 | reset aborts the read | check |

## 3. UVM 測試平台內容

UVM 測試需商用模擬器（VCS / Xcelium / Questa）執行；開源流程只做 elaboration（L1a）。

| 項目 | 數量 | 名稱 |
|---|---|---|
| UVM tests | 12 | `memory_base_test`, `memory_coverage_regression_test`, `memory_random_test`, `sd_regression_test`, `sd_init_test`, `sd_read_write_test`, `sd_erase_test`, `sd_error_test`, `sd_reset_test`, `sd_b2b_test`, `sd_corner_test`, `sd_stress_test` |
| Sequences | 52 | `ddr_seq_item`, `ddr_base_seq`, `ddr_rw_seq`, `ddr_cov_cmd_seq`, `ddr_cov_bank_seq`, `ddr_cov_bl_seq`, `lpddr_seq_item`, `lpddr_base_seq`, `lpddr_rw_seq`, `lpddr_cov_cmd_seq`, `lpddr_cov_bank_seq`, `hbm_seq_item`, `hbm_base_seq`, `hbm_rw_seq`, `hbm_cov_cmd_seq`, `hbm_cov_ch_seq`, `ufs_seq_item`, `ufs_base_seq`, `ufs_rw_seq`, `ufs_cov_upiu_seq` |
| SVA（assert / cover property） | 32 / 34 | `cover_p_stub_reset`, `assert_p_sd_cmd_valid`, `cover_p_sd_cmd_valid`, `assert_p_sd_addr_valid`, `cover_p_sd_addr_valid`, `assert_p_sd_data_valid`, `cover_p_sd_data_valid`, `assert_p_sd_no_x`, `cover_p_sd_no_x`, `assert_p_sd_card_busy`, `cover_p_sd_card_busy`, `assert_p_sd_resp_latency` … |
| Covergroups / coverpoints | 16 / 39 | |

## 4. 充分度判定與缺口

判定：**🟡 Partial**（mutation score 75%）。

未被偵測的 mutant（測試缺口或等價 mutant）：

- `dut_sd_card_dut.sv:60 0 -> 1 [for (int i = 0; i < CAP_BYTES; i++) mem[i] = i[7:0] ^ 8'hA5;]`
- `dut_sd_card_dut.sv:180 0 -> 1 [if (!bad_addr && !bad_crc) begin data_cnt <= 0; nib <= 0; cs]`
- `dut_sd_card_dut.sv:201 0 -> 1 [if (idx != 6'd0) bit_cnt <= 0;]`

DUT 模型缺陷（XFAIL check，修好模型後會變成 XPASS 提醒移除標記）：

- command with the specified CRC7 is accepted
- R2 starts with 0, 0, 111111
- R6 reports CURRENT_STATE (ident) in bits 12:9

