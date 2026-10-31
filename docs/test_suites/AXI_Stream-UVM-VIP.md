# AXI-Stream 測試套件（AXI_Stream-UVM-VIP）

> 由 `tools/gen_test_suite_docs.py` 依 VIP 內容、`func_report.csv` 與 `mutation_report.csv` 自動產生，請勿手動修改。

## 1. 概要

| 項目 | 內容 |
|---|---|
| 類別 | AMBA |
| 類型 | UVM VIP |
| 功能測試 | 1 個檔案，17 個 check，全部通過 |
| Mutation | 22/22 個 mutant 被偵測（100%） |
| 判定 | **✅ Sufficient**（17 個 check，mutation score 100%） |

## 2. 可執行的功能測試

執行：`python3 tools/run_func_tests.py AXI_Stream-UVM-VIP`（Icarus Verilog 或 Verilator 5.052）。

### `tb/smoke_func_tb.sv`

結果：**PASS**（iverilog，17 checks）

模型合約與範圍（摘自測試檔頭）：

```text
Functional smoke testbench (AXI4-Stream DUT model)
```

| # | Check | 類型 |
|---|---|---|
| 1 | no report in reset | check |
| 2 | one report per packet | check |
| 3 | CRC-32 of 123456789 = 0xCBF43926, 9 bytes | check |
| 4 | TID / TDEST reported, no error | check |
| 5 | null bytes are dropped (same CRC, same count) | check |
| 6 | TID / TDEST of the second packet | check |
| 7 | three position bytes counted, CRC unchanged | check |
| 8 | single byte 'a': CRC 0xE8B7BE43 | check |
| 9 | position byte only: no data, CRC of nothing is 0 | check |
| 10 | TKEEP 0 / TSTRB 1 flagged, data bytes still counted | check |
| 11 | TID change inside a packet flagged; the first TID reported | check |
| 12 | TDEST change inside a packet flagged; the first TDEST reported | check |
| 13 | error state cleared for the next packet; CRC of 1234 | check |
| 14 | eight back-to-back packets, eight reports | check |
| 15 | last of them reported correctly | check |
| 16 | 255 data bytes counted | check |
| 17 | TREADY low for %0d clocks of a held transfer | check |

## 3. UVM 測試平台內容

UVM agent test（`axi_stream_func_test`：directed + constrained-random 流量，scoreboard 以 DUT 模型的參考模型逐筆比對，並比對 driver 與 monitor 的 transaction）在 Verilator 上以 `python3 tools/run_uvm_tests.py AXI_Stream-UVM-VIP` 執行；agent 由 `tools/gen_uvm_agents.py` 依 `tools/uvm_agents/` 的協定 spec 產生。

| 項目 | 數量 | 名稱 |
|---|---|---|
| UVM tests | 2 | `axi_stream_base_test`, `axi_stream_func_test` |
| Sequences | 3 | `axi_stream_base_sequence`, `axi_stream_directed_sequence`, `axi_stream_transaction` |
| SVA（assert / cover property） | 6 / 4 | - |
| Covergroups / coverpoints | 1 / 5 | |

## 4. 充分度判定與缺口

判定：**✅ Sufficient**（17 個 check，mutation score 100%）。

無已知缺口。

