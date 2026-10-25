# ONFI 測試套件（ONFI-VIP）

> 由 `tools/gen_test_suite_docs.py` 依 VIP 內容、`func_report.csv` 與 `mutation_report.csv` 自動產生，請勿手動修改。

## 1. 概要

| 項目 | 內容 |
|---|---|
| 類別 | Memory |
| 類型 | UVM VIP |
| 功能測試 | 1 個檔案，39 個 check，全部通過 |
| Mutation | 8/8 個 mutant 被偵測（100%） |
| 判定 | **✅ Sufficient**（39 個 check，mutation score 100%） |

## 2. 可執行的功能測試

執行：`python3 tools/run_func_tests.py ONFI-VIP`（Icarus Verilog 或 Verilator 5.052）。

### `tb/func_onfi_tb.sv`

結果：**PASS**（verilator，39 checks）

模型合約與範圍（摘自測試檔頭）：

```text
func_onfi_tb.sv -- self-checking functional test for the ONFI NAND model
(onfi_nand_model, flattened by smoke/flatten.py).
Run: python3 tools/run_func_tests.py ONFI-VIP

Model contract (from tb_top.sv and onfi_pkg.sv's driver), asynchronous
SDR bus sampled on clk: command/address/data latched on the WE# rising
edge (CLE / ALE / neither), data out on the RE# falling edge. Address
cycles as the VIP driver sends them: column, page, block (erase: page,
block); the model uses the last two bytes. 64 blocks x 64 pages x
256 bytes, erased = 0xFF. R/B# low for tR = 25, tPROG = 200,
tBERS = 2000, tRST = 10 clocks. Status: [7] WP# (1 = not protected),
[6] ready, [0] FAIL. READ ID returns "ONFI" + 01h; the parameter page
starts with "ONFI" and ends with its CRC-16. 80h fills the page register
with FFh; SET/GET FEATURES carry P1..P4; 00h after 70h during a page read
resumes the data output.

Not modelled (limitations, not tested): column addressing, the ONFI
2-column + 3-row address format, multi-plane/cache operations.
```

| # | Check | 類型 |
|---|---|---|
| 1 | reset: ready, IO bus released | check |
| 2 | READ ID (address 20h) returns the ONFI signature | check |
| 3 | READ ID 5th byte 01h, then wraps | check |
| 4 | IO not driven with CE# high | check |
| 5 | one byte per RE# pulse however long RE# is low; RE# pulses with CE# high are ignored | check |
| 6 | parameter page starts with the ONFI signature | check |
| 7 | parameter page integrity CRC (bytes 254-255) valid | check |
| 8 | parameter page geometry: 256-byte pages, 64 pages, 64 blocks | check |
| 9 | READ STATUS: C0h (not protected, ready, pass) | check |
| 10 | READ STATUS bit 7 low with WP# asserted | check |
| 11 | READ (00h-30h): R/B# low for tR = 25 clocks | check |
| 12 | erased page reads FFh (and FFh past the page end) | check |
| 13 | PROGRAM (80h-10h): R/B# low for tPROG = 200 clocks | check |
| 14 | status after program: ready, pass | check |
| 15 | programmed page reads back | check |
| 16 | page read with RE# high for 1..4 clocks between bytes | check |
| 17 | pages in other blocks / pages are independent | check |
| 18 | partial program: written bytes stored | check |
| 19 | partial program: unwritten bytes of the page stay FFh | check |
| 20 | ERASE (60h-D0h): R/B# low for tBERS = 2000 clocks | check |
| 21 | status after erase: ready, pass | check |
| 22 | erased block reads FFh | check |
| 23 | erase leaves other blocks intact | check |
| 24 | erase clears the first and last page of the block | check |
| 25 | erase leaves the last page of the previous block intact | check |
| 26 | program with WP# asserted: status protected + FAIL | check |
| 27 | erase with WP# asserted: status protected + FAIL | check |
| 28 | write-protected program / erase leave the array unchanged | check |
| 29 | next program with WP# released passes (FAIL cleared) | check |
| 30 | GET FEATURES returns P1 written by SET FEATURES | check |
| 31 | GET FEATURES returns P2..P4 | check |
| 32 | unwritten feature address reads 00h | check |
| 33 | status bit 6 low while the array is busy | check |
| 34 | status bit 6 high once ready | check |
| 35 | 00h after 70h resumes page data output | check |
| 36 | RESET (FFh): R/B# low for tRST = 10 clocks | check |
| 37 | status after RESET: C0h | check |
| 38 | busy during erase | check |
| 39 | reset pin ends the busy period | check |

## 3. UVM 測試平台內容

UVM 測試需商用模擬器（VCS / Xcelium / Questa）執行；開源流程只做 elaboration（L1a）。

| 項目 | 數量 | 名稱 |
|---|---|---|
| UVM tests | 3 | `memory_base_test`, `memory_coverage_regression_test`, `onfi_deep_test` |
| Sequences | 54 | `ddr_seq_item`, `ddr_base_seq`, `ddr_rw_seq`, `ddr_sweep_seq`, `ddr_cov_cmd_seq`, `ddr_cov_bank_seq`, `ddr_cov_bl_seq`, `emmc_seq_item`, `emmc_base_seq`, `emmc_rw_seq`, `emmc_sweep_seq`, `emmc_cov_cmd_seq`, `emmc_cov_bw_seq`, `hbm_seq_item`, `hbm_base_seq`, `hbm_rw_seq`, `hbm_sweep_seq`, `hbm_cov_cmd_seq`, `hbm_cov_ch_seq`, `lpddr_seq_item` |
| SVA（assert / cover property） | 31 / 35 | `assert_l1_cmd_io`, `cover_l1_cmd_io`, `assert_l1_addr_io`, `cover_l1_addr_io`, `assert_l1_we_re`, `cover_l1_we_re`, `assert_l1_cle_ale`, `cover_l1_cle_ale`, `assert_l2_cmd_ce`, `cover_l2_cmd_ce`, `assert_l2_addr_ce`, `cover_l2_addr_ce` … |
| Covergroups / coverpoints | 11 / 17 | |

## 4. 充分度判定與缺口

判定：**✅ Sufficient**（39 個 check，mutation score 100%）。

模型未實作的功能（不在測試範圍）：

- Not modelled (limitations, not tested): column addressing, the ONFI 2-column + 3-row address format, multi-plane/cache operations.

