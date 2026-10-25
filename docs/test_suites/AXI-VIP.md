# AXI 測試套件（AXI-VIP）

> 由 `tools/gen_test_suite_docs.py` 依 VIP 內容、`func_report.csv` 與 `mutation_report.csv` 自動產生，請勿手動修改。

## 1. 概要

| 項目 | 內容 |
|---|---|
| 類別 | AMBA |
| 類型 | UVM VIP |
| 功能測試 | 2 個檔案，51 個 check，全部通過 |
| Mutation | 23/23 個 mutant 被偵測（100%） |
| 判定 | **✅ Sufficient**（51 個 check，mutation score 100%） |

## 2. 可執行的功能測試

執行：`python3 tools/run_func_tests.py AXI-VIP`（Icarus Verilog 或 Verilator 5.052）。

### `tb/func_axi_tb.sv`

結果：**PASS**（iverilog，22 checks）

| # | Check | 類型 |
|---|---|---|
| 1 | reset: no B / R, WREADY low, AWREADY / ARREADY high | check |
| 2 | unwritten words (first and last of the 4 KB) read 0 | check |
| 3 | 16-beat INCR write / read | check |
| 4 | WRAP bursts of 2, 4, 8, 16 beats wrap at the burst boundary | check |
| 5 | FIXED burst: every beat to the same address, neighbours untouched | check |
| 6 | 256-beat INCR burst | check |
| 7 | 4-beat write to the error region: SLVERR | check |
| 8 | error-region write leaves the aliased memory unchanged | check |
| 9 | 4-beat read from the error region: SLVERR, zero data, RLAST on the last beat | check |
| 10 | 300 random FIXED / INCR / WRAP bursts match the AXI4 reference memory | check |
| 11 | RLAST only on the last beat, BRESP OKAY | check |
| 12 | BVALID held until BREADY | check |
| 13 | RVALID, RDATA and RLAST held stable while RREADY is low | check |
| 14 | W beat ahead of AW waits (WREADY low) | check |
| 15 | W beat presented before AW is written once AW arrives | check |
| 16 | AWREADY low while a write burst is active | check |
| 17 | after WLAST the next AW waits for the B handshake | check |
| 18 | AWREADY returns once B is accepted | check |
| 19 | AW during a write burst waits and does not redirect that burst's beats | check |
| 20 | write and read bursts active | check |
| 21 | reset aborts both bursts (WREADY, RVALID low, ARREADY high) | check |
| 22 | memory contents survive the reset | check |

### `tb/smoke_func_tb.sv`

結果：**PASS**（iverilog，29 checks）

| # | Check | 類型 |
|---|---|---|
| 1 | wready high once write burst active | check |
| 2 | bvalid asserted after WLAST | check |
| 3 | bvalid cleared after B handshake | check |
| 4 | rvalid high during read burst | check |
| 5 | rresp OKAY on good region | check |
| 6 | rlast low on first beat | check |
| 7 | rlast high on final beat | check |
| 8 | rvalid low after burst completes | check |
| 9 | awready high (always-ready AW) | check |
| 10 | arready high when no read burst | check |
| 11 | bresp OKAY on good write | check |
| 12 | read beat 0 equals written data | check |
| 13 | read beat 1 equals written data | check |
| 14 | wstrb masks unenabled byte lanes | check |
| 15 | bresp SLVERR on error region write | check |
| 16 | rresp SLVERR on error region read | check |
| 17 | error region read returns zero data | check |
| 18 | single-beat error read has rlast | check |

## 3. UVM 測試平台內容

UVM RAL test（`amba_ral_test`：hw_reset / bit_bash / mirror 等）在 Verilator 上以 `python3 tools/run_uvm_tests.py AXI-VIP` 執行（見 [docs/RAL.md](../RAL.md)）；其餘 UVM 測試需商用模擬器（VCS / Xcelium / Questa），開源流程只做 elaboration（L1a）。

| 項目 | 數量 | 名稱 |
|---|---|---|
| UVM tests | 5 | `amba_base_test`, `amba_axi_test`, `amba_axi_burst_test`, `amba_apb_test`, `amba_ral_test` |
| Sequences | 11 | `axi_base_sequence`, `axi_single_seq`, `axi_incr_burst_seq`, `axi_wrap_burst_seq`, `axi_back_to_back_seq`, `axi_error_inject_seq`, `axi_reset_seq`, `axi_stress_seq`, `axi_random_sequence`, `axi_regression_sequence`, `amba_seq_item` |
| SVA（assert / cover property） | 32 / 15 | `assert_axi_aw`, `assert_axi_wlast`, `assert_axi_bresp`, `assert_ahb_trans`, `assert_apb_en`, `assert_p_axi_awvalid_stable`, `cover_p_axi_awvalid_stable`, `assert_p_axi_awburst_valid`, `cover_p_axi_awburst_valid`, `assert_p_axi_awsize_valid`, `cover_p_axi_awsize_valid`, `assert_p_axi_bresp_valid` … |
| Covergroups / coverpoints | 8 / 42 | |

## 4. 充分度判定與缺口

判定：**✅ Sufficient**（51 個 check，mutation score 100%）。

無已知缺口。

