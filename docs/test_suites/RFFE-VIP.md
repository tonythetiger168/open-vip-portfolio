# MIPI RFFE 測試套件（RFFE-VIP）

> 由 `tools/gen_test_suite_docs.py` 依 VIP 內容、`func_report.csv` 與 `mutation_report.csv` 自動產生，請勿手動修改。

## 1. 概要

| 項目 | 內容 |
|---|---|
| 類別 | MIPI |
| 類型 | UVM VIP |
| 功能測試 | 1 個檔案，14 個 check，全部通過 |
| Mutation | 25/29 個 mutant 被偵測（86%） |
| 判定 | **✅ Sufficient**（14 個 check，mutation score 86%） |

## 2. 可執行的功能測試

執行：`python3 tools/run_func_tests.py RFFE-VIP`（Icarus Verilog 或 Verilator 5.052）。

### `tb/func_rffe_tb.sv`

結果：**PASS**（iverilog，14 checks）

模型合約與範圍（摘自測試檔頭）：

```text
func_rffe_tb.sv -- self-checking functional test for the MIPI RFFE slave
model (rffe_slave_model, flattened by smoke/flatten.py).
Run: python3 tools/run_func_tests.py RFFE-VIP

Model contract (from tb/top_tb.sv):
   Sequence Start Condition (SDATA pulse with SCLK low >= 3 system clocks),
   then bits sampled on SCLK rising edges: SA[3:0], command[2:0]:
   Register-0 Write (010, no address), Register Write (011, 5-bit address),
   Extended Write (101, 8-bit address), Register Read (110, 5-bit address),
   Extended Read (111, 8-bit address); then a parity cell and a bus-park
   cell. Writes take data[7:0] + parity from the master; reads return
   data[7:0] + parity (^data) driven by the slave. SLAVE_ADDR = 3; other
   addresses are ignored. 32 registers + 256 extended registers.
```

| # | Check | 類型 |
|---|---|---|
| 1 | slave does not drive SDATA after power-up | check |
| 2 | frame during reset ignored | check |
| 3 | Register Write stores data at the 5-bit address | check |
| 4 | Register Read returns the byte, slave-driven | check |
| 5 | read data parity bit is ^data | check |
| 6 | slave releases SDATA after the read | check |
| 7 | Register-0 Write (no address field) writes register 0 | check |
| 8 | Extended Write stores data at the 8-bit address | check |
| 9 | Extended Read returns the byte with parity | check |
| 10 | extended space is separate from the register space | check |
| 11 | unwritten register reads 0 | check |
| 12 | write to another slave address is ignored | check |
| 13 | read for another slave address gets no response | check |
| 14 | slave resynchronises on the next start condition | check |

## 3. UVM 測試平台內容

UVM 測試需商用模擬器（VCS / Xcelium / Questa）執行；開源流程只做 elaboration（L1a）。

| 項目 | 數量 | 名稱 |
|---|---|---|
| UVM tests | 3 | `rffe_base_test`, `rffe_random_test`, `rffe_regression_test` |
| Sequences | 10 | `rffe_base_sequence`, `rffe_reg_write_seq`, `rffe_reg_read_seq`, `rffe_ext_seq`, `rffe_reg0_write_seq`, `rffe_all_slaves_seq`, `rffe_error_inject_seq`, `rffe_random_sequence`, `rffe_regression_sequence`, `rffe_transaction` |
| SVA（assert / cover property） | 19 / 2 | `a_rffe_l1_clk`, `a_rffe_l1_rst`, `a_rffe_l1_state`, `a_rffe_l1_valid`, `a_rffe_trans_idle`, `a_rffe_trans_ssc`, `a_rffe_trans_command_seq`, `a_rffe_trans_data_seq`, `a_rffe_trans_bus_park`, `a_rffe_l3_reset_idle`, `a_rffe_l3_no_stuck`, `a_rffe_l3_full_cycle` … |
| Covergroups / coverpoints | 4 / 10 | |

## 4. 充分度判定與缺口

判定：**✅ Sufficient**（14 個 check，mutation score 86%）。

未被偵測的 mutant（測試缺口或等價 mutant）：

- `dut_rffe_slave_model.sv:28 0 -> 1 [vif_slv_sdata_o  = 0;]`
- `dut_rffe_slave_model.sv:63 0 -> 1 [n = 0;]`
- `dut_rffe_slave_model.sv:64 3 -> 4 [while (n < 3 && vif_sclk_i === 1'b0) begin]`
- `dut_rffe_slave_model.sv:64 < -> <= in condition [while (n < 3 && vif_sclk_i === 1'b0) begin]`

