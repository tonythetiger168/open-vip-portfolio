# MIPI SPMI 測試套件（SPMI-VIP）

> 由 `tools/gen_test_suite_docs.py` 依 VIP 內容、`func_report.csv` 與 `mutation_report.csv` 自動產生，請勿手動修改。

## 1. 概要

| 項目 | 內容 |
|---|---|
| 類別 | MIPI |
| 類型 | UVM VIP |
| 功能測試 | 1 個檔案，15 個 check，全部通過 |
| Mutation | 24/29 個 mutant 被偵測（83%） |
| 判定 | **✅ Sufficient**（15 個 check，mutation score 83%） |

## 2. 可執行的功能測試

執行：`python3 tools/run_func_tests.py SPMI-VIP`（Icarus Verilog 或 Verilator 5.052）。

### `tb/func_spmi_tb.sv`

結果：**PASS**（iverilog，15 checks）

模型合約與範圍（摘自測試檔頭）：

```text
func_spmi_tb.sv -- self-checking functional test for the MIPI SPMI slave
model (spmi_slave_model, flattened by smoke/flatten.py).
Run: python3 tools/run_func_tests.py SPMI-VIP

Model contract (from tb/top_tb.sv):
   a Sequence Start Condition (SDATA pulses high while SCLK stays low for at
   least 3 system clocks) starts a frame. Bits are sampled on SCLK rising
   edges: slave address[3:0], command[3:0], register address[7:0], parity.
   For a matching address and Register Write (2) / Register Read (3) the
   slave drives an ACK bit (1); a read then returns data[7:0] + parity
   (^data) from the slave, a write takes data[7:0] + parity from the
   master. SLAVE_ADDR = 2. Other addresses / commands get no response.
```

| # | Check | 類型 |
|---|---|---|
| 1 | slave does not drive SDATA after power-up | check |
| 2 | Register Write to own address is ACKed | check |
| 3 | Register Write stores the data byte | check |
| 4 | slave releases SDATA after the write | check |
| 5 | Register Read returns the written byte | check |
| 6 | slave drives SDATA for all 8 data cells and the parity cell | check |
| 7 | read data parity bit is ^data | check |
| 8 | slave releases SDATA after the read | check |
| 9 | registers are independent | check |
| 10 | second register reads back with parity | check |
| 11 | unwritten register reads 0 | check |
| 12 | frame for another slave address is ignored (no ACK) | check |
| 13 | unsupported command is ignored (no ACK) | check |
| 14 | short SDATA pulse is not taken as a start condition | check |
| 15 | a proper frame after the glitch still works | check |

## 3. UVM 測試平台內容

UVM 測試需商用模擬器（VCS / Xcelium / Questa）執行；開源流程只做 elaboration（L1a）。

| 項目 | 數量 | 名稱 |
|---|---|---|
| UVM tests | 3 | `spmi_base_test`, `spmi_random_test`, `spmi_regression_test` |
| Sequences | 10 | `spmi_base_sequence`, `spmi_reg_write_seq`, `spmi_reg_read_seq`, `spmi_addr_corner_seq`, `spmi_all_sa_seq`, `spmi_back_to_back_seq`, `spmi_error_inject_seq`, `spmi_random_sequence`, `spmi_regression_sequence`, `spmi_transaction` |
| SVA（assert / cover property） | 20 / 2 | `a_spmi_l1_clk`, `a_spmi_l1_rst`, `a_spmi_l1_state`, `a_spmi_l1_valid`, `a_spmi_trans_idle`, `a_spmi_trans_ssc`, `a_spmi_trans_command`, `a_spmi_trans_data`, `a_spmi_trans_ack_park`, `a_spmi_l3_reset_idle`, `a_spmi_l3_no_stuck`, `a_spmi_l3_full_cycle` … |
| Covergroups / coverpoints | 4 / 9 | |

## 4. 充分度判定與缺口

判定：**✅ Sufficient**（15 個 check，mutation score 83%）。

未被偵測的 mutant（測試缺口或等價 mutant）：

- `dut_spmi_slave_model.sv:24 0 -> 1 [vif_slv_sdata_o  = 0;]`
- `dut_spmi_slave_model.sv:44 0 -> 1 [n = 0;]`
- `dut_spmi_slave_model.sv:45 3 -> 4 [while (n < 3 && vif_sclk_i === 1'b0) begin]`
- `dut_spmi_slave_model.sv:45 < -> <= in condition [while (n < 3 && vif_sclk_i === 1'b0) begin]`
- `dut_spmi_slave_model.sv:47 1 -> 2 [if (vif_sclk_i === 1'b0) n = n + 1;]`

