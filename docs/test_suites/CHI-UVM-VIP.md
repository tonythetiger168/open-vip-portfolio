# CHI 測試套件（CHI-UVM-VIP）

> 由 `tools/gen_test_suite_docs.py` 依 VIP 內容、`func_report.csv` 與 `mutation_report.csv` 自動產生，請勿手動修改。

## 1. 概要

| 項目 | 內容 |
|---|---|
| 類別 | AMBA |
| 類型 | UVM VIP |
| 功能測試 | 2 個檔案，53 個 check，全部通過 |
| Mutation | 27/28 個 mutant 被偵測（96%） |
| 判定 | **✅ Sufficient**（53 個 check，mutation score 96%） |

## 2. 可執行的功能測試

執行：`python3 tools/run_func_tests.py CHI-UVM-VIP`（Icarus Verilog 或 Verilator 5.052）。

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

結果：**PASS**（iverilog，14 checks）

| # | Check | 類型 |
|---|---|---|
| 1 | channels reset quiet | check |
| 2 | no response without request | check |
| 3 | no ready without request | check |
| 4 | REQ accepted | check |
| 5 | DAT accepted | check |
| 6 | RSPVALID after request | check |
| 7 | RSP OK status | check |
| 8 | RSP completes | check |
| 9 | second REQ accepted | check |
| 10 | second RSP received | check |

## 3. UVM 測試平台內容

UVM agent test（`chi_func_test`：directed + constrained-random 流量，scoreboard 以 DUT 模型的參考模型逐筆比對，並比對 driver 與 monitor 的 transaction）在 Verilator 上以 `python3 tools/run_uvm_tests.py CHI-UVM-VIP` 執行；agent 由 `tools/gen_uvm_agents.py` 依 `tools/uvm_agents/` 的協定 spec 產生。

| 項目 | 數量 | 名稱 |
|---|---|---|
| UVM tests | 2 | `chi_base_test`, `chi_func_test` |
| Sequences | 3 | `chi_base_sequence`, `chi_directed_sequence`, `chi_transaction` |
| SVA（assert / cover property） | 3 / 2 | - |
| Covergroups / coverpoints | 1 / 2 | |

## 4. 充分度判定與缺口

判定：**✅ Sufficient**（53 個 check，mutation score 96%）。

未被偵測的 mutant（測試缺口或等價 mutant）：

- `dut_chi_hn_model.sv:114 && flipped [WACK: if (ack_valid && ack_rn == rn) st <= IDLE;]`

