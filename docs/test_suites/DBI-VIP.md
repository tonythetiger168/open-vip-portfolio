# MIPI DBI (Display Bus Interface) 測試套件（DBI-VIP）

> 由 `tools/gen_test_suite_docs.py` 依 VIP 內容、`func_report.csv` 與 `mutation_report.csv` 自動產生，請勿手動修改。

## 1. 概要

| 項目 | 內容 |
|---|---|
| 類別 | MIPI |
| 類型 | UVM VIP |
| 功能測試 | 1 個檔案，15 個 check，全部通過 |
| Mutation | 9/10 個 mutant 被偵測（90%） |
| 判定 | **✅ Sufficient**（15 個 check，mutation score 90%） |

## 2. 可執行的功能測試

執行：`python3 tools/run_func_tests.py DBI-VIP`（Icarus Verilog 或 Verilator 5.052）。

### `tb/func_dbi_tb.sv`

結果：**PASS**（verilator，15 checks）

模型合約與範圍（摘自測試檔頭）：

```text
func_dbi_tb.sv -- self-checking functional test for the MIPI DBI (type B,
8-bit) display controller model (dbi_display_controller, flattened by
smoke/flatten.py). Run: python3 tools/run_func_tests.py DBI-VIP

Model contract (from tb/top_tb.sv and dbi_defs_pkg):
   a write is latched on the WRX rising edge with CSX low, if WRX was low for
   at least DBI_MIN_WR_LOW=2 clocks; DCX=0 selects a command, DCX=1 a
   parameter/pixel. Parameters are stored per command and read back with
   RDX low, DCX high (unset commands read cmd^0xA5). Memory write (0x2C)
   streams pixels into GRAM (256 B, auto-increment, wraps) but only after
   sleep-out (0x11). RESX low resets the controller state.
```

| # | Check | 類型 |
|---|---|---|
| 1 | data bus not driven out of reset | check |
| 2 | read before any command: command 00h default (00h ^ A5h) | check |
| 3 | parameter of MADCTL reads back | check |
| 4 | data bus released after the read strobe | check |
| 5 | parameter of COLMOD reads back | check |
| 6 | parameters are stored per command | check |
| 7 | unset command reads the default cmd^0xA5 | check |
| 8 | memory write ignored before sleep-out (0x11) | check |
| 9 | memory write streams pixels with address auto-increment | check |
| 10 | new memory-write command restarts at address 0 | check |
| 11 | WRX low pulse shorter than 2 clocks is ignored | check |
| 12 | write with CSX high is ignored | check |
| 13 | GRAM address wraps after 256 pixels | check |
| 14 | after RESX: command pointer cleared, short WRX pulse ignored | check |
| 15 | after RESX, memory write needs sleep-out again | check |

## 3. UVM 測試平台內容

UVM 測試需商用模擬器（VCS / Xcelium / Questa）執行；開源流程只做 elaboration（L1a）。

| 項目 | 數量 | 名稱 |
|---|---|---|
| UVM tests | 3 | `dbi_base_test`, `dbi_random_test`, `dbi_regression_test` |
| Sequences | 10 | `dbi_base_sequence`, `dbi_cmd_write_seq`, `dbi_param_write_seq`, `dbi_pixel_write_seq`, `dbi_read_back_seq`, `dbi_error_inject_seq`, `dbi_reset_seq`, `dbi_random_sequence`, `dbi_regression_sequence`, `dbi_transaction` |
| SVA（assert / cover property） | 21 / 2 | `a_dbi_l1_clk`, `a_dbi_l1_rst`, `a_dbi_l1_state`, `a_dbi_l1_valid`, `a_dbi_trans_idle`, `a_dbi_trans_command_write`, `a_dbi_trans_param_write`, `a_dbi_trans_pixel_write`, `a_dbi_trans_read_back`, `a_dbi_l3_reset_idle`, `a_dbi_l3_no_stuck`, `a_dbi_l3_full_cycle` … |
| Covergroups / coverpoints | 3 / 8 | |

## 4. 充分度判定與缺口

判定：**✅ Sufficient**（15 個 check，mutation score 90%）。

未被偵測的 mutant（測試缺口或等價 mutant）：

- `dut_dbi_display_controller.sv:33 0 -> 1 [gram_addr <= 0; gram_mode <= 0; initialized <= 0;]`

