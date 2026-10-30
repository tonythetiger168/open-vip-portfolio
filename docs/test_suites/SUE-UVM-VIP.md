# SUE / ESUN scale-up Ethernet transport 測試套件（SUE-UVM-VIP）

> 由 `tools/gen_test_suite_docs.py` 依 VIP 內容、`func_report.csv` 與 `mutation_report.csv` 自動產生，請勿手動修改。

## 1. 概要

| 項目 | 內容 |
|---|---|
| 類別 | Networking |
| 類型 | UVM VIP |
| 功能測試 | 1 個檔案，30 個 check，全部通過 |
| Mutation | 43/43 個 mutant 被偵測（100%） |
| 判定 | **✅ Sufficient**（30 個 check，mutation score 100%） |

## 2. 可執行的功能測試

執行：`python3 tools/run_func_tests.py SUE-UVM-VIP`（Icarus Verilog 或 Verilator 5.052）。

### `tb/smoke_func_tb.sv`

結果：**PASS**（iverilog，30 checks）

模型合約與範圍（摘自測試檔頭）：

```text
Functional smoke testbench (SUE DUT model)
```

| # | Check | 類型 |
|---|---|---|
| 1 | nothing out in reset | check |
| 2 | no report without a frame | check |
| 3 | VC 0 PSN 0, 1 byte: ACK 0, delivered | check |
| 4 | VC 0 PSN 1, 64 bytes | check |
| 5 | VC 3 has its own PSN | check |
| 6 | VC 2 PSN 0 | check |
| 7 | VC 1 PSN 0 | check |
| 8 | VC 0 PSN 1 again: duplicate, ACK 1, not delivered | check |
| 9 | VC 0 PSN 0: duplicate, ACK of the last (1) | check |
| 10 | VC 0 PSN 3 where 2 is due: NACK 2, dropped | check |
| 11 | retransmitted PSN 2: delivered | check |
| 12 | then PSN 3 | check |
| 13 | PSN 0x8003 (32767 ahead): gap, NACK 4 | check |
| 14 | PSN 0x8004 (32768 behind): duplicate, ACK 3 | check |
| 15 | payload bit flipped: CRC NACK of VC 1's 1 | check |
| 16 | CRC bit flipped | check |
| 17 | XPU 0x0043: dropped | check |
| 18 | version 2: dropped | check |
| 19 | opcode 1: dropped | check |
| 20 | EtherType 0x0800: dropped | check |
| 21 | length field 11 for 10 bytes: dropped | check |
| 22 | length field 9 for 10 bytes: dropped | check |
| 23 | empty payload: dropped | check |
| 24 | 65-byte payload: dropped | check |
| 25 | 25-byte runt: dropped | check |
| 26 | VC 2 PSN 1 after the drops | check |
| 27 | VC 1 PSN 1 after its CRC NACKs | check |
| 28 | VC 3 untouched | check |
| 29 | VC 3 PSN 6..69 in order | check |
| 30 | one last-byte strobe per delivered frame (%0d) | check |

## 3. UVM 測試平台內容

UVM agent test（`sue_func_test`：directed + constrained-random 流量，scoreboard 以 DUT 模型的參考模型逐筆比對，並比對 driver 與 monitor 的 transaction）在 Verilator 上以 `python3 tools/run_uvm_tests.py SUE-UVM-VIP` 執行；agent 由 `tools/gen_uvm_agents.py` 依 `tools/uvm_agents/` 的協定 spec 產生。

| 項目 | 數量 | 名稱 |
|---|---|---|
| UVM tests | 2 | `sue_base_test`, `sue_func_test` |
| Sequences | 3 | `sue_base_sequence`, `sue_directed_sequence`, `sue_transaction` |
| SVA（assert / cover property） | 3 / 2 | - |
| Covergroups / coverpoints | 1 / 3 | |

## 4. 充分度判定與缺口

判定：**✅ Sufficient**（30 個 check，mutation score 100%）。

無已知缺口。

