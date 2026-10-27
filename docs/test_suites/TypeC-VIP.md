# USB Type-C Port Controller 測試套件（TypeC-VIP）

> 由 `tools/gen_test_suite_docs.py` 依 VIP 內容、`func_report.csv` 與 `mutation_report.csv` 自動產生，請勿手動修改。

## 1. 概要

| 項目 | 內容 |
|---|---|
| 類別 | USB |
| 類型 | UVM VIP |
| 功能測試 | 1 個檔案，11 個 check，全部通過 |
| Mutation | 1/1 個 mutant 被偵測（100%） |
| 判定 | **✅ Sufficient**（11 個 check，mutation score 100%） |

## 2. 可執行的功能測試

執行：`python3 tools/run_func_tests.py TypeC-VIP`（Icarus Verilog 或 Verilator 5.052）。

### `tb/func_typec_tb.sv`

結果：**PASS**（iverilog，11 checks）

模型合約與範圍（摘自測試檔頭）：

```text
func_typec_tb.sv -- self-checking functional test for the USB Type-C
partner termination model (typec_partner_model, flattened by
smoke/flatten.py). Run: python3 tools/run_func_tests.py TypeC-VIP

Model contract (from tb/top_tb.sv and typec_defs_pkg):
   the partner presents CC terminations by mode, one clock after the mode
   changes: SNK = Rd on CC1 / open on CC2 (plug orientation), SRC = Rp/Rp,
   AUDIO accessory = Ra/Ra, DEBUG accessory = Rd/Rd. cc_glitch_req forces
   both lines open (detach / debounce stimulus); reset opens both lines.
```

| # | Check | 類型 |
|---|---|---|
| 1 | both CC lines open in reset (unattached) | check |
| 2 | sink partner: Rd on CC1, CC2 open (orientation) | check |
| 3 | source partner: Rp on both CC lines | check |
| 4 | audio accessory: Ra on both CC lines | check |
| 5 | debug accessory: Rd on both CC lines | check |
| 6 | glitch request opens both lines | check |
| 7 | terminations restored after the glitch | check |
| 8 | mode change takes effect on the next clock edge | check |
| 9 | asynchronous reset opens both lines | check |
| 10 | terminations follow the mode after reset | check |
| 11 | a held glitch request keeps both lines open | check |

## 3. UVM 測試平台內容

UVM 測試需商用模擬器（VCS / Xcelium / Questa）執行；開源流程只做 elaboration（L1a）。

| 項目 | 數量 | 名稱 |
|---|---|---|
| UVM tests | 3 | `typec_base_test`, `typec_random_test`, `typec_regression_test` |
| Sequences | 13 | `typec_base_sequence`, `typec_snk_attach_seq`, `typec_src_attach_seq`, `typec_drp_try_src_seq`, `typec_audio_acc_seq`, `typec_debug_acc_seq`, `typec_vconn_seq`, `typec_cc_glitch_seq`, `typec_bad_vconn_seq`, `typec_reset_seq`, `typec_random_sequence`, `typec_regression_sequence`, `typec_transaction` |
| SVA（assert / cover property） | 23 / 2 | `a_typec_l1_clk`, `a_typec_l1_rst`, `a_typec_l1_state`, `a_typec_l1_valid`, `a_typec_trans_unattached`, `a_typec_trans_attachwait`, `a_typec_trans_attached_snk`, `a_typec_trans_attached_src`, `a_typec_trans_audio`, `a_typec_trans_debug`, `a_typec_trans_try_src`, `a_typec_l3_reset_unattached` … |
| Covergroups / coverpoints | 3 / 9 | |

## 4. 充分度判定與缺口

判定：**✅ Sufficient**（11 個 check，mutation score 100%）。

無已知缺口。

