# eMMC 測試套件（eMMC-VIP）

> 由 `tools/gen_test_suite_docs.py` 依 VIP 內容、`func_report.csv` 與 `mutation_report.csv` 自動產生，請勿手動修改。

## 1. 概要

| 項目 | 內容 |
|---|---|
| 類別 | Memory |
| 類型 | UVM VIP |
| 功能測試 | 1 個檔案，41 個 check，全部通過 |
| Mutation | 8/12 個 mutant 被偵測（67%） |
| 判定 | **🟡 Partial**（mutation score 67%） |

## 2. 可執行的功能測試

執行：`python3 tools/run_func_tests.py eMMC-VIP`（Icarus Verilog 或 Verilator 5.052）。

### `tb/func_emmc_tb.sv`

結果：**PASS**（verilator，41 checks）

模型合約與範圍（摘自測試檔頭）：

```text
func_emmc_tb.sv -- self-checking functional test for the eMMC device model
(emmc_device_dut in tb_top.sv, flattened by smoke/flatten.py).
Run: python3 tools/run_func_tests.py eMMC-VIP

Model contract (from tb_top.sv):
   * a command is 48 bits on cmd, MSB first, one per clock with cmd_valid:
     start 0, transmission 1, index[5:0], argument[31:0], CRC7 (x^7+x^3+1),
     end 1. A burst of any other length is ignored.
   * responses are shifted out on resp with resp_valid: 48-bit R1/R1b/R3
     {0, 0, index, status/OCR, CRC7, 1} (R3 index 0x3F) and 136-bit R2 (CID).
     R1 status: ADDRESS_OUT_OF_RANGE bit 31, COM_CRC_ERROR bit 23,
     ILLEGAL_COMMAND bit 22, CURRENT_STATE bits 12:9.
   * CMD0 reset (no response), CMD1/CMD41 (after CMD55) R3 with OCR
     C0FF8000, CMD2 R2 CID, CMD3 sets RCA -> stby, CMD7 -> tran, CMD13 R1.
   * CMD17/18 read one 512-byte block at block address arg (rd_data/
     rd_valid), CMD8 returns EXT_CSD (byte i = i); unwritten memory holds
     (address[7:0] ^ 0xA5). Block address >= 2048 is out of range.
   * CMD24/25 write: 512 data bytes then one XOR checksum byte; a bad
     checksum sets err and clears data_crc_ok. Then busy for 32 clocks.
   * CMD6 busy 32 clocks; CMD38 erases blocks 0-15 to 0xFF, busy 64 clocks.
   * unknown indices, CMD41 without CMD55, bad CRC/start/transmission bits
     set the matching status bits and err.
Known defect (XFAIL): the model computes the command CRC7 over
{00, index, argument} instead of {start 0, transmission 1, index,
argument}, so every command with a correct CRC is flagged COM_CRC_ERROR.
After checking that, the test sends the CRC the model expects. (Response
CRCs cover {0, 0, index, status} and are correct.)
Known deviation (XFAIL): R1 of CMD3/6/7/8/17/18/24/25/38 builds the
status as {16'h0, state, 12'h0}, putting CURRENT_STATE in bits 15:12
instead of 12:9 (CMD13 is correct).
Known deviation (XFAIL): R2 must start with start bit 0, transmission bit
0 and 111111; the model's 137-bit R2 frame is truncated to 136 bits and
loses the transmission bit.
```

| # | Check | 類型 |
|---|---|---|
| 1 | CRC7 reference matches the known command CRCs | check |
| 2 | ready, idle state after reset | check |
| 3 | CMD13 answered with R1 | check |
| 4 | command with the specified CRC7 is accepted | XFAIL（模型缺陷） |
| 5 | command with the model's CRC7 accepted | check |
| 6 | CMD0: no response, idle | check |
| 7 | CMD1: R3 with OCR C0FF8000 (busy bit set) | check |
| 8 | CMD1 moves to ready | check |
| 9 | CMD2: 136-bit R2 | check |
| 10 | R2 carries the CID | check |
| 11 | R2 starts with 0, 0, 111111 | XFAIL（模型缺陷） |
| 12 | CMD2 moves to ident | check |
| 13 | CMD3: R1, RCA 2 assigned, stby | check |
| 14 | CMD13: R1 reports stby, no errors | check |
| 15 | CMD7 selects the card: tran | check |
| 16 | CMD7 R1 reports CURRENT_STATE (stby) in bits 12:9 | XFAIL（模型缺陷） |
| 17 | CMD8 returns the 512-byte EXT_CSD | check |
| 18 | CMD17 reads block 3 (initial pattern) | check |
| 19 | back to tran after the read | check |
| 20 | CMD24: R1 before the data phase | check |
| 21 | programming: busy, prg state | check |
| 22 | good checksum, busy ~32 clocks (%0d) | check |
| 23 | back to tran after programming | check |
| 24 | written block read back | check |
| 25 | neighbouring block untouched | check |
| 26 | bad data checksum flags err | check |
| 27 | CMD38: R1b, busy ~64 clocks (%0d) | check |
| 28 | erased block reads 0xFF | check |
| 29 | erase stops at block 15 | check |
| 30 | CMD6: R1b with ~32 clocks busy | check |
| 31 | read beyond capacity: ADDRESS_OUT_OF_RANGE, no data | check |
| 32 | write beyond capacity rejected | check |
| 33 | CRC error: COM_CRC_ERROR | check |
| 34 | transmission bit 0 treated as a CRC error | check |
| 35 | unknown CMD60: ILLEGAL_COMMAND | check |
| 36 | ACMD41 without CMD55: ILLEGAL_COMMAND | check |
| 37 | CMD55 accepted and sets APP_CMD | check |
| 38 | ACMD41 after CMD55 accepted, APP_CMD cleared | check |
| 39 | a 40-bit burst is ignored | check |
| 40 | CMD0 returns the card to idle | check |
| 41 | reset aborts the read | check |

## 3. UVM 測試平台內容

UVM 測試需商用模擬器（VCS / Xcelium / Questa）執行；開源流程只做 elaboration（L1a）。

| 項目 | 數量 | 名稱 |
|---|---|---|
| UVM tests | 12 | `memory_base_test`, `memory_coverage_regression_test`, `memory_random_test`, `emmc_regression_test`, `emmc_init_test`, `emmc_read_write_test`, `emmc_erase_test`, `emmc_error_test`, `emmc_reset_test`, `emmc_b2b_test`, `emmc_corner_test`, `emmc_stress_test` |
| Sequences | 51 | `emmc_seq_item`, `emmc_base_seq`, `emmc_rw_seq`, `emmc_init_seq`, `emmc_read_seq`, `emmc_write_seq`, `emmc_config_seq`, `emmc_erase_seq`, `emmc_error_seq`, `emmc_reset_seq`, `emmc_b2b_seq`, `emmc_stress_seq`, `emmc_corner_seq`, `emmc_cov_cmd_seq`, `emmc_cov_bw_seq`, `emmc_fsm_seq`, `emmc_regression_mix_seq`, `ddr_seq_item`, `ddr_base_seq`, `ddr_rw_seq` |
| SVA（assert / cover property） | 32 / 33 | `assert_p_emmc_cmd_valid`, `cover_p_emmc_cmd_valid`, `assert_p_emmc_addr_valid`, `cover_p_emmc_addr_valid`, `assert_p_emmc_data_valid`, `cover_p_emmc_data_valid`, `assert_p_emmc_no_x`, `cover_p_emmc_no_x`, `assert_p_emmc_card_busy`, `cover_p_emmc_card_busy`, `assert_p_emmc_resp_latency`, `cover_p_emmc_resp_latency` … |
| Covergroups / coverpoints | 14 / 33 | |

## 4. 充分度判定與缺口

判定：**🟡 Partial**（mutation score 67%）。

未被偵測的 mutant（測試缺口或等價 mutant）：

- `dut_emmc_device_dut.sv:94 0 -> 1 [st <= E_IDLE; bit_cnt <= 0; rsp_cnt <= 0; data_cnt <= 0; pro]`
- `dut_emmc_device_dut.sv:105 1'b1 inverted [vif_data_crc_ok <= 1'b1;]`
- `dut_emmc_device_dut.sv:184 0 -> 1 [data_cnt <= 0;]`
- `dut_emmc_device_dut.sv:230 == flipped [if (idx == 6'd13) cstate <= cstate;]`

DUT 模型缺陷（XFAIL check，修好模型後會變成 XPASS 提醒移除標記）：

- command with the specified CRC7 is accepted
- R2 starts with 0, 0, 111111
- CMD7 R1 reports CURRENT_STATE (stby) in bits 12:9

