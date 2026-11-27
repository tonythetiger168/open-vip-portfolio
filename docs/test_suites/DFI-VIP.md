# DFI 5.0 (MC-PHY Interface) 測試套件（DFI-VIP）

> 由 `tools/gen_test_suite_docs.py` 依 VIP 內容、`func_report.csv` 與 `mutation_report.csv` 自動產生，請勿手動修改。

## 1. 概要

| 項目 | 內容 |
|---|---|
| 類別 | Memory |
| 類型 | UVM VIP |
| 功能測試 | 1 個檔案，80 個 check，全部通過 |
| Mutation | 25/25 個 mutant 被偵測（100%） |
| 判定 | **✅ Sufficient**（80 個 check，mutation score 100%） |

## 2. 可執行的功能測試

執行：`python3 tools/run_func_tests.py DFI-VIP`（Icarus Verilog 或 Verilator 5.054）。

### `tb/smoke_func_tb.sv`

結果：**PASS**（iverilog，80 checks）

模型合約與範圍（摘自測試檔頭）：

```text
Functional smoke testbench (DFI DUT model)
```

| # | Check | 類型 |
|---|---|---|
| 1 | outputs clear in reset | check |
| 2 | command before init: busy error (%02h) | check |
| 3 | init complete 10 cycles after init start (%0d) | check |
| 4 | frequency taken at init | check |
| 5 | legal ACT / WR / RD: no error (%02h) | check |
| 6 | read returns the written burst | check |
| 7 | first read beat 8 cycles after RD (%0d) | check |
| 8 | unwritten columns read the default pattern | check |
| 9 | byte masks keep masked bytes | check |
| 10 | burst wraps inside the 64-column row | check |
| 11 | row 8 reads the row-0 location | check |
| 12 | RD 3 cycles after ACT: tRCD error, read enable error (%02h) | check |
| 13 | RD 4 cycles after ACT accepted | check |
| 14 | PRE 7 cycles after ACT: tRAS error (%02h) | check |
| 15 | PRE 8 cycles after ACT accepted | check |
| 16 | ACT 3 cycles after PRE: tRP error (%02h) | check |
| 17 | ACT 5 cycles after PRE accepted | check |
| 18 | ACT 4 cycles after PRE accepted | check |
| 19 | NOP / MRS / ZQ commands ignored, bank still open | check |
| 20 | ACT to an open bank: bank error | check |
| 21 | RD to a closed bank: bank error, no data (%02h) | check |
| 22 | REF with banks open: bank error | check |
| 23 | PRE of a closed bank is a no-op | check |
| 24 | PREA with a bank inside tRAS: timing error | check |
| 25 | rejected PREA closes nothing | check |
| 26 | PREA closes all banks | check |
| 27 | bank closed by PREA | check |
| 28 | REF with all banks closed | check |
| 29 | ACT 11 cycles after REF: tRFC error | check |
| 30 | ACT 12 cycles after REF accepted | check |
| 31 | REF 3 cycles after PRE: tRP error (%02h) | check |
| 32 | REF 5 cycles after PRE accepted | check |
| 33 | REF 10 cycles after REF: tRFC error | check |
| 34 | REF 12 cycles after REF accepted | check |
| 35 | RD with auto-precharge | check |
| 36 | auto-precharge closed the bank | check |
| 37 | WR with auto-precharge, ACT after the burst and tRP | check |
| 38 | ACT right after WR with auto-precharge: tRP error (%02h) | check |
| 39 | ACT 7 cycles after RD with auto-precharge: tRP error (%02h) | check |
| 40 | ACT 8 cycles after RD with auto-precharge accepted (%02h) | check |
| 41 | write enable one cycle early: wrdata error | check |
| 42 | early write: beats inside the window are written | check |
| 43 | write enable one cycle late | check |
| 44 | write burst one beat short | check |
| 45 | write burst one beat long | check |
| 46 | read enable one cycle early: rddata error, 3 beats (%0d) | check |
| 47 | read enable one cycle late: 3 beats | check |
| 48 | read enable one beat long: 4 beats | check |
| 49 | WR to a closed bank: bank and wrdata errors | check |
| 50 | ACT with cke low ignored | check |
| 51 | ctrlupd_ack one cycle after the request | check |
| 52 | command during ctrlupd_ack: busy error | check |
| 53 | 4-cycle update ends without a handshake error | check |
| 54 | %0d-cycle update: handshake error | check |
| 55 | %0d-cycle update accepted | check |
| 56 | 70-cycle update: one handshake error (%0d) | check |
| 57 | PHY update request %0d with type %0d | check |
| 58 | PHY update takes 4 cycles after the ack (%0d) | check |
| 59 | in time | check |
| 60 | ack 40 cycles late: one handshake error (%0d) | check |
| 61 | command during phyupd_ack: busy error | check |
| 62 | ack dropped during the update: handshake error, request withdrawn | check |
| 63 | no lp_ack before tlp_resp | check |
| 64 | lp_ack four cycles after the request | check |
| 65 | command during lp_ack: busy error | check |
| 66 | lp_ack drops lp_wakeup + 1 cycles after the request (%0d) | check |
| 67 | lp_wakeup 0: request declined | check |
| 68 | request withdrawn before the ack: no ack | check |
| 69 | ack held while waking up | check |
| 70 | lp_wakeup 2: ack dropped 3 cycles after the request | check |
| 71 | frequency change: init_complete drops | check |
| 72 | frequency change with a bank open: bank error, new frequency | check |

## 3. UVM 測試平台內容

UVM agent test（`dfi_func_test`：directed + constrained-random 流量，scoreboard 以 DUT 模型的參考模型逐筆比對，並比對 driver 與 monitor 的 transaction）在 Verilator 上以 `python3 tools/run_uvm_tests.py DFI-VIP` 執行；agent 由 `tools/gen_uvm_agents.py` 依 `tools/uvm_agents/` 的協定 spec 產生。

| 項目 | 數量 | 名稱 |
|---|---|---|
| UVM tests | 2 | `dfi_base_test`, `dfi_func_test` |
| Sequences | 3 | `dfi_base_sequence`, `dfi_directed_sequence`, `dfi_transaction` |
| SVA（assert / cover property） | 7 / 3 | - |
| Covergroups / coverpoints | 1 / 19 | |

## 4. 充分度判定與缺口

判定：**✅ Sufficient**（80 個 check，mutation score 100%）。

無已知缺口。

