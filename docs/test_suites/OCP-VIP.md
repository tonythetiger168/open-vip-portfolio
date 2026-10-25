# OCP-IP Open Core Protocol 測試套件（OCP-VIP）

> 由 `tools/gen_test_suite_docs.py` 依 VIP 內容、`func_report.csv` 與 `mutation_report.csv` 自動產生，請勿手動修改。

## 1. 概要

| 項目 | 內容 |
|---|---|
| 類別 | Interconnect |
| 類型 | UVM VIP |
| 功能測試 | 1 個檔案，12 個 check，全部通過 |
| Mutation | 6/6 個 mutant 被偵測（100%） |
| 判定 | **✅ Sufficient**（12 個 check，mutation score 100%） |

## 2. 可執行的功能測試

執行：`python3 tools/run_func_tests.py OCP-VIP`（Icarus Verilog 或 Verilator 5.052）。

### `tb/func_ocp_tb.sv`

結果：**PASS**（verilator，12 checks）

模型合約與範圍（摘自測試檔頭）：

```text
func_ocp_tb.sv -- self-checking functional test for the OCP slave model
(ocp_slave_model, flattened by smoke/flatten.py).
Run: python3 tools/run_func_tests.py OCP-VIP

Model contract (from tb/top_tb.sv), OCP 2.x basic signals:
   MCmd (WR=1, RD=2) is held until SCmdAccept (randomly throttled, low while
   a request is outstanding). After 1..4 clocks a one-clock SResp returns
   DVA (with SData for reads) or ERR for MAddr[11:8] == 0xF. Unwritten
   addresses read 0.
```

| # | Check | 類型 |
|---|---|---|
| 1 | no accept / no response with MCmd idle | check |
| 2 | write gets DVA response | check |
| 3 | read returns DVA with the written data | check |
| 4 | unwritten address reads 0 | check |
| 5 | write to MAddr[11:8]=0xF returns ERR | check |
| 6 | read from the error region returns ERR | check |
| 7 | second write overwrites the first | check |
| 8 | 60 random reads/writes: data, DVA and 1..4 clock latency all correct | check |
| 9 | every response latency 1..4 occurs (%0d/%0d/%0d/%0d) | check |
| 10 | exactly one single-clock SResp per request | check |
| 11 | SCmdAccept low while a request is outstanding | XFAIL（模型缺陷） |
| 12 | reset clears accept, response and pending state | check |

## 3. UVM 測試平台內容

UVM 測試需商用模擬器（VCS / Xcelium / Questa）執行；開源流程只做 elaboration（L1a）。

| 項目 | 數量 | 名稱 |
|---|---|---|
| UVM tests | 3 | `ocp_base_test`, `ocp_random_test`, `ocp_regression_test` |
| Sequences | 12 | `ocp_base_sequence`, `ocp_write_seq`, `ocp_read_seq`, `ocp_wr_rd_same_addr_seq`, `ocp_backpressure_seq`, `ocp_addr_sweep_seq`, `ocp_data_corner_seq`, `ocp_error_inject_seq`, `ocp_reset_seq`, `ocp_random_sequence`, `ocp_regression_sequence`, `ocp_transaction` |
| SVA（assert / cover property） | 19 / 2 | `a_ocp_l1_clk`, `a_ocp_l1_rst`, `a_ocp_l1_state`, `a_ocp_l1_valid`, `a_ocp_trans_idle`, `a_ocp_trans_write`, `a_ocp_trans_read`, `a_ocp_trans_wait_resp`, `a_ocp_trans_error_resp`, `a_ocp_l3_reset_idle`, `a_ocp_l3_no_stuck`, `a_ocp_l3_full_cycle` … |
| Covergroups / coverpoints | 3 / 9 | |

## 4. 充分度判定與缺口

判定：**✅ Sufficient**（12 個 check，mutation score 100%）。

DUT 模型缺陷（XFAIL check，修好模型後會變成 XPASS 提醒移除標記）：

- SCmdAccept low while a request is outstanding

