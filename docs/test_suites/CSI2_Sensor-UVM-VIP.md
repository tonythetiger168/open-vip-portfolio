# CSI-2 camera sensor transmitter 測試套件（CSI2_Sensor-UVM-VIP）

> 由 `tools/gen_test_suite_docs.py` 依 VIP 內容、`func_report.csv` 與 `mutation_report.csv` 自動產生，請勿手動修改。

## 1. 概要

| 項目 | 內容 |
|---|---|
| 類別 | MIPI |
| 類型 | UVM VIP |
| 功能測試 | 1 個檔案，25 個 check，全部通過 |
| Mutation | 28/28 個 mutant 被偵測（100%） |
| 判定 | **✅ Sufficient**（25 個 check，mutation score 100%） |

## 2. 可執行的功能測試

執行：`python3 tools/run_func_tests.py CSI2_Sensor-UVM-VIP`（Icarus Verilog 或 Verilator 5.052）。

### `tb/smoke_func_tb.sv`

結果：**PASS**（iverilog，25 checks）

模型合約與範圍（摘自測試檔頭）：

```text
Functional smoke testbench (CSIS DUT model)
```

| # | Check | 類型 |
|---|---|---|
| 1 | nothing out in reset | check |
| 2 | a burst of HS-zeros only: no report | check |
| 3 | FS with frame number 7 | check |
| 4 | RAW8 line of 16 after 13 lead-in zeros | check |
| 5 | YUV422 on VC 2, no lead-in or trailer | check |
| 6 | long packet with WC 0 | check |
| 7 | header bit error in each of the 24 positions: corrected, line counted | check |
| 8 | ECC bit errors: corrected | check |
| 9 | ECC bits 7:6 are ignored | check |
| 10 | two-bit header error: dropped | check |
| 11 | payload bit error: CRC error, line not counted | check |
| 12 | CRC bit error | check |
| 13 | burst cut in the header | check |
| 14 | burst cut right after the ECC byte | check |
| 15 | corrected header, burst cut in the payload | check |
| 16 | burst cut in the CRC | check |
| 17 | burst cut after the CRC low byte | check |
| 18 | LS + line + LE in one burst | check |
| 19 | junk byte after a packet: rest of the burst ignored | check |
| 20 | trailer of zeros: no further report | check |
| 21 | line of 300 bytes | check |
| 22 | FE | check |
| 23 | FS on VC 1 after a one-clock gap: frame 2, line count cleared | check |
| 24 | packet after a dropped header in the same burst is not taken | check |
| 25 | no payload byte in the clock of a report | check |

## 3. UVM 測試平台內容

UVM agent test（`csis_func_test`：directed + constrained-random 流量，scoreboard 以 DUT 模型的參考模型逐筆比對，並比對 driver 與 monitor 的 transaction）在 Verilator 上以 `python3 tools/run_uvm_tests.py CSI2_Sensor-UVM-VIP` 執行；agent 由 `tools/gen_uvm_agents.py` 依 `tools/uvm_agents/` 的協定 spec 產生。

| 項目 | 數量 | 名稱 |
|---|---|---|
| UVM tests | 2 | `csis_base_test`, `csis_func_test` |
| Sequences | 3 | `csis_base_sequence`, `csis_directed_sequence`, `csis_transaction` |
| SVA（assert / cover property） | 5 / 2 | - |
| Covergroups / coverpoints | 1 / 4 | |

## 4. 充分度判定與缺口

判定：**✅ Sufficient**（25 個 check，mutation score 100%）。

無已知缺口。

