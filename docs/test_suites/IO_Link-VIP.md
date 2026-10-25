# IO-Link 測試套件（IO_Link-VIP）

> 由 `tools/gen_test_suite_docs.py` 依 VIP 內容、`func_report.csv` 與 `mutation_report.csv` 自動產生，請勿手動修改。

## 1. 概要

| 項目 | 內容 |
|---|---|
| 類別 | Industrial |
| 類型 | UVM VIP |
| 功能測試 | 1 個檔案，7 個 check，全部通過 |
| Mutation | 23/30 個 mutant 被偵測（77%） |
| 判定 | **🟡 Partial**（只有 7 個 check） |

## 2. 可執行的功能測試

執行：`python3 tools/run_func_tests.py IO_Link-VIP`（Icarus Verilog 或 Verilator 5.052）。

### `tb/smoke_func_tb.sv`

結果：**PASS**（iverilog，7 checks）

| # | Check | 類型 |
|---|---|---|
| 1 | tx line idle high | check |
| 2 | handshakes quiet | check |
| 3 | tx_cnf after transmission | check |
| 4 | serial frame observed on tx | check |
| 5 | serialised data integrity | check |
| 6 | rx_valid after host byte | check |
| 7 | received data integrity | check |

## 3. UVM 測試平台內容

UVM 測試需商用模擬器（VCS / Xcelium / Questa）執行；開源流程只做 elaboration（L1a）。

| 項目 | 數量 | 名稱 |
|---|---|---|
| UVM tests | 1 | `io_link_base_test` |
| Sequences | 2 | `io_link_base_sequence`, `io_link_transaction` |
| SVA（assert / cover property） | 3 / 2 | - |
| Covergroups / coverpoints | 1 / 3 | |

## 4. 充分度判定與缺口

判定：**🟡 Partial**（只有 7 個 check）。

未被偵測的 mutant（測試缺口或等價 mutant）：

- `dut_io_link_model.sv:38 1'b0 inverted [rstart  <= 1'b0;]`
- `dut_io_link_model.sv:59 1'b0 inverted [tsh  <= {1'b0, tsh[7:1]};]`
- `dut_io_link_model.sv:63 1'b1 inverted [tx  <= 1'b1;]`
- `dut_io_link_model.sv:75 == flipped [if (tst == TX_IDLE && tx_cnf)]`
- `dut_io_link_model.sv:75 && flipped [if (tst == TX_IDLE && tx_cnf)]`
- `dut_io_link_model.sv:76 1'b0 inverted [tx_cnf <= 1'b0;]`
- `dut_io_link_model.sv:91 1'b0 inverted [rstart   <= 1'b0;]`

