# TileLink (TL-UL/TL-C) 測試套件（TileLink-VIP）

> 由 `tools/gen_test_suite_docs.py` 依 VIP 內容、`func_report.csv` 與 `mutation_report.csv` 自動產生，請勿手動修改。

## 1. 概要

| 項目 | 內容 |
|---|---|
| 類別 | Interconnect |
| 類型 | UVM VIP |
| 功能測試 | 1 個檔案，10 個 check，全部通過 |
| Mutation | 7/7 個 mutant 被偵測（100%） |
| 判定 | **✅ Sufficient**（10 個 check，mutation score 100%） |

## 2. 可執行的功能測試

執行：`python3 tools/run_func_tests.py TileLink-VIP`（Icarus Verilog 或 Verilator 5.052）。

### `tb/func_tilelink_tb.sv`

結果：**PASS**（verilator，10 checks）

模型合約與範圍（摘自測試檔頭）：

```text
func_tilelink_tb.sv -- self-checking functional test for the TileLink-UL
device model (tilelink_device_model, flattened by smoke/flatten.py).
Run: python3 tools/run_func_tests.py TileLink-VIP

Model contract (from tb/top_tb.sv), TL-UL A/D channels:
   A beat accepted on a_valid && a_ready (a_ready randomly throttled, one
   request outstanding). One clock later D returns AccessAck (0) for
   PutFullData (A opcode 0) or AccessAckData (1) with the stored word for
   Get (A opcode 4); unwritten addresses read 0. Other A opcodes are
   answered with AccessAck and a `uvm_warning.
```

| # | Check | 類型 |
|---|---|---|
| 1 | A not ready and D idle during reset | check |
| 2 | PutFullData answered with AccessAck | check |
| 3 | D response one clock after the A beat is accepted | check |
| 4 | Get answered with AccessAckData and the stored word | check |
| 5 | Get of an unwritten address returns 0 | check |
| 6 | 50 random Put/Get: opcodes and data match the reference | check |
| 7 | exactly one D beat per A request | check |
| 8 | a_ready low while a request is outstanding | XFAIL（模型缺陷） |
| 9 | unsupported A opcode (PutPartialData) answered with AccessAck | check |
| 10 | reset clears ready and D valid | check |

## 3. UVM 測試平台內容

UVM 測試需商用模擬器（VCS / Xcelium / Questa）執行；開源流程只做 elaboration（L1a）。

| 項目 | 數量 | 名稱 |
|---|---|---|
| UVM tests | 3 | `tilelink_base_test`, `tilelink_random_test`, `tilelink_regression_test` |
| Sequences | 12 | `tilelink_base_sequence`, `tilelink_put_seq`, `tilelink_get_seq`, `tilelink_wr_rd_same_addr_seq`, `tilelink_size_sweep_seq`, `tilelink_data_corner_seq`, `tilelink_addr_sweep_seq`, `tilelink_error_inject_seq`, `tilelink_reset_seq`, `tilelink_random_sequence`, `tilelink_regression_sequence`, `tilelink_transaction` |
| SVA（assert / cover property） | 18 / 3 | `a_tilelink_l1_clk`, `a_tilelink_l1_rst`, `a_tilelink_l1_state`, `a_tilelink_l1_valid`, `a_tilelink_trans_idle`, `a_tilelink_trans_a_channel`, `a_tilelink_trans_d_channel`, `a_tilelink_trans_retry`, `a_tilelink_l3_reset_idle`, `a_tilelink_l3_no_stuck`, `a_tilelink_l3_full_cycle`, `a_tilelink_l3_back_idle` … |
| Covergroups / coverpoints | 3 / 8 | |

## 4. 充分度判定與缺口

判定：**✅ Sufficient**（10 個 check，mutation score 100%）。

DUT 模型缺陷（XFAIL check，修好模型後會變成 XPASS 提醒移除標記）：

- a_ready low while a request is outstanding

