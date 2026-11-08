# GMII / RGMII Ethernet PHY link partner 測試套件（GMII_PHY-UVM-VIP）

> 由 `tools/gen_test_suite_docs.py` 依 VIP 內容、`func_report.csv` 與 `mutation_report.csv` 自動產生，請勿手動修改。

## 1. 概要

| 項目 | 內容 |
|---|---|
| 類別 | Networking |
| 類型 | UVM VIP |
| 功能測試 | 1 個檔案，26 個 check，全部通過 |
| Mutation | 29/29 個 mutant 被偵測（100%） |
| 判定 | **✅ Sufficient**（26 個 check，mutation score 100%） |

## 2. 可執行的功能測試

執行：`python3 tools/run_func_tests.py GMII_PHY-UVM-VIP`（Icarus Verilog 或 Verilator 5.052）。

### `tb/smoke_func_tb.sv`

結果：**PASS**（iverilog，26 checks）

模型合約與範圍（摘自測試檔頭）：

```text
Functional smoke testbench (GPHY DUT model)
```

| # | Check | 類型 |
|---|---|---|
| 1 | nothing out in reset | check |
| 2 | quiet after reset | check |
| 3 | frame to the MAC: delivered without FCS, sent back with swapped addresses | check |
| 4 | broadcast, 64 bytes: sent back without padding | check |
| 5 | other unicast: dropped silently | check |
| 6 | multicast: dropped | check |
| 7 | FCS error: crc_err, not sent back | check |
| 8 | grx_er: phy_err | check |
| 9 | 38-byte runt: len_err | check |
| 10 | 1519 bytes: len_err | check |
| 11 | 1518 bytes: good | check |
| 12 | VLAN-tagged 1522 bytes: good | check |
| 13 | length field 20: 20 data bytes sent back, padded to 60 | check |
| 14 | length field longer than the frame: all of it | check |
| 15 | type 0x0600 is not a length | check |
| 16 | PAUSE quanta 2: pause status, transmitter held | check |
| 17 | frame during the pause is sent back after it | check |
| 18 | pause lasted at least 128 byte times | check |
| 19 | MAC control opcode 2: not a PAUSE | check |
| 20 | PAUSE with an FCS error is not honoured | check |
| 21 | bad preamble byte: fragment | check |
| 22 | SFD without preamble | check |
| 23 | 15-byte preamble | check |
| 24 | frame cut after 3 bytes: fragment | check |
| 25 | 6-byte frame: delivered with crc and len errors | check |
| 26 | preamble only: fragment | check |

## 3. UVM 測試平台內容

UVM agent test（`gphy_func_test`：directed + constrained-random 流量，scoreboard 以 DUT 模型的參考模型逐筆比對，並比對 driver 與 monitor 的 transaction）在 Verilator 上以 `python3 tools/run_uvm_tests.py GMII_PHY-UVM-VIP` 執行；agent 由 `tools/gen_uvm_agents.py` 依 `tools/uvm_agents/` 的協定 spec 產生。

| 項目 | 數量 | 名稱 |
|---|---|---|
| UVM tests | 2 | `gphy_base_test`, `gphy_func_test` |
| Sequences | 3 | `gphy_base_sequence`, `gphy_directed_sequence`, `gphy_transaction` |
| SVA（assert / cover property） | 5 / 2 | - |
| Covergroups / coverpoints | 1 / 3 | |

## 4. 充分度判定與缺口

判定：**✅ Sufficient**（26 個 check，mutation score 100%）。

無已知缺口。

