# AXI 測試套件（AXI-VIP）

> 由 `tools/gen_test_suite_docs.py` 依 VIP 內容、`func_report.csv` 與 `mutation_report.csv` 自動產生，請勿手動修改。

## 1. 概要

| 項目 | 內容 |
|---|---|
| 類別 | AMBA |
| 類型 | UVM VIP |
| 功能測試 | 1 個檔案，37 個 check，全部通過 |
| Mutation | 27/27 個 mutant 被偵測（100%） |
| 判定 | **✅ Sufficient**（37 個 check，mutation score 100%） |

## 2. 可執行的功能測試

執行：`python3 tools/run_func_tests.py AXI-VIP`（Icarus Verilog 或 Verilator 5.054）。

### `tb/smoke_func_tb.sv`

結果：**PASS**（iverilog，37 checks）

| # | Check | 類型 |
|---|---|---|
| 1 | reset: no B / R, WREADY low | check |
| 2 | unwritten words (first and last of the 4 KB) read 0 | check |
| 3 | 16-beat INCR write / read, OKAY, RLAST on the last beat | check |
| 4 | 256-beat INCR burst | check |
| 5 | WRAP bursts of 2, 4, 8, 16 beats wrap at the burst boundary | check |
| 6 | FIXED burst: every beat to the same address, the last one stays | check |
| 7 | 8 single-byte beats fill one word lane by lane | check |
| 8 | 2- and 4-byte narrow bursts, read back narrow and full width | check |
| 9 | unaligned 8-byte INCR: lanes 3-7 of the first beat, then aligned; byte 2 and word 2 untouched | check |
| 10 | unaligned 4-byte INCR: lanes 2-3, then 4-7, then 0-3 | check |
| 11 | unaligned narrow FIXED burst: lane 5 only, every beat | check |
| 12 | WSTRB outside a narrow beat's lanes writes nothing | check |
| 13 | sparse random strobes | check |
| 14 | error-region write: SLVERR, aliased memory unchanged | check |
| 15 | error-region read: SLVERR and zero data on every beat, RLAST | check |
| 16 | INCR ending on the last byte of a 4 KB page: OKAY | check |
| 17 | INCR crossing a 4 KB page: SLVERR, nothing written either side | check |
| 18 | narrow INCR up to the page end: OKAY | check |
| 19 | unaligned narrow INCR across the page: SLVERR | check |
| 20 | unaligned WRAP burst: SLVERR | check |
| 21 | 3-beat WRAP burst: SLVERR | check |
| 22 | 16-byte AxSIZE on a 64-bit bus: SLVERR | check |
| 23 | reserved burst type: SLVERR | check |
| 24 | illegal write burst answered SLVERR | check |
| 25 | four writes outstanding; a fifth AW waits | check |
| 26 | four reads outstanding; a fifth AR waits | check |
| 27 | W waits while four B responses are not taken | check |
| 28 | outstanding writes and reads on several IDs complete with the right data | check |
| 29 | B responses overtake older writes of other IDs (%0d) | check |
| 30 | R beats of different IDs interleave (%0d) | check |
| 31 | four reads of one ID: beats returned in issue order | check |
| 32 | four writes of one ID: B responses in issue order | check |
| 33 | 150 random batches (narrow, unaligned, FIXED / INCR / WRAP, SLVERR) match the reference memory | check |
| 34 | BVALID / RVALID and their payload held until READY | check |
| 35 | AWREADY / ARREADY back-pressure seen | check |
| 36 | reset drops B, R and WREADY | check |
| 37 | after reset: memory contents kept, new bursts complete | check |

## 3. UVM 測試平台內容

UVM RAL test（`amba_ral_test`：hw_reset / bit_bash / mirror 等）在 Verilator 上以 `python3 tools/run_uvm_tests.py AXI-VIP` 執行（見 [docs/RAL.md](../RAL.md)）；其餘 UVM 測試需商用模擬器（VCS / Xcelium / Questa），開源流程只做 elaboration（L1a）。

| 項目 | 數量 | 名稱 |
|---|---|---|
| UVM tests | 6 | `amba_base_test`, `amba_axi_test`, `amba_axi_burst_test`, `amba_apb_test`, `amba_ral_test`, `amba_axi_cov_test` |
| Sequences | 12 | `axi_base_sequence`, `axi_single_seq`, `axi_incr_burst_seq`, `axi_wrap_burst_seq`, `axi_back_to_back_seq`, `axi_error_inject_seq`, `axi_reset_seq`, `axi_stress_seq`, `axi_cov_sweep_seq`, `axi_random_sequence`, `axi_regression_sequence`, `amba_seq_item` |
| SVA（assert / cover property） | 39 / 17 | `assert_axi_aw`, `assert_axi_wlast`, `assert_axi_bresp`, `assert_ahb_trans`, `assert_apb_en`, `assert_p_axi_awvalid_stable`, `cover_p_axi_awvalid_stable`, `assert_p_axi_awburst_valid`, `cover_p_axi_awburst_valid`, `assert_p_axi_awsize_valid`, `cover_p_axi_awsize_valid`, `assert_p_axi_bresp_valid` … |
| Covergroups / coverpoints | 11 / 53 | |

## 4. 充分度判定與缺口

判定：**✅ Sufficient**（37 個 check，mutation score 100%）。

無已知缺口。

