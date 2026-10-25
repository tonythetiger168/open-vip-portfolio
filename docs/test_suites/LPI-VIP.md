# ARM Q-Channel Low Power Interface 測試套件（LPI-VIP）

> 由 `tools/gen_test_suite_docs.py` 依 VIP 內容、`func_report.csv` 與 `mutation_report.csv` 自動產生，請勿手動修改。

## 1. 概要

| 項目 | 內容 |
|---|---|
| 類別 | Power |
| 類型 | UVM VIP |
| 功能測試 | 1 個檔案，12 個 check，全部通過 |
| Mutation | 14/16 個 mutant 被偵測（88%） |
| 判定 | **✅ Sufficient**（12 個 check，mutation score 88%） |

## 2. 可執行的功能測試

執行：`python3 tools/run_func_tests.py LPI-VIP`（Icarus Verilog 或 Verilator 5.052）。

### `tb/func_lpi_tb.sv`

結果：**PASS**（iverilog，12 checks）

模型合約與範圍（摘自測試檔頭）：

```text
func_lpi_tb.sv -- self-checking functional test for the AMBA LPI Q-channel
device model (lpi_device_model, flattened by smoke/flatten.py).
Run: python3 tools/run_func_tests.py LPI-VIP

Model contract (from tb/top_tb.sv), Q-channel handshake:
   Q_RUN     (QREQn=1, QACCEPTn=1, QDENY=0)
   Q_REQUEST (QREQn=0) -> QACCEPTn falls (Q_STOPPED) when QACTIVE=0,
                          QDENY rises (Q_DENIED) when QACTIVE=1
   QREQn=1 from Q_STOPPED -> QACCEPTn rises (Q_EXIT -> Q_RUN)
   QREQn=1 from Q_DENIED  -> QDENY falls (Q_CONTINUE -> Q_RUN)
   reset: QACCEPTn=0 (Q_STOPPED); QACCEPTn rises once QREQn is high.
```

| # | Check | 類型 |
|---|---|---|
| 1 | reset state is Q_STOPPED (QACCEPTn=0, QDENY=0) | check |
| 2 | device stays stopped while QREQn is low after reset | check |
| 3 | QREQn high exits to Q_RUN (QACCEPTn rises) | check |
| 4 | idle device accepts the request (Q_STOPPED) | check |
| 5 | Q_STOPPED is held while QREQn stays low | check |
| 6 | exit from Q_STOPPED back to Q_RUN | check |
| 7 | busy device denies the request (Q_DENIED) | check |
| 8 | Q_DENIED held until QREQn returns high | check |
| 9 | QDENY falls when QREQn returns high (Q_CONTINUE) | check |
| 10 | request after denial accepted once idle | check |
| 11 | reset forces Q_STOPPED | check |
| 12 | QACCEPTn low together with QDENY high never observed | check |

## 3. UVM 測試平台內容

UVM 測試需商用模擬器（VCS / Xcelium / Questa）執行；開源流程只做 elaboration（L1a）。

| 項目 | 數量 | 名稱 |
|---|---|---|
| UVM tests | 3 | `lpi_base_test`, `lpi_random_test`, `lpi_regression_test` |
| Sequences | 11 | `lpi_base_sequence`, `lpi_accept_seq`, `lpi_deny_seq`, `lpi_mixed_seq`, `lpi_long_stop_seq`, `lpi_active_hint_seq`, `lpi_back_to_back_seq`, `lpi_error_inject_seq`, `lpi_random_sequence`, `lpi_regression_sequence`, `lpi_transaction` |
| SVA（assert / cover property） | 21 / 2 | `a_lpi_l1_clk`, `a_lpi_l1_rst`, `a_lpi_l1_state`, `a_lpi_l1_valid`, `a_lpi_trans_q_stopped`, `a_lpi_trans_q_exit`, `a_lpi_trans_q_run`, `a_lpi_trans_q_request`, `a_lpi_trans_q_denied`, `a_lpi_trans_q_continue`, `a_lpi_l3_reset_idle`, `a_lpi_l3_no_stuck` … |
| Covergroups / coverpoints | 3 / 8 | |

## 4. 充分度判定與缺口

判定：**✅ Sufficient**（12 個 check，mutation score 88%）。

未被偵測的 mutant（測試缺口或等價 mutant）：

- `dut_lpi_device_model.sv:19 1'b0 inverted [vif_qacceptn = 1'b0;]`
- `dut_lpi_device_model.sv:20 1'b0 inverted [vif_qdeny    = 1'b0;]`

