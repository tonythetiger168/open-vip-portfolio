# UART 測試套件（UART-VIP）

> 由 `tools/gen_test_suite_docs.py` 依 VIP 內容、`func_report.csv` 與 `mutation_report.csv` 自動產生，請勿手動修改。

## 1. 概要

| 項目 | 內容 |
|---|---|
| 類別 | Serial |
| 類型 | UVM VIP |
| 功能測試 | 1 個檔案，11 個 check，全部通過 |
| Mutation | 13/19 個 mutant 被偵測（68%） |
| 判定 | **🟡 Partial**（mutation score 68%） |

## 2. 可執行的功能測試

執行：`python3 tools/run_func_tests.py UART-VIP`（Icarus Verilog 或 Verilator 5.052）。

### `tb/smoke_func_tb.sv`

結果：**PASS**（iverilog，11 checks）

| # | Check | 類型 |
|---|---|---|
| 1 | : echo received | check |
| 2 | : echo byte matches | check |
| 3 | rxd idle high after reset | check |

## 3. UVM 測試平台內容

UVM 測試需商用模擬器（VCS / Xcelium / Questa）執行；開源流程只做 elaboration（L1a）。

| 項目 | 數量 | 名稱 |
|---|---|---|
| UVM tests | 3 | `uart_base_test`, `uart_random_test`, `uart_regression_test` |
| Sequences | 10 | `uart_base_sequence`, `uart_write_seq`, `uart_read_seq`, `uart_burst_seq`, `uart_back_to_back_seq`, `uart_error_inject_seq`, `uart_reset_seq`, `uart_random_sequence`, `uart_regression_sequence`, `uart_transaction` |
| SVA（assert / cover property） | 19 / 2 | `a_uart_l1_clk`, `a_uart_l1_rst`, `a_uart_l1_state`, `a_uart_l1_valid`, `a_uart_trans_idle`, `a_uart_trans_start_bit`, `a_uart_trans_data_bits`, `a_uart_trans_parity`, `a_uart_trans_stop_bit`, `a_uart_l3_reset_idle`, `a_uart_l3_no_stuck`, `a_uart_l3_full_cycle` … |
| Covergroups / coverpoints | 3 / 8 | |

## 4. 充分度判定與缺口

判定：**🟡 Partial**（mutation score 68%）。

未被偵測的 mutant（測試缺口或等價 mutant）：

- `dut_uart_loopback_model.sv:27 2 -> 3 [repeat (BAUD_DIV/2) @(posedge vif_clk);]`
- `dut_uart_loopback_model.sv:39 && flipped [if (stopb === 1'b1 && !(slot === 1'b0 && ^d === 1'b1)) begin]`
- `dut_uart_loopback_model.sv:39 1'b0 inverted [if (stopb === 1'b1 && !(slot === 1'b0 && ^d === 1'b1)) begin]`
- `dut_uart_loopback_model.sv:39 1'b1 inverted [if (stopb === 1'b1 && !(slot === 1'b0 && ^d === 1'b1)) begin]`
- `dut_uart_loopback_model.sv:57 0 -> 1 [echo_pending = (echo_q.size() > 0);]`
- `dut_uart_loopback_model.sv:61 8 -> 9 [for (int i = 0; i < 8; i++) begin]`

