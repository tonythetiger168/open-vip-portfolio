# IEEE 1588 PTP 測試套件（PTP-VIP）

> 由 `tools/gen_test_suite_docs.py` 依 VIP 內容、`func_report.csv` 與 `mutation_report.csv` 自動產生，請勿手動修改。

## 1. 概要

| 項目 | 內容 |
|---|---|
| 類別 | Networking |
| 類型 | UVM VIP |
| 功能測試 | 1 個檔案，18 個 check，全部通過 |
| Mutation | 8/10 個 mutant 被偵測（80%） |
| 判定 | **✅ Sufficient**（18 個 check，mutation score 80%） |

## 2. 可執行的功能測試

執行：`python3 tools/run_func_tests.py PTP-VIP`（Icarus Verilog 或 Verilator 5.052）。

### `tb/smoke_func_tb.sv`

結果：**PASS**（iverilog，18 checks）

| # | Check | 類型 |
|---|---|---|
| 1 | clock reset to zero | check |
| 2 | valids quiet | check |
| 3 | clock steps by 8ns | check |
| 4 | event valid strobe | check |
| 5 | event timestamp not in the future | check |
| 6 | event timestamp near capture point | check |
| 7 | event strobe is a pulse | check |
| 8 | egress valid | check |
| 9 | egress timestamp not in the future | check |
| 10 | egress strobe is a pulse | check |
| 11 | clock continues stepping | check |

## 3. UVM 測試平台內容

UVM agent test（`ptp_func_test`：directed + constrained-random 流量，scoreboard 以 DUT 模型的參考模型逐筆比對，並比對 driver 與 monitor 的 transaction）在 Verilator 上以 `python3 tools/run_uvm_tests.py PTP-VIP` 執行；agent 由 `tools/gen_uvm_agents.py` 依 `tools/uvm_agents/` 的協定 spec 產生。

| 項目 | 數量 | 名稱 |
|---|---|---|
| UVM tests | 2 | `ptp_base_test`, `ptp_func_test` |
| Sequences | 3 | `ptp_base_sequence`, `ptp_directed_sequence`, `ptp_transaction` |
| SVA（assert / cover property） | 3 / 2 | - |
| Covergroups / coverpoints | 1 / 1 | |

## 4. 充分度判定與缺口

判定：**✅ Sufficient**（18 個 check，mutation score 80%）。

未被偵測的 mutant（測試缺口或等價 mutant）：

- `dut_ptp_model.sv:28 1'b0 inverted [ev_d         <= 1'b0;]`
- `dut_ptp_model.sv:32 && flipped [if (event_i && !ev_d) begin]`

