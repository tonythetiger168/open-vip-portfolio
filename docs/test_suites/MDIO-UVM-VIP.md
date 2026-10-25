# MDIO 測試套件（MDIO-UVM-VIP）

> 由 `tools/gen_test_suite_docs.py` 依 VIP 內容、`func_report.csv` 與 `mutation_report.csv` 自動產生，請勿手動修改。

## 1. 概要

| 項目 | 內容 |
|---|---|
| 類別 | Networking |
| 類型 | UVM VIP |
| 功能測試 | 2 個檔案，23 個 check，全部通過 |
| Mutation | 20/20 個 mutant 被偵測（100%） |
| 判定 | **✅ Sufficient**（23 個 check，mutation score 100%） |

## 2. 可執行的功能測試

執行：`python3 tools/run_func_tests.py MDIO-UVM-VIP`（Icarus Verilog 或 Verilator 5.052）。

### `tb/func_mdio_tb.sv`

結果：**PASS**（iverilog，12 checks）

模型合約與範圍（摘自測試檔頭）：

```text
func_mdio_tb.sv -- IEEE 802.3 Clause 22 functional test for the MDIO PHY
model (mdio_model, flattened by smoke/flatten.py); complements
smoke_func_tb.sv (status mirror, idle bus).
Run: python3 tools/run_func_tests.py MDIO-UVM-VIP

Model contract (from tb/top_tb.sv): mdio_status mirrors phy_status one
clock later. Frames follow Clause 22: 32-bit preamble of ones, ST 01, OP
10 (read) / 01 (write), PHYAD, REGAD, turnaround, 16 data bits, MSB
first; the PHY samples MDIO on MDC rising edges (MDC = 8 clocks here).
A read of PHYAD 5 (any REGAD) returns TA Z, 0, then phy_status; the PHY
changes MDIO one clock after an MDC rising edge and releases it after
the last data bit. Writes and other PHY addresses get no response.
```

| # | Check | 類型 |
|---|---|---|
| 1 | reset: status 0, MDIO released (pulled up) | check |
| 2 | mdio_status mirrors each phy_status bit | check |
| 3 | mdio_status updates on the next clock edge | check |
| 4 | write frame: PHY never drives MDIO | check |
| 5 | read of another PHY address: no response | check |
| 6 | read of PHY 5: TA 0 then phy_status, MSB first | check |
| 7 | MDIO released after the read frame | check |
| 8 | second read (other REGAD) returns the new status | check |
| 9 | read after a 20-bit preamble is not answered | check |
| 10 | reset clears status and the response state | check |
| 11 | 31-bit preamble: read not answered | check |
| 12 | exactly 32-bit preamble: read answered, every data bit down to bit 0 driven | check |

### `tb/smoke_func_tb.sv`

結果：**PASS**（iverilog，11 checks）

| # | Check | 類型 |
|---|---|---|
| 1 | mdio_status reset to zero | check |
| 2 | mdio pulled high (tri1) when undriven | check |
| 3 | mdio_status mirrors phy_status | check |
| 4 | mdio released while idle | check |

## 3. UVM 測試平台內容

UVM agent test（`mdio_func_test`：directed + constrained-random 流量，scoreboard 以 DUT 模型的參考模型逐筆比對，並比對 driver 與 monitor 的 transaction）在 Verilator 上以 `python3 tools/run_uvm_tests.py MDIO-UVM-VIP` 執行；agent 由 `tools/gen_uvm_agents.py` 依 `tools/uvm_agents/` 的協定 spec 產生。

| 項目 | 數量 | 名稱 |
|---|---|---|
| UVM tests | 2 | `mdio_base_test`, `mdio_func_test` |
| Sequences | 3 | `mdio_base_sequence`, `mdio_directed_sequence`, `mdio_transaction` |
| SVA（assert / cover property） | 3 / 2 | - |
| Covergroups / coverpoints | 1 / 3 | |

## 4. 充分度判定與缺口

判定：**✅ Sufficient**（23 個 check，mutation score 100%）。

無已知缺口。

