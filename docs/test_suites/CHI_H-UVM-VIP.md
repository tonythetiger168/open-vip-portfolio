# CHI Issue H link level (SN-F, REQ / RSP / DAT flits, L-credits) 測試套件（CHI_H-UVM-VIP）

> 由 `tools/gen_test_suite_docs.py` 依 VIP 內容、`func_report.csv` 與 `mutation_report.csv` 自動產生，請勿手動修改。

## 1. 概要

| 項目 | 內容 |
|---|---|
| 類別 | AMBA |
| 類型 | UVM VIP |
| 功能測試 | 1 個檔案，63 個 check，全部通過 |
| Mutation | 28/28 個 mutant 被偵測（100%） |
| 判定 | **✅ Sufficient**（63 個 check，mutation score 100%） |

## 2. 可執行的功能測試

執行：`python3 tools/run_func_tests.py CHI_H-UVM-VIP`（Icarus Verilog 或 Verilator 5.052）。

### `tb/smoke_func_tb.sv`

結果：**PASS**（iverilog，63 checks）

模型合約與範圍（摘自測試檔頭）：

```text
Functional smoke testbench (CHIH DUT model)
```

| # | Check | 類型 |
|---|---|---|
| 1 | reset: no credits, no flits | check |
| 2 | REQ and DAT flits before the first L-credit: dropped (err 0) | check |
| 3 | 4 REQ and 4 DAT L-credits granted after reset | check |
| 4 | WriteNoSnpFull: CompDBIDResp to SrcID with the 12-bit TxnID | check |
| 5 | first DBID is the model's start value 0xFF0 (12 bits) | check |
| 6 | full write data accepted | check |
| 7 | one DAT L-credit back per write data flit | check |
| 8 | ReadNoSnp of 64 bytes: 4 CompData packets, no RSP | check |
| 9 | CompData_UC packet %0d: DataID %0d and the written data | check |
| 10 | no DMT: TgtID = ReturnNID = SrcID, TxnID = ReturnTxnID, HomeNID = SrcID, DBID = TxnID | check |
| 11 | CompData: QoS, DataSource, DataPull, CBusy, DBID MBZ, CacheLineID, TagOp, Tag, TU, TraceTag, CAH, NumDat, Replicate all 0 | check |
| 12 | Order 0b01: ReadReceipt to SrcID with TxnID | check |
| 13 | DMT: CompData to ReturnNID with ReturnTxnID, HomeNID = SrcID, DBID = TxnID | check |
| 14 | 16-byte read at 0x50: one packet, DataID = CCID = Addr[5:4] = 1 | check |
| 15 | read BE marks the 16-byte data window | check |
| 16 | Size %0d at 0x6C: %0d packet(s) from DataID %0d | check |
| 17 | Size 2 at 0x6C: BE bytes 12..15 of the packet | check |
| 18 | next DBID | check |
| 19 | partial write: random BE accepted | check |
| 20 | only bytes with BE are written | check |
| 21 | WriteDataCancel accepted | check |
| 22 | cancelled write left memory alone | check |
| 23 | Device WriteNoSnpPtl: BE below Addr breaks B2.9.3 | check |
| 24 | Device WriteNoSnpPtl: BE at and above Addr is fine | check |
| 25 | WriteNoSnpFull with a byte not enabled: error | check |
| 26 | the broken packet was not written | check |
| 27 | data under BE = 0 must be zero | check |
| 28 | BE outside the 4-byte data window | check |
| 29 | WriteDataCancel with a BE set | check |
| 30 | write data with no write waiting | check |
| 31 | write data with a TxnID that is not the DBID | check |
| 32 | write data with a DataID outside the transfer | check |
| 33 | SnpRespData is not write data | check |
| 34 | write data to another node | check |
| 35 | a repeated DataID | check |
| 36 | read at 1 KB: CompData with NDERR, data 0 | check |
| 37 | write above 1 KB: CompDBIDResp with NDERR | check |
| 38 | the NDERR write did not touch line 1 | check |
| 39 | REQ to another node: dropped | check |
| 40 | WriteUniqueFull is not an SN-F request | check |
| 41 | WriteNoSnpZero (7-bit opcode 0x44) not supported here | check |
| 42 | MultiReq request: not supported | check |
| 43 | NumReq / {3'b0, Size}: MBZ bit set | check |
| 44 | Size 128 bytes is reserved | check |
| 45 | Order 0b10 is reserved from HN-F to SN-F | check |
| 46 | Order 0b11 is reserved from HN-F to SN-F | check |
| 47 | WriteNoSnpFull of 32 bytes | check |
| 48 | dropped requests still return their L-credit | check |
| 49 | 5th REQ after a credit came back: accepted, 20 packets | check |
| 50 | 6 back-to-back REQ flits on 4 L-credits: one dropped (err 0), 5 served | check |
| 51 | 15 RSP and 15 DAT L-credits held: fine | check |
| 52 | a 16th RSP L-credit: overflow | check |
| 53 | a 16th DAT L-credit: overflow | check |
| 54 | after the overflow the link still works | check |

## 3. UVM 測試平台內容

UVM agent test（`chih_func_test`：directed + constrained-random 流量，scoreboard 以 DUT 模型的參考模型逐筆比對，並比對 driver 與 monitor 的 transaction）在 Verilator 上以 `python3 tools/run_uvm_tests.py CHI_H-UVM-VIP` 執行；agent 由 `tools/gen_uvm_agents.py` 依 `tools/uvm_agents/` 的協定 spec 產生。

| 項目 | 數量 | 名稱 |
|---|---|---|
| UVM tests | 2 | `chih_base_test`, `chih_func_test` |
| Sequences | 3 | `chih_base_sequence`, `chih_directed_sequence`, `chih_transaction` |
| SVA（assert / cover property） | 6 / 9 | - |
| Covergroups / coverpoints | 1 / 18 | |

## 4. 充分度判定與缺口

判定：**✅ Sufficient**（63 個 check，mutation score 100%）。

無已知缺口。

