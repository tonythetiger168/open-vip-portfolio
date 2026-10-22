# 800G Ethernet 測試套件（ETH800G-VIP）

> 由 `tools/gen_test_suite_docs.py` 依 VIP 內容、`func_report.csv` 與 `mutation_report.csv` 自動產生，請勿手動修改。

## 1. 概要

| 項目 | 內容 |
|---|---|
| 類別 | Networking |
| 類型 | UVM VIP |
| 功能測試 | 2 個檔案，30 個 check，全部通過 |
| Mutation | 19/19 個 mutant 被偵測（100%） |
| 判定 | **✅ Sufficient**（30 個 check，mutation score 100%） |

## 2. 可執行的功能測試

執行：`python3 tools/run_func_tests.py ETH800G-VIP`（Icarus Verilog 或 Verilator 5.052）。

### `tb/func_eth800g_tb.sv`

結果：**PASS**（iverilog，16 checks）

模型合約與範圍（摘自測試檔頭）：

```text
func_eth800g_tb.sv -- self-checking functional test for the 800G Ethernet
packet-statistics model (eth800g_model, flattened by smoke/flatten.py).
Run: python3 tools/run_func_tests.py ETH800G-VIP

Model contract (from tb/top_tb.sv), 256-bit packet bus:
   Always ready. A beat counts on pkt_valid; a packet runs from SOP to EOP
   and each beat carries 32 - MTY bytes. At EOP the packet counter and the
   byte counter (bytes of the whole packet) advance, and err_oversize
   pulses for one clock when the packet exceeds 9600 bytes.
```

| # | Check | 類型 |
|---|---|---|
| 1 | counters and error clear in reset | check |
| 2 | always ready | check |
| 3 | 2-beat packet: 1 packet, 60 bytes | check |
| 4 | single full beat (SOP+EOP): 32 bytes | check |
| 5 | single 1-byte beat (MTY 31) | check |
| 6 | SOP/EOP without valid are ignored | check |
| 7 | 9600-byte packet is not oversize | check |
| 8 | short packet after a long one is not oversize | check |
| 9 | 9601-byte packet flags err_oversize at EOP | check |
| 10 | err_oversize is a one-clock pulse | check |
| 11 | oversize packet still counted | check |
| 12 | 60 random packets: packet and byte counts | check |
| 13 | 60 random packets: err_oversize exactly for those over 9600 bytes | check |
| 14 | SOP repeated inside a packet: no bytes lost | check |
| 15 | EOP without SOP is not counted as a packet | XFAIL（模型缺陷） |
| 16 | reset clears the counters | check |

### `tb/smoke_func_tb.sv`

結果：**PASS**（iverilog，14 checks）

| # | Check | 類型 |
|---|---|---|
| 1 | counters zero in reset | check |
| 2 | no err in reset | check |
| 3 | one packet counted | check |
| 4 | byte count with mty | check |
| 5 | second packet counted | check |
| 6 | byte count accumulates | check |
| 7 | no count when idle | check |
| 8 | oversize flagged | check |
| 9 | oversize packet still counted | check |
| 10 | err is a pulse | check |

## 3. UVM 測試平台內容

UVM 測試需商用模擬器（VCS / Xcelium / Questa）執行；開源流程只做 elaboration（L1a）。

| 項目 | 數量 | 名稱 |
|---|---|---|
| UVM tests | 1 | `eth800g_base_test` |
| Sequences | 2 | `eth800g_base_sequence`, `eth800g_transaction` |
| SVA（assert / cover property） | 4 / 2 | - |
| Covergroups / coverpoints | 1 / 5 | |

## 4. 充分度判定與缺口

判定：**✅ Sufficient**（30 個 check，mutation score 100%）。

DUT 模型缺陷（XFAIL check，修好模型後會變成 XPASS 提醒移除標記）：

- EOP without SOP is not counted as a packet

