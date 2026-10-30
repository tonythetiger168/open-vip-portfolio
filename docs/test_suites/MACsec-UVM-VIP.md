# MACsec (IEEE 802.1AE, GCM-AES-128) 測試套件（MACsec-UVM-VIP）

> 由 `tools/gen_test_suite_docs.py` 依 VIP 內容、`func_report.csv` 與 `mutation_report.csv` 自動產生，請勿手動修改。

## 1. 概要

| 項目 | 內容 |
|---|---|
| 類別 | Security |
| 類型 | UVM VIP |
| 功能測試 | 1 個檔案，50 個 check，全部通過 |
| Mutation | 39/39 個 mutant 被偵測（100%） |
| 判定 | **✅ Sufficient**（50 個 check，mutation score 100%） |

## 2. 可執行的功能測試

執行：`python3 tools/run_func_tests.py MACsec-UVM-VIP`（Icarus Verilog 或 Verilator 5.052）。

### `tb/smoke_func_tb.sv`

結果：**PASS**（iverilog，50 checks）

模型合約與範圍（摘自測試檔頭）：

```text
Functional smoke testbench (MACsec DUT model)
```

| # | Check | 類型 |
|---|---|---|
| 1 | nothing out in reset | check |
| 2 | reference AES-128: FIPS-197 C.1 | check |
| 3 | reference H for the zero key (GCM test case 1) | check |
| 4 | GCM test case 1 tag | check |
| 5 | GCM test case 2 ciphertext | check |
| 6 | GCM test case 2 tag | check |
| 7 | no status or output after reset without a frame | check |
| 8 | integrity only: data sent in clear and delivered | check |
| 9 | one last-byte strobe per delivered frame (%0d) | check |

## 3. UVM 測試平台內容

UVM agent test（`macsec_func_test`：directed + constrained-random 流量，scoreboard 以 DUT 模型的參考模型逐筆比對，並比對 driver 與 monitor 的 transaction）在 Verilator 上以 `python3 tools/run_uvm_tests.py MACsec-UVM-VIP` 執行；agent 由 `tools/gen_uvm_agents.py` 依 `tools/uvm_agents/` 的協定 spec 產生。

| 項目 | 數量 | 名稱 |
|---|---|---|
| UVM tests | 2 | `macsec_base_test`, `macsec_func_test` |
| Sequences | 3 | `macsec_base_sequence`, `macsec_directed_sequence`, `macsec_transaction` |
| SVA（assert / cover property） | 3 / 2 | - |
| Covergroups / coverpoints | 1 / 5 | |

## 4. 充分度判定與缺口

判定：**✅ Sufficient**（50 個 check，mutation score 100%）。

無已知缺口。

