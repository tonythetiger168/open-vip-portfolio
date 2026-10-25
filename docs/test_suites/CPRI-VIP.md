# CPRI v8.0 (eCPRI over CPR) 測試套件（CPRI-VIP）

> 由 `tools/gen_test_suite_docs.py` 依 VIP 內容、`func_report.csv` 與 `mutation_report.csv` 自動產生，請勿手動修改。

## 1. 概要

| 項目 | 內容 |
|---|---|
| 類別 | Telecom |
| 類型 | UVM VIP |
| 功能測試 | 1 個檔案，17 個 check，全部通過 |
| Mutation | 19/19 個 mutant 被偵測（100%） |
| 判定 | **✅ Sufficient**（17 個 check，mutation score 100%） |

## 2. 可執行的功能測試

執行：`python3 tools/run_func_tests.py CPRI-VIP`（Icarus Verilog 或 Verilator 5.052）。

### `tb/func_cpri_tb.sv`

結果：**PASS**（iverilog，17 checks）

模型合約與範圍（摘自測試檔頭）：

```text
func_cpri_tb.sv -- self-checking functional test for the CPRI slave model
(cpri_slave_dut, flattened by smoke/flatten.py).
Run: python3 tools/run_func_tests.py CPRI-VIP

Model contract (from tb/top_tb.sv and cpri_defs_pkg):
   K28.5 comma words (tx_k=1, tx_data=0xBCBCBCBC) advance a comma counter;
   slv_state leaves RESET for L1_SYNC on the first comma and the slave
   becomes synchronised after 4 commas, after which slv_state follows the
   master's state. In LINK_ACTIVE, tx data/k are looped back on rx one clock
   later; otherwise rx is 0. LOS returns the slave to RESET.
```

| # | Check | 類型 |
|---|---|---|
| 1 | slave in RESET before any comma | check |
| 2 | K28.5 pattern without K flag does not count as comma | check |
| 3 | first comma moves slave to L1_SYNC | check |
| 4 | slave synchronised after 4 commas | check |
| 5 | slave follows master into PROTOCOL_SETUP | check |
| 6 | slave follows master into LINK_PASSIVE | check |
| 7 | no data loopback before LINK_ACTIVE | check |
| 8 | slave reaches LINK_ACTIVE | check |
| 9 | data word looped back in LINK_ACTIVE | check |
| 10 | K character and K flag looped back | check |
| 11 | LOS returns the slave to RESET, unsynced | check |
| 12 | no loopback after LOS | check |
| 13 | 2 commas are not enough to re-sync | check |
| 14 | data word restarts the count: 3 commas after it are not enough | check |
| 15 | re-sync after 4 commas following LOS | check |
| 16 | reset clears state | check |
| 17 | reset clears the looped-back K flag | check |

## 3. UVM 測試平台內容

UVM 測試需商用模擬器（VCS / Xcelium / Questa）執行；開源流程只做 elaboration（L1a）。

| 項目 | 數量 | 名稱 |
|---|---|---|
| UVM tests | 3 | `cpri_base_test`, `cpri_random_test`, `cpri_regression_test` |
| Sequences | 12 | `cpri_base_sequence`, `cpri_link_startup_seq`, `cpri_iq_data_seq`, `cpri_hyperframe_seq`, `cpri_iq_corner_seq`, `cpri_los_inject_seq`, `cpri_resync_seq`, `cpri_error_inject_seq`, `cpri_reset_seq`, `cpri_random_sequence`, `cpri_regression_sequence`, `cpri_transaction` |
| SVA（assert / cover property） | 20 / 2 | `a_cpri_l1_clk`, `a_cpri_l1_rst`, `a_cpri_l1_state`, `a_cpri_l1_valid`, `a_cpri_trans_reset`, `a_cpri_trans_l1_sync`, `a_cpri_trans_proto_setup`, `a_cpri_trans_cmi_setup`, `a_cpri_trans_link_passive`, `a_cpri_trans_link_active`, `a_cpri_l3_reset_idle`, `a_cpri_l3_startup` … |
| Covergroups / coverpoints | 3 / 7 | |

## 4. 充分度判定與缺口

判定：**✅ Sufficient**（17 個 check，mutation score 100%）。

無已知缺口。

