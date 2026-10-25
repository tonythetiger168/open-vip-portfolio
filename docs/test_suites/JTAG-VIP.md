# JTAG 測試套件（JTAG-VIP）

> 由 `tools/gen_test_suite_docs.py` 依 VIP 內容、`func_report.csv` 與 `mutation_report.csv` 自動產生，請勿手動修改。

## 1. 概要

| 項目 | 內容 |
|---|---|
| 類別 | Storage/Debug |
| 類型 | UVM VIP |
| 功能測試 | 1 個檔案，25 個 check，全部通過 |
| Mutation | 10/12 個 mutant 被偵測（83%） |
| 判定 | **✅ Sufficient**（25 個 check，mutation score 83%） |

## 2. 可執行的功能測試

執行：`python3 tools/run_func_tests.py JTAG-VIP`（Icarus Verilog 或 Verilator 5.052）。

### `tb/func_jtag_tb.sv`

結果：**PASS**（verilator，25 checks）

模型合約與範圍（摘自測試檔頭）：

```text
func_jtag_tb.sv -- self-checking functional test for the IEEE 1149.1 TAP
model (jtag_tap_dut in top/top_tb.sv, flattened by smoke/flatten.py).
Run: python3 tools/run_func_tests.py JTAG-VIP

Model contract (from top/top_tb.sv): 16-state TAP controller (state codes
of common_pkg::tap_state_e), 5-bit IR (IDCODE 01 selected in
Test-Logic-Reset, SAMPLE 02, EXTEST 00, BYPASS 1F, any other code selects
a 32-bit user data register written on Update-DR), Capture-IR loads
0b00101, IDCODE 0x1ABC0043. TDI is sampled on the rising TCK edge, TDO
changes on the falling edge and is enabled only in Shift-IR/Shift-DR.
The next-state reference below is written from the 1149.1 state diagram.
```

| # | Check | 類型 |
|---|---|---|
| 1 | TRST: Test-Logic-Reset with IDCODE selected | check |
| 2 | state follows the 1149.1 diagram on a random TMS walk (%0d mismatches) | check |
| 3 | random walk covered all 32 TAP arcs (got %0d) | check |
| 4 | ir_shift/dr_shift flag exactly Shift-IR/Shift-DR | check |
| 5 | five TMS=1 reset | check |
| 6 | five TMS=1 reach Test-Logic-Reset and select IDCODE | check |
| 7 | IDCODE scanned out after reset (got %h) | check |
| 8 | IDCODE LSB is 1 | check |
| 9 | dr_len counts 32 shifted bits | check |
| 10 | Capture-IR loads ...01 into the IR shift register | check |
| 11 | Capture-IR value 00101 | check |
| 12 | BYPASS loaded on Update-IR | check |
| 13 | BYPASS captures 0 | check |
| 14 | BYPASS delays TDI by one bit (got %h) | check |
| 15 | user instruction 0x07 loaded | check |
| 16 | user DR written on Update-DR is captured back | check |
| 17 | second write captured back | check |
| 18 | SAMPLE captures 0xCAFE0001 | check |
| 19 | EXTEST captures 0 | check |
| 20 | IDCODE capture unaffected by shifted-in data | check |
| 21 | Update-DR under IDCODE does not write the user register | check |
| 22 | Pause-DR: TDO disabled | check |
| 23 | scan across Pause-DR shifts out the captured data | check |
| 24 | data shifted around Pause-DR is updated intact (got %h) | check |
| 25 | update without shifting writes the captured value back | check |
| 26 | TRST mid-scan: reset, IDCODE, TDO off | check |

## 3. UVM 測試平台內容

UVM 測試需商用模擬器（VCS / Xcelium / Questa）執行；開源流程只做 elaboration（L1a）。

| 項目 | 數量 | 名稱 |
|---|---|---|
| UVM tests | 12 | `base_test`, `jtag_random_test`, `jtag_regression_test`, `full_regression_test`, `sata_random_test`, `sata_regression_test`, `nvme_random_test`, `nvme_regression_test`, `bt5_random_test`, `bt5_regression_test`, `dp2_random_test`, `dp2_regression_test` |
| Sequences | 16 | `bluetooth5_transaction`, `base_tx`, `displayport2_transaction`, `jtag_base_sequence`, `jtag_random_sequence`, `jtag_idcode_sequence`, `jtag_bypass_sequence`, `jtag_reset_sequence`, `jtag_dr_scan_sequence`, `jtag_back_to_back_sequence`, `jtag_corner_sequence`, `jtag_stress_sequence`, `jtag_regression_sequence`, `jtag_transaction`, `nvme_transaction`, `sata_transaction` |
| SVA（assert / cover property） | 29 / 29 | `assert_p_jtag_tlr`, `cover_p_jtag_tlr`, `assert_p_jtag_tdo_oe`, `cover_p_jtag_tdo_oe`, `assert_p_jtag_tms`, `cover_p_jtag_tms`, `assert_p_jtag_tdi`, `cover_p_jtag_tdi`, `assert_p_jtag_tdo`, `cover_p_jtag_tdo`, `assert_p_jtag_shift`, `cover_p_jtag_shift` … |
| Covergroups / coverpoints | 3 / 9 | |

## 4. 充分度判定與缺口

判定：**✅ Sufficient**（25 個 check，mutation score 83%）。

未被偵測的 mutant（測試缺口或等價 mutant）：

- `dut_jtag_tap_dut.sv:51 1'b0 inverted [bypass_sr <= 1'b0;]`
- `dut_jtag_tap_dut.sv:123 1'b0 inverted [vif_tdo    <= 1'b0;]`

