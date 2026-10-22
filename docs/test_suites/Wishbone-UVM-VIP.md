# Wishbone 測試套件（Wishbone-UVM-VIP）

> 由 `tools/gen_test_suite_docs.py` 依 VIP 內容、`func_report.csv` 與 `mutation_report.csv` 自動產生，請勿手動修改。

## 1. 概要

| 項目 | 內容 |
|---|---|
| 類別 | Interconnect |
| 類型 | UVM VIP |
| 功能測試 | 2 個檔案，34 個 check，全部通過 |
| Mutation | 11/11 個 mutant 被偵測（100%） |
| 判定 | **✅ Sufficient**（34 個 check，mutation score 100%） |

## 2. 可執行的功能測試

執行：`python3 tools/run_func_tests.py Wishbone-UVM-VIP`（Icarus Verilog 或 Verilator 5.052）。

### `tb/func_wishbone_tb.sv`

結果：**PASS**（iverilog，13 checks）

模型合約與範圍（摘自測試檔頭）：

```text
func_wishbone_tb.sv -- Wishbone B4 classic-cycle functional test for the
register model (wishbone_model, flattened by smoke/flatten.py);
complements smoke_func_tb.sv.
Run: python3 tools/run_func_tests.py Wishbone-UVM-VIP

Model contract (from tb/top_tb.sv): 16 x 32-bit registers (ADR[5:2]),
cleared by reset; ACK one clock after CYC && STB (one ACK per cycle,
registered); a write is stored once per ACK; DAT_O carries the read data
(or echoes the write data) with ACK. Checked against a reference with
400 random classic cycles, STB held over consecutive cycles, and cycles
where only one of CYC / STB is high.
```

| # | Check | 類型 |
|---|---|---|
| 1 | reset: ACK low, DAT_O 0 | check |
| 2 | all 16 registers read 0 after reset | check |
| 3 | write: ACK in the next clock, DAT_O echoes the write data | check |
| 4 | read: ACK in the next clock with the register value | check |
| 5 | registers decode ADR[5:2] only | check |
| 6 | no ACK unless both CYC and STB are high | check |
| 7 | no write unless both CYC and STB are high | check |
| 8 | consecutive cycles with STB held: each ACK completes exactly one write | check |
| 9 | 400 random cycles match the reference registers, ACK latency 1 | check |
| 10 | ACK only during a cycle | check |
| 11 | (ACK pending before reset) | check |
| 12 | reset drops ACK and DAT_O | check |
| 13 | reset clears all registers | check |

### `tb/smoke_func_tb.sv`

結果：**PASS**（iverilog，21 checks）

| # | Check | 類型 |
|---|---|---|
| 1 | ack reset low | check |
| 2 | write acknowledged | check |
| 3 | ack deasserts after cycle | check |
| 4 | read acknowledged | check |
| 5 | read data integrity | check |
| 6 | no ack when idle | check |

## 3. UVM 測試平台內容

UVM 測試需商用模擬器（VCS / Xcelium / Questa）執行；開源流程只做 elaboration（L1a）。

| 項目 | 數量 | 名稱 |
|---|---|---|
| UVM tests | 1 | `wishbone_base_test` |
| Sequences | 2 | `wishbone_base_sequence`, `wishbone_transaction` |
| SVA（assert / cover property） | 4 / 2 | - |
| Covergroups / coverpoints | 1 / 5 | |

## 4. 充分度判定與缺口

判定：**✅ Sufficient**（34 個 check，mutation score 100%）。

無已知缺口。

