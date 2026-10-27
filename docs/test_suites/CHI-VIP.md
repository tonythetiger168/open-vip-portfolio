# CHI 測試套件（CHI-VIP）

> 由 `tools/gen_test_suite_docs.py` 依 VIP 內容、`func_report.csv` 與 `mutation_report.csv` 自動產生，請勿手動修改。

## 1. 概要

| 項目 | 內容 |
|---|---|
| 類別 | AMBA |
| 類型 | RTL IP |
| 功能測試 | 2 個檔案，86 個 check，6489 次斷言評估，全部通過 |
| Mutation | 12/12 個 mutant 被偵測（100%） |
| 判定 | **✅ Sufficient**（86 個 check，mutation score 100%） |

## 2. 可執行的功能測試

執行：`python3 tools/run_func_tests.py CHI-VIP`（Icarus Verilog 或 Verilator 5.052）。

### `tb/CHI_tb.sv`

結果：**PASS**（verilator，6489 次斷言評估）

### `tb/func_chi_tb.sv`

結果：**PASS**（iverilog，86 checks）

| # | Check | 類型 |
|---|---|---|
| 1 | request accepted with a free credit | check |
| 2 | response valid RSP_LAT+1 clocks after the accepting edge (%0d) | check |
| 3 | response flit carries opcode OK, txnID and addr[15:0] | check |
| 4 | one response per request, then idle | check |
| 5 | irq pulses with the response (irq=%0d rsp=%0d mismatch=%0d) | check |
| 6 | response held without a response credit | check |
| 7 | response sent once the credit arrives | check |
| 8 | request accepted on the last credit | check |
| 9 | a request is accepted on the last credit (%0d) | check |
| 10 | irq mirrors rxrspflitv throughout | check |

## 3. UVM 測試平台內容

RTL IP：以 `tb/` 的 self-checking testbench 驗證，無 UVM 測試。

## 4. 充分度判定與缺口

判定：**✅ Sufficient**（86 個 check，mutation score 100%）。

無已知缺口。

