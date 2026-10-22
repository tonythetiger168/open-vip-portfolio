# ATB 測試套件（ATB-UVM-VIP）

> 由 `tools/gen_test_suite_docs.py` 依 VIP 內容、`func_report.csv` 與 `mutation_report.csv` 自動產生，請勿手動修改。

## 1. 概要

| 項目 | 內容 |
|---|---|
| 類別 | Debug |
| 類型 | UVM VIP |
| 功能測試 | 1 個檔案，9 個 check，全部通過 |
| Mutation | 4/6 個 mutant 被偵測（67%） |
| 判定 | **🟡 Partial**（只有 9 個 check） |

## 2. 可執行的功能測試

執行：`python3 tools/run_func_tests.py ATB-UVM-VIP`（Icarus Verilog 或 Verilator 5.052）。

### `tb/smoke_func_tb.sv`

結果：**PASS**（iverilog，9 checks）

| # | Check | 類型 |
|---|---|---|
| 1 | handshakes reset low | check |
| 2 | no afready without afvalid | check |
| 3 | afready after afvalid | check |
| 4 | afready drops after afvalid | check |
| 5 | trace beats accepted over time | check |
| 6 | flush suppresses afready | check |

## 3. UVM 測試平台內容

UVM 測試需商用模擬器（VCS / Xcelium / Questa）執行；開源流程只做 elaboration（L1a）。

| 項目 | 數量 | 名稱 |
|---|---|---|
| UVM tests | 1 | `atb_base_test` |
| Sequences | 2 | `atb_base_sequence`, `atb_transaction` |
| SVA（assert / cover property） | 3 / 2 | - |
| Covergroups / coverpoints | 1 / 4 | |

## 4. 充分度判定與缺口

判定：**🟡 Partial**（只有 9 個 check）。

未被偵測的 mutant（測試缺口或等價 mutant）：

- `dut_atb_model.sv:24 1'b0 inverted [flush_d    <= 1'b0;]`
- `dut_atb_model.sv:26 && flipped [at_ready   <= at_valid && !at_ready;]`

