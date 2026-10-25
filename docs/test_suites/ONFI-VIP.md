# ONFI 測試套件（ONFI-VIP）

> 由 `tools/gen_test_suite_docs.py` 依 VIP 內容、`func_report.csv` 與 `mutation_report.csv` 自動產生，請勿手動修改。

## 1. 概要

| 項目 | 內容 |
|---|---|
| 類別 | Memory |
| 類型 | UVM VIP |
| 功能測試 | 1 個檔案，37 個 check，全部通過 |
| Mutation | 7/8 個 mutant 被偵測（88%） |
| 判定 | **✅ Sufficient**（37 個 check，mutation score 88%） |

## 2. 可執行的功能測試

執行：`python3 tools/run_func_tests.py ONFI-VIP`（Icarus Verilog 或 Verilator 5.052）。

### `tb/func_onfi_tb.sv`

結果：**PASS**（verilator，37 checks）

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
[6] ready, [0] FAIL. READ ID / parameter page return "ONFI".

Not modelled (limitations, not tested): column addressing, the ONFI
2-column + 3-row address format, multi-plane/cache operations.
```

| # | Check | 類型 |
|---|---|---|
| 1 | reset: ready, IO bus released | check |
| 2 | READ ID (address 20h) returns the ONFI signature | check |
| 3 | READ ID 5th byte 01h, then wraps | check |
| 4 | IO not driven with CE# high | check |
| 5 | parameter page starts with the ONFI signature | check |
| 6 | parameter page integrity CRC (bytes 254-255) valid | XFAIL（模型缺陷） |
| 7 | READ STATUS: C0h (not protected, ready, pass) | check |
| 8 | READ STATUS bit 7 low with WP# asserted | check |
| 9 | READ (00h-30h): R/B# low for tR = 25 clocks | check |
| 10 | erased page reads FFh (and FFh past the page end) | check |
| 11 | PROGRAM (80h-10h): R/B# low for tPROG = 200 clocks | check |
| 12 | status after program: ready, pass | check |
| 13 | programmed page reads back | check |
| 14 | page read with RE# high for 1..4 clocks between bytes | check |
| 15 | pages in other blocks / pages are independent | check |
| 16 | partial program: written bytes stored | check |
| 17 | partial program: unwritten bytes of the page stay FFh | XFAIL（模型缺陷） |
| 18 | ERASE (60h-D0h): R/B# low for tBERS = 2000 clocks | check |
| 19 | status after erase: ready, pass | check |
| 20 | erased block reads FFh | check |
| 21 | erase leaves other blocks intact | check |
| 22 | erase clears the first and last page of the block | check |
| 23 | erase leaves the last page of the previous block intact | check |
| 24 | program with WP# asserted: status protected + FAIL | check |
| 25 | erase with WP# asserted: status protected + FAIL | check |
| 26 | write-protected program / erase leave the array unchanged | check |
| 27 | next program with WP# released passes (FAIL cleared) | check |
| 28 | GET FEATURES returns P1 written by SET FEATURES | check |
| 29 | GET FEATURES returns P2..P4 | XFAIL（模型缺陷） |
| 30 | unwritten feature address reads 00h | check |
| 31 | status bit 6 low while the array is busy | check |
| 32 | status bit 6 high once ready | check |
| 33 | 00h after 70h resumes page data output | XFAIL（模型缺陷） |
| 34 | RESET (FFh): R/B# low for tRST = 10 clocks | check |
| 35 | status after RESET: C0h | check |
| 36 | busy during erase | check |
| 37 | reset pin ends the busy period | check |

## 3. UVM 測試平台內容

UVM 測試需商用模擬器（VCS / Xcelium / Questa）執行；開源流程只做 elaboration（L1a）。

| 項目 | 數量 | 名稱 |
|---|---|---|
| UVM tests | 3 | `memory_base_test`, `memory_coverage_regression_test`, `onfi_deep_test` |
| Sequences | 54 | `ddr_seq_item`, `ddr_base_seq`, `ddr_rw_seq`, `ddr_sweep_seq`, `ddr_cov_cmd_seq`, `ddr_cov_bank_seq`, `ddr_cov_bl_seq`, `emmc_seq_item`, `emmc_base_seq`, `emmc_rw_seq`, `emmc_sweep_seq`, `emmc_cov_cmd_seq`, `emmc_cov_bw_seq`, `hbm_seq_item`, `hbm_base_seq`, `hbm_rw_seq`, `hbm_sweep_seq`, `hbm_cov_cmd_seq`, `hbm_cov_ch_seq`, `lpddr_seq_item` |
| SVA（assert / cover property） | 31 / 35 | `assert_l1_cmd_io`, `cover_l1_cmd_io`, `assert_l1_addr_io`, `cover_l1_addr_io`, `assert_l1_we_re`, `cover_l1_we_re`, `assert_l1_cle_ale`, `cover_l1_cle_ale`, `assert_l2_cmd_ce`, `cover_l2_cmd_ce`, `assert_l2_addr_ce`, `cover_l2_addr_ce` … |
| Covergroups / coverpoints | 11 / 17 | |

## 4. 充分度判定與缺口

判定：**✅ Sufficient**（37 個 check，mutation score 88%）。

未被偵測的 mutant（測試缺口或等價 mutant）：

- `dut_onfi_nand_model.sv:195 1'b1 inverted [if (!vif_ce_n && prev_re_n == 1'b0 && vif_re_n == 1'b1) begi]`

DUT 模型缺陷（XFAIL check，修好模型後會變成 XPASS 提醒移除標記）：

- parameter page integrity CRC (bytes 254-255) valid
- partial program: unwritten bytes of the page stay FFh
- GET FEATURES returns P2..P4
- 00h after 70h resumes page data output

模型未實作的功能（不在測試範圍）：

- Not modelled (limitations, not tested): column addressing, the ONFI 2-column + 3-row address format, multi-plane/cache operations.

