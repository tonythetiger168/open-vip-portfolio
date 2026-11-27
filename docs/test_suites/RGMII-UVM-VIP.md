# RGMII 測試套件（RGMII-UVM-VIP）

> 由 `tools/gen_test_suite_docs.py` 依 VIP 內容、`func_report.csv` 與 `mutation_report.csv` 自動產生，請勿手動修改。

## 1. 概要

| 項目 | 內容 |
|---|---|
| 類別 | Networking |
| 類型 | UVM VIP |
| 功能測試 | 1 個檔案，107 個 check，全部通過 |
| Mutation | 29/29 個 mutant 被偵測（100%） |
| 判定 | **✅ Sufficient**（107 個 check，mutation score 100%） |

## 2. 可執行的功能測試

執行：`python3 tools/run_func_tests.py RGMII-UVM-VIP`（Icarus Verilog 或 Verilator 5.054）。

### `tb/smoke_func_tb.sv`

結果：**PASS**（iverilog，107 checks）

模型合約與範圍（摘自測試檔頭）：

```text
Functional smoke testbench (RGMII DUT model)
```

| # | Check | 類型 |
|---|---|---|
| 1 | %s: status %0d (got %0d, len %0d/%0d, %0d results) | check |
| 2 | %s: status %0d (got %0d, %0d results) | check |
| 3 | reset values | check |
| 4 | length 46, unicast, untagged | check |
| 5 | broadcast class, type 0800 | check |
| 6 | multicast class | check |
| 7 | 802.1Q tag skipped for the type | check |
| 8 | FF-FF-FF-FF-FF-FE is multicast, not broadcast | check |
| 9 | filtered frame still reports its fields | check |
| 10 | runt reports no fields | check |
| 11 | type 0600 reported | check |
| 12 | pause quanta BEEF | check |
| 13 | pause to the station | check |
| 14 | opcode 2: not a PAUSE | check |
| 15 | opcode 0101: not a PAUSE | check |
| 16 | PAUSE to 01-80-C2-00-00-02 not honoured | check |
| 17 | type 8809: not a PAUSE | check |
| 18 | vtag: not a PAUSE | check |
| 19 | only two PAUSE frames honoured | check |
| 20 | length after a short preamble | check |
| 21 | no SFD: bytes after the first D5 in the data (%0d) | check |
| 22 | status 0 after reset | check |
| 23 | link up, 1000 Mb/s, full duplex | check |
| 24 | link up, 100 Mb/s, half duplex | check |
| 25 | link down, 10 Mb/s, full duplex | check |
| 26 | link up, 1000 Mb/s, half duplex | check |
| 27 | nibbles differing between edges: status not taken | check |
| 28 | RX_ER between frames: not status | check |
| 29 | status kept across a frame (preamble 55 is data) | check |
| 30 | preamble bytes with equal nibbles are not status | check |
| 31 | RX_ER byte with equal nibbles inside a frame is not status | check |
| 32 | false carrier: one pulse, no frame (%0d) | check |
| 33 | two false-carrier events (%0d) | check |
| 34 | 0E without RX_ER separates two events (%0d) | check |
| 35 | 0F, 1E, E0 with RX_ER, 0E without: no false carrier | check |
| 36 | 0E with RX_DV is data, not false carrier | check |
| 37 | two frames one byte apart | check |
| 38 | reset clears the status and drops the frame | check |
| 39 | no result for the dropped frame | check |

## 3. UVM 測試平台內容

UVM agent test（`rgmii_func_test`：directed + constrained-random 流量，scoreboard 以 DUT 模型的參考模型逐筆比對，並比對 driver 與 monitor 的 transaction）在 Verilator 上以 `python3 tools/run_uvm_tests.py RGMII-UVM-VIP` 執行；agent 由 `tools/gen_uvm_agents.py` 依 `tools/uvm_agents/` 的協定 spec 產生。

| 項目 | 數量 | 名稱 |
|---|---|---|
| UVM tests | 2 | `rgmii_base_test`, `rgmii_func_test` |
| Sequences | 3 | `rgmii_base_sequence`, `rgmii_directed_sequence`, `rgmii_transaction` |
| SVA（assert / cover property） | 8 / 5 | - |
| Covergroups / coverpoints | 1 / 11 | |

## 4. 充分度判定與缺口

判定：**✅ Sufficient**（107 個 check，mutation score 100%）。

無已知缺口。

