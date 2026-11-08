# HDMI CEC 測試套件（HDMI_CEC-UVM-VIP）

> 由 `tools/gen_test_suite_docs.py` 依 VIP 內容、`func_report.csv` 與 `mutation_report.csv` 自動產生，請勿手動修改。

## 1. 概要

| 項目 | 內容 |
|---|---|
| 類別 | Video |
| 類型 | UVM VIP |
| 功能測試 | 1 個檔案，20 個 check，全部通過 |
| Mutation | 26/26 個 mutant 被偵測（100%） |
| 判定 | **✅ Sufficient**（20 個 check，mutation score 100%） |

## 2. 可執行的功能測試

執行：`python3 tools/run_func_tests.py HDMI_CEC-UVM-VIP`（Icarus Verilog 或 Verilator 5.052）。

### `tb/smoke_func_tb.sv`

結果：**PASS**（iverilog，20 checks）

模型合約與範圍（摘自測試檔頭）：

```text
Functional smoke testbench (CEC DUT model)
```

| # | Check | 類型 |
|---|---|---|
| 1 | nothing out in reset | check |
| 2 | polling 4 -> 0: ACK, no data | check |
| 3 | Standby: header and opcode ACKed | check |
| 4 | Active Source 3 -> 0 with two operands | check |
| 5 | 15 data blocks | check |
| 6 | broadcast: accepted without pulling ACK low | check |
| 7 | polling another device: NACK | check |
| 8 | data bit low 1.0 ms: error notification | check |
| 9 | bit period 1.8 ms: error notification | check |
| 10 | bit period 2.9 ms: overrun, no notification | check |
| 11 | no EOM: the frame never ends | check |
| 12 | start low 3.0 ms | check |
| 13 | start period 5.0 ms | check |
| 14 | every window edge accepted | check |
| 15 | frame after the faults | check |
| 16 | ACK pulse is 1.5 ms (%0d clocks) | check |
| 17 | start low 3.9 ms accepted | check |
| 18 | start low 3.95 ms rejected | check |
| 19 | start period 4.7 ms accepted | check |
| 20 | start period 4.75 ms rejected | check |

## 3. UVM 測試平台內容

UVM agent test（`cec_func_test`：directed + constrained-random 流量，scoreboard 以 DUT 模型的參考模型逐筆比對，並比對 driver 與 monitor 的 transaction）在 Verilator 上以 `python3 tools/run_uvm_tests.py HDMI_CEC-UVM-VIP` 執行；agent 由 `tools/gen_uvm_agents.py` 依 `tools/uvm_agents/` 的協定 spec 產生。

| 項目 | 數量 | 名稱 |
|---|---|---|
| UVM tests | 2 | `cec_base_test`, `cec_func_test` |
| Sequences | 3 | `cec_base_sequence`, `cec_directed_sequence`, `cec_transaction` |
| SVA（assert / cover property） | 4 / 2 | - |
| Covergroups / coverpoints | 1 / 4 | |

## 4. 充分度判定與缺口

判定：**✅ Sufficient**（20 個 check，mutation score 100%）。

無已知缺口。

