# CAN-FD 測試套件（CAN_FD-UVM-VIP）

> 由 `tools/gen_test_suite_docs.py` 依 VIP 內容、`func_report.csv` 與 `mutation_report.csv` 自動產生，請勿手動修改。

## 1. 概要

| 項目 | 內容 |
|---|---|
| 類別 | Automotive |
| 類型 | UVM VIP |
| 功能測試 | 1 個檔案，53 個 check，全部通過 |
| Mutation | 27/27 個 mutant 被偵測（100%） |
| 判定 | **✅ Sufficient**（53 個 check，mutation score 100%） |

## 2. 可執行的功能測試

執行：`python3 tools/run_func_tests.py CAN_FD-UVM-VIP`（Icarus Verilog 或 Verilator 5.054）。

### `tb/smoke_func_tb.sv`

結果：**PASS**（iverilog，53 checks）

模型合約與範圍（摘自測試檔頭）：

```text
Functional smoke testbench (CAN-FD DUT model)
```

| # | Check | 類型 |
|---|---|---|
| 1 | tx recessive in reset | check |
| 2 | no reports in reset | check |
| 3 | frame outputs clear in reset | check |
| 4 | frame before bus integration ignored | check |
| 5 | classical base frame ACKed and reported | check |
| 6 | classical base fields | check |
| 7 | data byte sum | check |
| 8 | one dominant bit (ACK) for a good frame (%0d) | check |
| 9 | rx_ok after the sixth EOF bit (%0d) | check |
| 10 | classical extended remote frame | check |
| 11 | classical DLC 12 = 8 bytes | check |
| 12 | FD frame, 12 bytes, CRC17 | check |
| 13 | FD extended frame with BRS ACKed | check |
| 14 | BRS / ESI / 64 bytes reported | check |
| 15 | ACK lasts one nominal bit (%0d clocks) | check |
| 16 | rx_ok at the nominal bit time (%0d) | check |
| 17 | 16 bytes at 3/2 clocks (CRC17) | check |
| 18 | 20 bytes at 3/2 clocks (CRC21) | check |
| 19 | all 16 FD DLCs received (%0d) | check |
| 20 | 40 classical frames received (%0d) | check |
| 21 | bit time 0 treated as one clock | check |
| 22 | stuff error flagged, no ACK | check |
| 23 | six-bit error flag (%0d) | check |
| 24 | receive error counter +1 | check |
| 25 | FD CRC error flagged, no ACK | check |
| 26 | CRC error flag after the ACK delimiter (%0d) | check |
| 27 | CRC error flag six bits | check |
| 28 | SOF ignored 10 recessive bits after an error | check |
| 29 | SOF accepted 11 recessive bits after an error | check |
| 30 | FD CRC21 error flagged | check |
| 31 | stuff count error flagged as CRC error | check |
| 32 | fixed stuff bit error | check |
| 33 | dominant CRC delimiter: form error | check |
| 34 | classical CRC15 error | check |
| 35 | found a classical frame ending in a stuff bit | check |
| 36 | trailing CRC15 stuff bit accepted | check |
| 37 | bad trailing CRC15 stuff bit: stuff error | check |
| 38 | one-clock glitch ignored | check |
| 39 | frame after a glitch received | check |
| 40 | dominant ACK delimiter: form error after the ACK | check |
| 41 | dominant sixth EOF bit: form error | check |
| 42 | dominant last EOF bit ignored, counter -1 | check |
| 43 | res recessive: protocol exception, no flag | check |
| 44 | frame after a protocol exception received | check |
| 45 | res recessive without protocol exception: form error | check |
| 46 | filtered frame ACKed, not reported | check |
| 47 | matching frame reported | check |
| 48 | error passive at 128 and above | check |
| 49 | good frame sets an error-passive counter to 127 | check |
| 50 | counter saturates at 255 | check |
| 51 | reset clears the error counter | check |
| 52 | SOF after 10 recessive bits from reset ignored | check |
| 53 | SOF after 11 recessive bits from reset received | check |

## 3. UVM 測試平台內容

UVM agent test（`can_fd_func_test`：directed + constrained-random 流量，scoreboard 以 DUT 模型的參考模型逐筆比對，並比對 driver 與 monitor 的 transaction）在 Verilator 上以 `python3 tools/run_uvm_tests.py CAN_FD-UVM-VIP` 執行；agent 由 `tools/gen_uvm_agents.py` 依 `tools/uvm_agents/` 的協定 spec 產生。

| 項目 | 數量 | 名稱 |
|---|---|---|
| UVM tests | 2 | `can_fd_base_test`, `can_fd_func_test` |
| Sequences | 3 | `can_fd_base_sequence`, `can_fd_directed_sequence`, `can_fd_transaction` |
| SVA（assert / cover property） | 6 / 3 | - |
| Covergroups / coverpoints | 1 / 11 | |

## 4. 充分度判定與缺口

判定：**✅ Sufficient**（53 個 check，mutation score 100%）。

無已知缺口。

