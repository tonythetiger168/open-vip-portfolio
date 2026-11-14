# DVB CI / CI+ CAM (EN 50221, PC Card) 測試套件（CI_CAM-UVM-VIP）

> 由 `tools/gen_test_suite_docs.py` 依 VIP 內容、`func_report.csv` 與 `mutation_report.csv` 自動產生，請勿手動修改。

## 1. 概要

| 項目 | 內容 |
|---|---|
| 類別 | Security |
| 類型 | UVM VIP |
| 功能測試 | 1 個檔案，83 個 check，全部通過 |
| Mutation | 30/30 個 mutant 被偵測（100%） |
| 判定 | **✅ Sufficient**（83 個 check，mutation score 100%） |

## 2. 可執行的功能測試

執行：`python3 tools/run_func_tests.py CI_CAM-UVM-VIP`（Icarus Verilog 或 Verilator 5.054）。

### `tb/smoke_func_tb.sv`

結果：**PASS**（verilator，83 checks）

模型合約與範圍（摘自測試檔頭）：

```text
Functional smoke testbench (CAM DUT model)
```

| # | Check | 類型 |
|---|---|---|
| 1 | card detect low | check |
| 2 | VCC off: outputs idle | check |
| 3 | VCC off: no data | check |
| 4 | READY low in RESET | check |
| 5 | not ready: no data | check |
| 6 | READY after RESET | check |
| 7 | READY 20 clocks after RESET | check |
| 8 | CIS bytes at even addresses | check |
| 9 | odd attribute address FF | check |
| 10 | past the CIS FF | check |
| 11 | top of attribute memory FF | check |
| 12 | common memory FF | check |
| 13 | WAIT# low for 2 clocks of the strobe | check |
| 14 | I/O read in memory mode: not driven | check |
| 15 | COR 00 after RESET | check |
| 16 | CIS not writable | check |
| 17 | common-memory write is not the COR | check |
| 18 | COR read back | check |
| 19 | COR 01: still memory mode | check |
| 20 | memory mode: READY on IREQ# | check |
| 21 | a write next to the COR is not the COR | check |
| 22 | COR 4F: I/O mode, FR | check |
| 23 | COR 0E leaves I/O mode | check |
| 24 | COR 0F: I/O mode | check |
| 25 | attribute read in I/O mode | check |
| 26 | RS: FR low | check |
| 27 | FR still low just after RS | check |
| 28 | FR back after RS_DLY | check |
| 29 | SR: DA, FR low | check |
| 30 | size 2 | check |
| 31 | size MS 0 | check |
| 32 | buffer size MS | check |
| 33 | one byte left, FR low while a reply waits | check |
| 34 | buffer size LS 64 | check |
| 35 | read out: DA clear, FR | check |
| 36 | empty DATA read: RE | check |
| 37 | RS clears RE | check |
| 38 | processing: FR low, no DA | check |
| 39 | reply ready: DA | check |
| 40 | reply: link header kept, body XOR 5A | check |
| 41 | reply read: FR | check |
| 42 | reply PROC clocks after HC is cleared | check |
| 43 | 1-byte message | check |
| 44 | 64-byte message | check |
| 45 | 65 bytes: WE | check |
| 46 | and no reply | check |
| 47 | RS clears WE | check |
| 48 | size mismatch: WE, no reply | check |
| 49 | DATA write without HC: WE | check |
| 50 | COMMAND 00 opens no message | check |
| 51 | HC written twice: one message | check |
| 52 | message while FR low (reply waiting): WE | check |
| 53 | only the first is answered | check |
| 54 | SIZE shows the reply | check |
| 55 | no buffer size after a reply | check |
| 56 | SIZE_MS: 258 does not match 2 | check |
| 57 | FRIE with FR: IREQ# low | check |
| 58 | DAIE without DA: IREQ# high | check |
| 59 | DAIE with DA: IREQ# low | check |
| 60 | both | check |
| 61 | disabled | check |
| 62 | the reply of the IREQ message | check |
| 63 | clear packet passes unchanged | check |
| 64 | scrambled packet with a gap: SC cleared, payload descrambled | check |
| 65 | the stream is registered | check |
| 66 | and comes out after the clock | check |
| 67 | MIVAL low: data 0 | check |
| 68 | RESET: no data | check |
| 69 | after RESET: memory mode | check |
| 70 | COR cleared | check |
| 71 | I/O mode again, no reply left | check |
| 72 | DATA empty | check |
| 73 | a message right after RESET | check |
| 74 | COMMAND written from the strobe's address (FRIE) | check |
| 75 | and no DATA write | check |
| 76 | VCC off: no stream, no READY | check |
| 77 | power cycle: memory mode | check |
| 78 | SR after power: buffer size | check |
| 79 | COR cleared by power | check |
| 80 | long cycle | check |
| 81 | short strobe: WAIT# stretches it | check |
| 82 | WAIT# 2 clocks | check |

## 3. UVM 測試平台內容

UVM agent test（`cam_func_test`：directed + constrained-random 流量，scoreboard 以 DUT 模型的參考模型逐筆比對，並比對 driver 與 monitor 的 transaction）在 Verilator 上以 `python3 tools/run_uvm_tests.py CI_CAM-UVM-VIP` 執行；agent 由 `tools/gen_uvm_agents.py` 依 `tools/uvm_agents/` 的協定 spec 產生。

| 項目 | 數量 | 名稱 |
|---|---|---|
| UVM tests | 2 | `cam_base_test`, `cam_func_test` |
| Sequences | 3 | `cam_base_sequence`, `cam_directed_sequence`, `cam_transaction` |
| SVA（assert / cover property） | 3 / 1 | - |
| Covergroups / coverpoints | 1 / 2 | |

## 4. 充分度判定與缺口

判定：**✅ Sufficient**（83 個 check，mutation score 100%）。

無已知缺口。

