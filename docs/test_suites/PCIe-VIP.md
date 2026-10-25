# PCIe 測試套件（PCIe-VIP）

> 由 `tools/gen_test_suite_docs.py` 依 VIP 內容、`func_report.csv` 與 `mutation_report.csv` 自動產生，請勿手動修改。

## 1. 概要

| 項目 | 內容 |
|---|---|
| 類別 | Interconnect |
| 類型 | UVM VIP |
| 功能測試 | 1 個檔案，11 個 check，全部通過 |
| Mutation | 4/7 個 mutant 被偵測（57%） |
| 判定 | **🟡 Partial**（mutation score 57%） |

## 2. 可執行的功能測試

執行：`python3 tools/run_func_tests.py PCIe-VIP`（Icarus Verilog 或 Verilator 5.052）。

### `tb/smoke_func_tb.sv`

結果：**PASS**（verilator，11 checks）

| # | Check | 類型 |
|---|---|---|
| 1 | TLP beat during reset is ignored | check |
| 2 | single-beat write TLP counted once | check |
| 3 | single-beat write TLP data stored at TLP address | check |
| 4 | in_tlp set between SOP and EOP | check |
| 5 | multi-beat write TLP counted once at EOP | check |
| 6 | in_tlp cleared after EOP | check |
| 7 | payload DW0 at addr+0 | check |
| 8 | payload DW1 at addr+4 | check |
| 9 | payload DW2 at addr+8 | check |
| 10 | subsequent TLP increments write count | check |
| 11 | posted write overwrites previous contents | check |

## 3. UVM 測試平台內容

UVM 測試需商用模擬器（VCS / Xcelium / Questa）執行；開源流程只做 elaboration（L1a）。

| 項目 | 數量 | 名稱 |
|---|---|---|
| UVM tests | 6 | `mp_base_test`, `mp_error_inject_test`, `mp_pcie_gen5_test`, `mp_pcie_gen6_test`, `mp_power_mgmt_test`, `mp_random_regression_test` |
| Sequences | 10 | `mp_base_sequence`, `mp_back_to_back_sequence`, `mp_stress_sequence`, `mp_corner_case_sequence`, `mp_reset_sequence`, `mp_error_inject_sequence`, `mp_power_mgmt_sequence`, `mp_random_sequence`, `mp_regression_sequence`, `mp_sequence_item` |
| SVA（assert / cover property） | 28 / 25 | `assert_valid_ready`, `assert_sop_eop`, `assert_link_state`, `assert_p_pcie_tlp_fmt`, `cover_p_pcie_tlp_fmt`, `assert_p_pcie_tlp_type`, `cover_p_pcie_tlp_type`, `assert_p_pcie_tag_range`, `cover_p_pcie_tag_range`, `assert_p_pcie_tc_range`, `cover_p_pcie_tc_range`, `assert_p_pcie_length_dw` … |
| Covergroups / coverpoints | 7 / 20 | |

## 4. 充分度判定與缺口

判定：**🟡 Partial**（mutation score 57%）。

未被偵測的 mutant（測試缺口或等價 mutant）：

- `dut_mp_endpoint_mem_model.sv:18 0 -> 1 [int wr_count = 0, rd_count = 0;]`
- `dut_mp_endpoint_mem_model.sv:20 0 -> 1 [bit        in_tlp = 0;]`
- `dut_mp_endpoint_mem_model.sv:24 0 -> 1 [in_tlp <= 0;]`

