# CHI 測試套件（CHI-UVM-VIP）

> 由 `tools/gen_test_suite_docs.py` 依 VIP 內容、`func_report.csv` 與 `mutation_report.csv` 自動產生，請勿手動修改。

## 1. 概要

| 項目 | 內容 |
|---|---|
| 類別 | AMBA |
| 類型 | UVM VIP |
| 功能測試 | 2 個檔案，155 個 check，全部通過 |
| Mutation | 29/29 個 mutant 被偵測（100%） |
| 判定 | **✅ Sufficient**（155 個 check，mutation score 100%） |

## 2. 可執行的功能測試

執行：`python3 tools/run_func_tests.py CHI-UVM-VIP`（Icarus Verilog 或 Verilator 5.054）。

### `chi_hn/tb/func_chi_hn_tb.sv`

結果：**PASS**（iverilog，39 checks）

模型合約與範圍（摘自測試檔頭）：

```text
FUNC_SIM: iverilog

func_chi_hn_tb.sv -- two caching request nodes for chi_hn_model, each with
its own cache (I / SC / UC / UD and data) and snoop responder, and the
expected home behaviour written out independently of the model:
   * every request type with and without a copy in the other node, the
     snoop it needs (none, SnpShared, SnpOnce, SnpUnique), the granted
     state and the data (always the latest value written by either node)
   * dirty data from SnpShared reaches memory, from SnpOnce it does not
   * CompAck: required by ReadShared / ReadUnique / CleanUnique /
     MakeUnique, the home blocks until it arrives
   * error bits: write-back without ownership, CleanUnique without a
     copy, illegal / misrouted snoop responses, stray CompAck, bad opcode,
     line out of range
   * 2500 random transactions on 6 shared lines with random snoop and
     CompAck delays and back-pressure; single-writer / multiple-reader and
     data checked after every transaction
Run: python3 tools/run_func_tests.py CHI-UVM-VIP
```

| # | Check | 類型 |
|---|---|---|
| 1 | ReadShared with no other copy: CompData UC, no snoop | check |
| 2 | WriteBackFull: Comp I | check |
| 3 | written-back data read from memory | check |
| 4 | ReadShared of a UC line: SnpShared, both SC | check |
| 5 | second sharer of a line held SC: no snoop | check |
| 6 | CleanUnique from SC: SnpUnique to the sharer, Comp UC | check |
| 7 | ReadUnique of a UD line: dirty data passed, UC | check |
| 8 | ReadShared of a UD line: data from the snoop | check |
| 9 | SnpShared dirty data was written to memory | check |
| 10 | ReadOnce of a UD line: SnpOnce, data 4444, owner keeps UD | check |
| 11 | SnpOnce data was not written to memory | check |
| 12 | ReadOnce of a UC (clean) line: SnpOnce, memory data | check |
| 13 | MakeUnique: SnpUnique, Comp UD | check |
| 14 | line written after MakeUnique read back by the other node | check |
| 15 | no new request accepted before CompAck | check |
| 16 | ReadOnce needs no CompAck | check |
| 17 | SnpShared answered with I: requester gets UC | check |
| 18 | no error in legal flows | check |
| 19 | WriteBackFull without ownership: err 0, Comp I | check |
| 20 | memory not written by it | check |
| 21 | CleanUnique without a copy: err 1, still Comp UC | check |
| 22 | CompAck with nothing outstanding: err 3 | check |
| 23 | no snoop response yet | check |
| 24 | snoop response from the requester: ignored (err 2) | check |
| 25 | SnpUnique answered SC: completes | check |
| 26 | filter follows the (illegal) SC answer: the node is snooped again | check |
| 27 | opcode 7: err 4, Comp I | check |
| 28 | line 64: err 5, CompData I of zero, no snoop | check |
| 29 | ReadOnce to line 65: CompData I | check |
| 30 | WriteBackFull to line 66: Comp | check |
| 31 | bad requests need no CompAck | check |
| 32 | directed: every snoop, state and data as expected | check |
| 33 | %0d random transactions: snoops, states, data and single-writer rule as expected | check |
| 34 | error bits only from the error tests | check |
| 35 | reset clears errors | check |
| 36 | SnpUnique answered SC: err 2 only, completes | check |
| 37 | SnpShared answered UC: err 2 only; the node still holds the line, CompData SC | check |
| 38 | after reset line 0 reads zero and the filter is empty | check |
| 39 | line 63 reads zero | check |

### `tb/smoke_func_tb.sv`

結果：**PASS**（verilator，116 checks）

模型合約與範圍（摘自測試檔頭）：

```text
Functional smoke testbench (CHI DUT model)
```

| # | Check | 類型 |
|---|---|---|
| 1 | %s: four CompData beats (%0d beats, %0d rsp, %0d errors) | check |
| 2 | %s: Comp (op %0h rs %0d er %0d) | check |
| 3 | %s: CompDBIDResp (op %0h er %0d) | check |
| 4 | %s: data accepted | check |
| 5 | %s: protocol error %0d (got %0d, %0d errors) | check |
| 6 | reset values | check |
| 7 | REQ flit before an L-credit: error 1 | check |
| 8 | two L-credits per inbound channel (%0d %0d %0d) | check |
| 9 | the flit without credit was dropped | check |
| 10 | no CompData before we grant RXDAT credits; REQ credit returned | check |
| 11 | two RXDAT credits: two beats (%0d) | check |
| 12 | ReadNoSnp: the rest of the line | check |
| 13 | ReadNoSnp: DBID 0, I, OK | check |
| 14 | CopyBackWrData for a WriteNoSnp: error 6 | check |
| 15 | write data for a DBID not waiting: error 6 | check |
| 16 | write data for DBID 800: error 6 | check |
| 17 | then the right data completes the write | check |
| 18 | NonCopyBackWrData for a WriteBack: error 6 | check |
| 19 | CompAck with no tracker waiting: error 6 | check |
| 20 | TXRSP opcode other than CompAck: error 6 | check |
| 21 | two ReadUniques hold both trackers | check |
| 22 | distinct DBIDs | check |
| 23 | no tracker: RetryAck with PCrdType 1 | check |
| 24 | a second RetryAck | check |
| 25 | CompAck frees a tracker: PCrdGrant | check |
| 26 | the freed tracker is reserved: RetryAck | check |
| 27 | re-sent with AllowRetry 0: served on the reserved tracker | check |
| 28 | next free tracker: grant for the second retry | check |
| 29 | second retried request served | check |
| 30 | no tracker left waiting for CompAck | check |
| 31 | three retries, three grants: none left | check |
| 32 | third retried request served | check |
| 33 | write waiting for data while a read completes | check |
| 34 | Evict while both trackers wait: RetryAck | check |
| 35 | one grant for one retry | check |
| 36 | retried Evict completes | check |
| 37 | back-to-back Evicts need no tracker | check |
| 38 | no RXRSP credit: six Comps queued, REQ credits withheld (%0d sent, %0d accepted) | check |
| 39 | queued Comps delivered (%0d) | check |
| 40 | Comp %0d in order | check |
| 41 | REQ credits granted again (%0d) | check |
| 42 | reset | check |
| 43 | credits granted again after reset | check |
| 44 | after reset: TxnID 80 is free, memory kept | check |

## 3. UVM 測試平台內容

UVM agent test（`chi_func_test`：directed + constrained-random 流量，scoreboard 以 DUT 模型的參考模型逐筆比對，並比對 driver 與 monitor 的 transaction）在 Verilator 上以 `python3 tools/run_uvm_tests.py CHI-UVM-VIP` 執行；agent 由 `tools/gen_uvm_agents.py` 依 `tools/uvm_agents/` 的協定 spec 產生。

| 項目 | 數量 | 名稱 |
|---|---|---|
| UVM tests | 2 | `chi_base_test`, `chi_func_test` |
| Sequences | 3 | `chi_base_sequence`, `chi_directed_sequence`, `chi_transaction` |
| SVA（assert / cover property） | 6 / 3 | - |
| Covergroups / coverpoints | 1 / 9 | |

## 4. 充分度判定與缺口

判定：**✅ Sufficient**（155 個 check，mutation score 100%）。

無已知缺口。

