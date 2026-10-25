# MDIO 測試套件（MDIO-UVM-VIP）

> 由 `tools/gen_test_suite_docs.py` 依 VIP 內容、`func_report.csv` 與 `mutation_report.csv` 自動產生，請勿手動修改。

## 1. 概要

| 項目 | 內容 |
|---|---|
| 類別 | Networking |
| 類型 | UVM VIP |
| 功能測試 | 2 個檔案，19 個 check，全部通過 |
| Mutation | 4/4 個 mutant 被偵測（100%） |
| 判定 | **✅ Sufficient**（19 個 check，mutation score 100%） |

## 2. 可執行的功能測試

執行：`python3 tools/run_func_tests.py MDIO-UVM-VIP`（Icarus Verilog 或 Verilator 5.052）。

### `tb/func_mdio_tb.sv`

結果：**PASS**（iverilog，8 checks）

模型合約與範圍（摘自測試檔頭）：

```text
func_mdio_tb.sv -- IEEE 802.3 Clause 22 functional test for the MDIO PHY
model (mdio_model, flattened by smoke/flatten.py); complements
smoke_func_tb.sv (status mirror, idle bus).
Run: python3 tools/run_func_tests.py MDIO-UVM-VIP

Model contract (from tb/top_tb.sv): mdio_status mirrors phy_status one
clock later; the PHY (address 5) answers a read with phy_status on MDIO.
Frames here follow Clause 22: 32-bit preamble of ones, ST 01, OP 10
(read) / 01 (write), PHYAD, REGAD, turnaround, 16 data bits, MSB first,
MDIO sampled by the PHY on the MDC rising edge (MDC = 8 clocks).

Model defect (XFAIL): the model shifts MDIO in on every clock while MDC
is low (not on MDC edges) and only starts a response when the bits 16..24
clocks back read 0_1100_0101 at a fixed counter phase, which a
preamble-led frame never produces, so a read is never answered. The VIP
driver itself only toggles MDC and phy_status (no management frames).
```

| # | Check | 類型 |
|---|---|---|
| 1 | reset: status 0, MDIO released (pulled up) | check |
| 2 | mdio_status mirrors each phy_status bit | check |
| 3 | mdio_status updates on the next clock edge | check |
| 4 | write frame: PHY never drives MDIO | check |
| 5 | read of another PHY address: no response | check |
| 6 | read of PHY 5: TA 0 then phy_status, MSB first | XFAIL（模型缺陷） |
| 7 | MDIO released after the read frame | check |
| 8 | reset clears status and the response state | check |

### `tb/smoke_func_tb.sv`

結果：**PASS**（iverilog，11 checks）

| # | Check | 類型 |
|---|---|---|
| 1 | mdio_status reset to zero | check |
| 2 | mdio pulled high (tri1) when undriven | check |
| 3 | mdio_status mirrors phy_status | check |
| 4 | mdio released while idle | check |

## 3. UVM 測試平台內容

UVM 測試需商用模擬器（VCS / Xcelium / Questa）執行；開源流程只做 elaboration（L1a）。

| 項目 | 數量 | 名稱 |
|---|---|---|
| UVM tests | 1 | `mdio_base_test` |
| Sequences | 2 | `mdio_base_sequence`, `mdio_transaction` |
| SVA（assert / cover property） | 3 / 2 | - |
| Covergroups / coverpoints | 1 / 2 | |

## 4. 充分度判定與缺口

判定：**✅ Sufficient**（19 個 check，mutation score 100%）。

DUT 模型缺陷（XFAIL check，修好模型後會變成 XPASS 提醒移除標記）：

- read of PHY 5: TA 0 then phy_status, MSB first

