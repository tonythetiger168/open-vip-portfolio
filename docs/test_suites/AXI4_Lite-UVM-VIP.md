# AXI4-Lite 測試套件（AXI4_Lite-UVM-VIP）

> 由 `tools/gen_test_suite_docs.py` 依 VIP 內容、`func_report.csv` 與 `mutation_report.csv` 自動產生，請勿手動修改。

## 1. 概要

| 項目 | 內容 |
|---|---|
| 類別 | AMBA |
| 類型 | UVM VIP |
| 功能測試 | 1 個檔案，172 個 check，全部通過 |
| Mutation | 28/28 個 mutant 被偵測（100%） |
| 判定 | **✅ Sufficient**（172 個 check，mutation score 100%） |

## 2. 可執行的功能測試

執行：`python3 tools/run_func_tests.py AXI4_Lite-UVM-VIP`（Icarus Verilog 或 Verilator 5.052）。

### `tb/smoke_func_tb.sv`

結果：**PASS**（iverilog，172 checks）

模型合約與範圍（摘自測試檔頭）：

```text
Functional smoke testbench (AXI4-Lite DUT model)
```

| # | Check | 類型 |
|---|---|---|
| 1 | AW and W accepted | check |
| 2 | B response returned | check |
| 3 | AR accepted | check |
| 4 | R response returned | check |
| 5 | BVALID / RVALID low in reset | check |
| 6 | no response while the bus is idle (READY high without VALID) | check |
| 7 | word 0 reads 0 after reset, OKAY | check |
| 8 | 0x3FC: last word, OKAY | check |
| 9 | 0x400: first SLVERR address, rdata 0 | check |
| 10 | 0x7FC: last SLVERR address | check |
| 11 | 0x800: DECERR, rdata 0 | check |
| 12 | write AW + W together: OKAY | check |
| 13 | read back full word | check |
| 14 | AW first, W 3 clocks later | check |
| 15 | W first, AW 3 clocks later | check |
| 16 | byte strobe merge on lane 1 | check |
| 17 | byte strobe merge on lanes 3 and 0 | check |
| 18 | write with no strobe: OKAY, nothing written | check |
| 19 | unprivileged write to 0x3C0: SLVERR | check |
| 20 | unprivileged write did not land; reads are not restricted | check |
| 21 | privileged write to 0x3C0: OKAY | check |
| 22 | privileged write landed | check |
| 23 | 0x3BC is below the privileged region | check |
| 24 | 0x3FC is in the privileged region (AWPROT[0] = 0, others set) | check |
| 25 | write to 0x400: SLVERR | check |
| 26 | write to 0x800: DECERR | check |
| 27 | write to 0x7FC: SLVERR | check |
| 28 | error writes did not alias onto word 0 | check |
| 29 | error writes did not alias onto word 0xFF | check |
| 30 | one AW and one W accepted | check |
| 31 | AWREADY / WREADY low while B is pending | check |
| 32 | B held while BREADY is low | check |
| 33 | B dropped after BREADY | check |
| 34 | second AW not accepted while the first waits for W | check |
| 35 | both writes completed in order | check |
| 36 | first AW took the first W | check |
| 37 | second AW took the second W | check |
| 38 | second W not accepted while the first waits for AW | check |
| 39 | W-first: first W to the first AW | check |
| 40 | W-first: second W to the second AW | check |
| 41 | one AR accepted while R is pending | check |
| 42 | R held while RREADY is low | check |
| 43 | R dropped after RREADY | check |
| 44 | every 17th word written and read back | check |

## 3. UVM 測試平台內容

UVM agent test（`axi4_lite_func_test`：directed + constrained-random 流量，scoreboard 以 DUT 模型的參考模型逐筆比對，並比對 driver 與 monitor 的 transaction）在 Verilator 上以 `python3 tools/run_uvm_tests.py AXI4_Lite-UVM-VIP` 執行；agent 由 `tools/gen_uvm_agents.py` 依 `tools/uvm_agents/` 的協定 spec 產生。

| 項目 | 數量 | 名稱 |
|---|---|---|
| UVM tests | 2 | `axi4_lite_base_test`, `axi4_lite_func_test` |
| Sequences | 3 | `axi4_lite_base_sequence`, `axi4_lite_directed_sequence`, `axi4_lite_transaction` |
| SVA（assert / cover property） | 12 / 4 | - |
| Covergroups / coverpoints | 1 / 5 | |

## 4. 充分度判定與缺口

判定：**✅ Sufficient**（172 個 check，mutation score 100%）。

無已知缺口。

