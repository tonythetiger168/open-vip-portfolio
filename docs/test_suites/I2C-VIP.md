# I2C 測試套件（I2C-VIP）

> 由 `tools/gen_test_suite_docs.py` 依 VIP 內容、`func_report.csv` 與 `mutation_report.csv` 自動產生，請勿手動修改。

## 1. 概要

| 項目 | 內容 |
|---|---|
| 類別 | Serial |
| 類型 | UVM VIP |
| 功能測試 | 1 個檔案，6 個 check，全部通過 |
| Mutation | 17/23 個 mutant 被偵測（74%） |
| 判定 | **🟡 Partial**（只有 6 個 check） |

## 2. 可執行的功能測試

執行：`python3 tools/run_func_tests.py I2C-VIP`（Icarus Verilog 或 Verilator 5.052）。

### `tb/smoke_func_tb.sv`

結果：**PASS**（iverilog，6 checks）

| # | Check | 類型 |
|---|---|---|
| 1 | write: addr 0x50+W ACKed | check |
| 2 | write: data byte ACKed | check |
| 3 | read: addr 0x50+R ACKed | check |
| 4 | read: data == 0xA6 (write/read consistency) | check |
| 5 | wrong address 0x51 not ACKed | check |
| 6 | read: data == 0x5A after overwrite | check |

## 3. UVM 測試平台內容

UVM 測試需商用模擬器（VCS / Xcelium / Questa）執行；開源流程只做 elaboration（L1a）。

| 項目 | 數量 | 名稱 |
|---|---|---|
| UVM tests | 3 | `i2c_base_test`, `i2c_random_test`, `i2c_regression_test` |
| Sequences | 10 | `i2c_base_sequence`, `i2c_write_seq`, `i2c_read_seq`, `i2c_burst_seq`, `i2c_back_to_back_seq`, `i2c_error_inject_seq`, `i2c_reset_seq`, `i2c_random_sequence`, `i2c_regression_sequence`, `i2c_transaction` |
| SVA（assert / cover property） | 21 / 2 | `a_i2c_l1_clk`, `a_i2c_l1_rst`, `a_i2c_l1_state`, `a_i2c_l1_valid`, `a_i2c_trans_idle`, `a_i2c_trans_start`, `a_i2c_trans_addr`, `a_i2c_trans_ack`, `a_i2c_trans_write`, `a_i2c_trans_read`, `a_i2c_trans_stop`, `a_i2c_l3_reset_idle` … |
| Covergroups / coverpoints | 3 / 7 | |

## 4. 充分度判定與缺口

判定：**🟡 Partial**（只有 6 個 check）。

未被偵測的 mutant（測試缺口或等價 mutant）：

- `dut_i2c_slave_model.sv:21 0 -> 1 [vif_slv_sda_o  = 0;]`
- `dut_i2c_slave_model.sv:22 0 -> 1 [vif_slv_sda_oe = 0;]`
- `dut_i2c_slave_model.sv:32 0 -> 1 [vif_slv_sda_oe = 0;]`
- `dut_i2c_slave_model.sv:80 0 -> 1 [stop = 0;]`
- `dut_i2c_slave_model.sv:81 ! dropped in condition [while (!stop) begin]`
- `dut_i2c_slave_model.sv:88 ! dropped in condition [while (!nack) send_byte(mem[cur_addr], nack);]`

