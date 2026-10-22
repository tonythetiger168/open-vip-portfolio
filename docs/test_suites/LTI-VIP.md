# ARM Local Translation Interface 測試套件（LTI-VIP）

> 由 `tools/gen_test_suite_docs.py` 依 VIP 內容、`func_report.csv` 與 `mutation_report.csv` 自動產生，請勿手動修改。

## 1. 概要

| 項目 | 內容 |
|---|---|
| 類別 | Interconnect |
| 類型 | UVM VIP |
| 功能測試 | 1 個檔案，10 個 check，全部通過 |
| Mutation | 15/16 個 mutant 被偵測（94%） |
| 判定 | **✅ Sufficient**（10 個 check，mutation score 94%） |

## 2. 可執行的功能測試

執行：`python3 tools/run_func_tests.py LTI-VIP`（Icarus Verilog 或 Verilator 5.052）。

### `tb/func_lti_tb.sv`

結果：**PASS**（iverilog，10 checks）

模型合約與範圍（摘自測試檔頭）：

```text
func_lti_tb.sv -- self-checking functional test for the Arm LTI
translation-unit model (lti_translation_unit_model, flattened by
smoke/flatten.py). Run: python3 tools/run_func_tests.py LTI-VIP

Model contract (from tb/top_tb.sv):
   LA channel: request (la_id, la_addr) accepted on la_valid && la_ready;
   la_ready is randomly throttled and low while a translation is pending
   (one outstanding request). LR channel: after 1..6 clocks a one-clock
   lr_valid returns the same id with resp OK and paddr = VA (identity map),
   or resp FAULT and paddr 0 when VA[51:48] == 0xF.
```

| # | Check | 類型 |
|---|---|---|
| 1 | no ready / no response during reset | check |
| 2 | translation returns the request id, OKAY and the identity-mapped PA | check |
| 3 | VA[51:48]=0xF faults with PA 0 | check |
| 4 | VA just below the fault region translates | check |
| 5 | every response arrives within 1..7 clocks of acceptance | check |
| 6 | 80 random requests: ids, responses and PAs all correct | check |
| 7 | six distinct translation latencies, one per timer value 1..6 (%0d..%0d, %0d values) | check |
| 8 | la_ready is low while a translation is outstanding | XFAIL（模型缺陷） |
| 9 | exactly one single-clock lr_valid per request | check |
| 10 | reset clears pending state | check |

## 3. UVM 測試平台內容

UVM 測試需商用模擬器（VCS / Xcelium / Questa）執行；開源流程只做 elaboration（L1a）。

| 項目 | 數量 | 名稱 |
|---|---|---|
| UVM tests | 3 | `lti_base_test`, `lti_random_test`, `lti_regression_test` |
| Sequences | 11 | `lti_base_sequence`, `lti_low_addr_seq`, `lti_high_addr_seq`, `lti_id_sweep_seq`, `lti_same_va_seq`, `lti_back_to_back_seq`, `lti_error_inject_seq`, `lti_reset_seq`, `lti_random_sequence`, `lti_regression_sequence`, `lti_transaction` |
| SVA（assert / cover property） | 19 / 2 | `a_lti_l1_clk`, `a_lti_l1_rst`, `a_lti_l1_state`, `a_lti_l1_valid`, `a_lti_trans_idle`, `a_lti_trans_request`, `a_lti_trans_translate`, `a_lti_trans_response`, `a_lti_trans_fault`, `a_lti_l3_reset_idle`, `a_lti_l3_no_stuck`, `a_lti_l3_full_cycle` … |
| Covergroups / coverpoints | 3 / 9 | |

## 4. 充分度判定與缺口

判定：**✅ Sufficient**（10 個 check，mutation score 94%）。

未被偵測的 mutant（測試缺口或等價 mutant）：

- `dut_lti_translation_unit_model.sv:63 > -> >= in condition [if (xlate_timer > 1) begin]`

DUT 模型缺陷（XFAIL check，修好模型後會變成 XPASS 提醒移除標記）：

- la_ready is low while a translation is outstanding

