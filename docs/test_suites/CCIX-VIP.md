# CCIX Cache Coherent Interconnect 測試套件（CCIX-VIP）

> 由 `tools/gen_test_suite_docs.py` 依 VIP 內容、`func_report.csv` 與 `mutation_report.csv` 自動產生，請勿手動修改。

## 1. 概要

| 項目 | 內容 |
|---|---|
| 類別 | Interconnect |
| 類型 | UVM VIP |
| 功能測試 | 1 個檔案，13 個 check，全部通過 |
| Mutation | 15/15 個 mutant 被偵測（100%） |
| 判定 | **✅ Sufficient**（13 個 check，mutation score 100%） |

## 2. 可執行的功能測試

執行：`python3 tools/run_func_tests.py CCIX-VIP`（Icarus Verilog 或 Verilator 5.052）。

### `tb/func_ccix_tb.sv`

結果：**PASS**（iverilog，13 checks）

模型合約與範圍（摘自測試檔頭）：

```text
func_ccix_tb.sv -- self-checking functional test for the CCIX agent model
(ccix_agent_model, flattened by smoke/flatten.py).
Run: python3 tools/run_func_tests.py CCIX-VIP

Model contract (from tb/top_tb.sv):
   link-up grants 4 credits on the first clock after reset; each received
   flit (tx_flit_valid) consumes one credit and is echoed one clock later on
   rx_flit as {2'b01, tx[61:56], tx[55:4], 4'd1}; the credit is returned 4
   clocks after the flit. vif_credit shows the current pool.
```

| # | Check | 類型 |
|---|---|---|
| 1 | no credits and no rx flit while in reset | check |
| 2 | link-up grants 4 credits | check |
| 3 | rx flit valid one clock after tx flit | check |
| 4 | rx flit carries header 01, payload, credit-return 1 | check |
| 5 | flit consumes one credit | check |
| 6 | rx valid is a single-clock pulse per flit | check |
| 7 | credit returned 4 clocks after the flit | check |
| 8 | 4 back-to-back flits drain all credits | check |
| 9 | all 4 credits returned after the burst | check |
| 10 | every flit of the burst is delivered | check |
| 11 | burst flits delivered in order | check |
| 12 | reset clears credits and rx | check |
| 13 | credits re-granted after reset | check |

## 3. UVM 測試平台內容

UVM 測試需商用模擬器（VCS / Xcelium / Questa）執行；開源流程只做 elaboration（L1a）。

| 項目 | 數量 | 名稱 |
|---|---|---|
| UVM tests | 3 | `ccix_base_test`, `ccix_random_test`, `ccix_regression_test` |
| Sequences | 11 | `ccix_base_sequence`, `ccix_link_up_seq`, `ccix_req_rsp_seq`, `ccix_snoop_seq`, `ccix_data_seq`, `ccix_credit_stress_seq`, `ccix_error_inject_seq`, `ccix_reset_seq`, `ccix_random_sequence`, `ccix_regression_sequence`, `ccix_transaction` |
| SVA（assert / cover property） | 19 / 2 | `a_ccix_l1_clk`, `a_ccix_l1_rst`, `a_ccix_l1_state`, `a_ccix_l1_valid`, `a_ccix_trans_reset`, `a_ccix_trans_link_up`, `a_ccix_trans_req_rsp`, `a_ccix_trans_mem_snoop`, `a_ccix_trans_error`, `a_ccix_l3_reset_idle`, `a_ccix_l3_no_stuck`, `a_ccix_l3_full_cycle` … |
| Covergroups / coverpoints | 3 / 8 | |

## 4. 充分度判定與缺口

判定：**✅ Sufficient**（13 個 check，mutation score 100%）。

無已知缺口。

