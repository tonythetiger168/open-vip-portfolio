# PCIe IDE (AES-256-GCM) 測試套件（PCIe_IDE-UVM-VIP）

> 由 `tools/gen_test_suite_docs.py` 依 VIP 內容、`func_report.csv` 與 `mutation_report.csv` 自動產生，請勿手動修改。

## 1. 概要

| 項目 | 內容 |
|---|---|
| 類別 | Security |
| 類型 | UVM VIP |
| 功能測試 | 1 個檔案，44 個 check，全部通過 |
| Mutation | 25/28 個 mutant 被偵測（89%） |
| 判定 | **✅ Sufficient**（44 個 check，mutation score 89%） |

## 2. 可執行的功能測試

執行：`python3 tools/run_func_tests.py PCIe_IDE-UVM-VIP`（Icarus Verilog 或 Verilator 5.052）。

### `tb/smoke_func_tb.sv`

結果：**PASS**（iverilog，44 checks）

模型合約與範圍（摘自測試檔頭）：

```text
Functional smoke testbench (IDE DUT model)
```

| # | Check | 類型 |
|---|---|---|
| 1 | nothing out in reset | check |
| 2 | reference AES-256: FIPS-197 C.3 | check |
| 3 | reference H for the zero 256-bit key (GCM test case 13) | check |
| 4 | GCM test case 13 tag | check |
| 5 | GCM test case 14 ciphertext | check |
| 6 | GCM test case 14 tag | check |
| 7 | no status or output without a TLP | check |
| 8 | TLP without a prefix: delivered as it came | check |
| 9 | 48-DW plain TLP: delivered | check |
| 10 | plain TLPs still pass while insecure | check |
| 11 | K_SET_GO for stream 4: just a message | check |
| 12 | K_SET_GO for stream 3: consumed | check |
| 13 | one last-DW strobe per delivered TLP (%0d / %0d) | check |

## 3. UVM 測試平台內容

UVM agent test（`ide_func_test`：directed + constrained-random 流量，scoreboard 以 DUT 模型的參考模型逐筆比對，並比對 driver 與 monitor 的 transaction）在 Verilator 上以 `python3 tools/run_uvm_tests.py PCIe_IDE-UVM-VIP` 執行；agent 由 `tools/gen_uvm_agents.py` 依 `tools/uvm_agents/` 的協定 spec 產生。

| 項目 | 數量 | 名稱 |
|---|---|---|
| UVM tests | 2 | `ide_base_test`, `ide_func_test` |
| Sequences | 3 | `ide_base_sequence`, `ide_directed_sequence`, `ide_transaction` |
| SVA（assert / cover property） | 3 / 2 | - |
| Covergroups / coverpoints | 1 / 4 | |

## 4. 充分度判定與缺口

判定：**✅ Sufficient**（44 個 check，mutation score 89%）。

未被偵測的 mutant（測試缺口或等價 mutant）：

- `dut_ide_model.sv:104 16 -> 17 [for (int j = 0; j < 16; j++) v[127 - 8*j -: 8] = (from + j <]`
- `dut_ide_model.sv:173 3 -> 4 [for (int i = 0; i < 3; i++) ob[i] <= {rb[4 + 4*i], rb[5 + 4*]`
- `dut_ide_model.sv:178 4 -> 5 [for (int j = 0; j < 4; j++) if (16*b + 4*j < plen) ob[3 + 4*]`

