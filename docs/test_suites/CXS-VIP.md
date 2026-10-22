# CXS CCIX Stream Interface 測試套件（CXS-VIP）

> 由 `tools/gen_test_suite_docs.py` 依 VIP 內容、`func_report.csv` 與 `mutation_report.csv` 自動產生，請勿手動修改。

## 1. 概要

| 項目 | 內容 |
|---|---|
| 類別 | Interconnect |
| 類型 | UVM VIP |
| 功能測試 | 1 個檔案，11 個 check，全部通過 |
| Mutation | 10/10 個 mutant 被偵測（100%） |
| 判定 | **✅ Sufficient**（11 個 check，mutation score 100%） |

## 2. 可執行的功能測試

執行：`python3 tools/run_func_tests.py CXS-VIP`（Icarus Verilog 或 Verilator 5.052）。

### `tb/func_cxs_tb.sv`

結果：**PASS**（iverilog，11 checks）

模型合約與範圍（摘自測試檔頭）：

```text
func_cxs_tb.sv -- self-checking functional test for the CXS receiver model
(cxs_receiver_model, flattened by smoke/flatten.py).
Run: python3 tools/run_func_tests.py CXS-VIP

Model contract (from tb/top_tb.sv):
   cxs_active_ack follows cxs_active_req one clock later. Flits are accepted
   only while active_ack is high; each accepted flit folds its 64-bit data
   into a running CRC-8 (poly 0x07, byte 0 first) that restarts at every
   packet; cxs_last ends a packet and bumps the packet counter. A gap
   (valid low) inside a packet abandons it. CRC and counters are internal,
   so the test reads them hierarchically (white-box).
```

| # | Check | 類型 |
|---|---|---|
| 1 | active_ack low out of reset | check |
| 2 | flit sent before active_ack is not accepted | check |
| 3 | active_ack follows active_req after one clock | check |
| 4 | single-flit packet counted with correct CRC-8 | check |
| 5 | 5-flit packet: CRC chained across flits | check |
| 6 | CRC restarts at each packet | check |
| 7 | packet abandoned on a valid gap (not counted) | check |
| 8 | next packet after abandon starts a fresh CRC | check |
| 9 | active_ack drops one clock after active_req | check |
| 10 | flits ignored after deactivation | check |
| 11 | reset clears ack and packet count | check |

## 3. UVM 測試平台內容

UVM 測試需商用模擬器（VCS / Xcelium / Questa）執行；開源流程只做 elaboration（L1a）。

| 項目 | 數量 | 名稱 |
|---|---|---|
| UVM tests | 3 | `cxs_base_test`, `cxs_random_test`, `cxs_regression_test` |
| Sequences | 12 | `cxs_base_sequence`, `cxs_single_flit_seq`, `cxs_multi_flit_seq`, `cxs_cntl_walk_seq`, `cxs_data_corner_seq`, `cxs_back_to_back_seq`, `cxs_deactivate_seq`, `cxs_error_inject_seq`, `cxs_reset_seq`, `cxs_random_sequence`, `cxs_regression_sequence`, `cxs_transaction` |
| SVA（assert / cover property） | 19 / 2 | `a_cxs_l1_clk`, `a_cxs_l1_rst`, `a_cxs_l1_state`, `a_cxs_l1_valid`, `a_cxs_trans_idle`, `a_cxs_trans_activate`, `a_cxs_trans_data_tx`, `a_cxs_trans_deactivate`, `a_cxs_trans_link_error`, `a_cxs_l3_reset_idle`, `a_cxs_l3_no_stuck`, `a_cxs_l3_full_cycle` … |
| Covergroups / coverpoints | 3 / 8 | |

## 4. 充分度判定與缺口

判定：**✅ Sufficient**（11 個 check，mutation score 100%）。

無已知缺口。

