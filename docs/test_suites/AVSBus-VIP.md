# AVSBus (Adaptive Voltage Scaling) 測試套件（AVSBus-VIP）

> 由 `tools/gen_test_suite_docs.py` 依 VIP 內容、`func_report.csv` 與 `mutation_report.csv` 自動產生，請勿手動修改。

## 1. 概要

| 項目 | 內容 |
|---|---|
| 類別 | Power |
| 類型 | UVM VIP |
| 功能測試 | 1 個檔案，14 個 check，全部通過 |
| Mutation | 11/12 個 mutant 被偵測（92%） |
| 判定 | **✅ Sufficient**（14 個 check，mutation score 92%） |

## 2. 可執行的功能測試

執行：`python3 tools/run_func_tests.py AVSBus-VIP`（Icarus Verilog 或 Verilator 5.052）。

### `tb/func_avsbus_tb.sv`

結果：**PASS**（verilator，14 checks）

模型合約與範圍（摘自測試檔頭）：

```text
func_avsbus_tb.sv -- self-checking functional test for the AVSBus regulator
model (avsbus_regulator_model, flattened by smoke/flatten.py).
Run: python3 tools/run_func_tests.py AVSBus-VIP

Model contract (from tb/top_tb.sv):
   master frame: 15 bits MSB first on avs_mdata, sampled on posedge, first
   bit flagged by avs_ctrl: [14]=start(1) [13:10]=opcode [9]=resp_req
   [8:1]=voltage id [0]=even parity over [13:1].
   opcodes SET_VOLT=1 GET_VOLT=2 ENABLE=3 DISABLE=4; SET_VOLT accepted for
   0x20 <= vid <= 0xC0. With resp_req the slave answers on avs_sdata after
   3 clocks: [14]=start [13:10]=status (ACK=A, ERR=F) [9]=0 [8:1]=vout
   [0]=parity, MSB first, one bit per clock.
```

| # | Check | 類型 |
|---|---|---|
| 1 | GET_VOLT returns the reset voltage 0x60 (SET sent during reset ignored) | check |
| 2 | response frame start bit / reserved bit | check |
| 3 | SET_VOLT in range is ACKed and echoes the new voltage | check |
| 4 | GET_VOLT reads back the programmed voltage | check |
| 5 | SET_VOLT below VMIN is rejected with ERR, voltage unchanged | check |
| 6 | SET_VOLT above VMAX is rejected with ERR | check |
| 7 | SET_VOLT at VMIN boundary accepted | check |
| 8 | SET_VOLT at VMAX boundary accepted | check |
| 9 | parity error is rejected with ERR and not applied | check |
| 10 | unknown opcode is rejected with ERR | check |
| 11 | ENABLE is ACKed and enables the rail | check |
| 12 | DISABLE is ACKed and disables the rail | check |
| 13 | no response frame when resp_req=0 | check |
| 14 | silent SET_VOLT was applied | check |

## 3. UVM 測試平台內容

UVM 測試需商用模擬器（VCS / Xcelium / Questa）執行；開源流程只做 elaboration（L1a）。

| 項目 | 數量 | 名稱 |
|---|---|---|
| UVM tests | 3 | `avsbus_base_test`, `avsbus_random_test`, `avsbus_regression_test` |
| Sequences | 11 | `avsbus_base_sequence`, `avsbus_set_voltage_seq`, `avsbus_get_voltage_seq`, `avsbus_enable_seq`, `avsbus_corner_voltage_seq`, `avsbus_no_resp_seq`, `avsbus_back_to_back_seq`, `avsbus_error_inject_seq`, `avsbus_random_sequence`, `avsbus_regression_sequence`, `avsbus_transaction` |
| SVA（assert / cover property） | 20 / 2 | `a_avsbus_l1_clk`, `a_avsbus_l1_rst`, `a_avsbus_l1_state`, `a_avsbus_l1_valid`, `a_avsbus_trans_idle`, `a_avsbus_trans_command`, `a_avsbus_trans_data_phase`, `a_avsbus_trans_ack`, `a_avsbus_l3_reset_idle`, `a_avsbus_l3_no_stuck`, `a_avsbus_l3_full_cycle`, `a_avsbus_l3_back_idle` … |
| Covergroups / coverpoints | 3 / 8 | |

## 4. 充分度判定與缺口

判定：**✅ Sufficient**（14 個 check，mutation score 92%）。

未被偵測的 mutant（測試缺口或等價 mutant）：

- `dut_avsbus_regulator_model.sv:24 1'b0 inverted [bit       enabled = 1'b0;]`

