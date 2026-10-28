# UALink 測試套件（UALink-VIP）

> 由 `tools/gen_test_suite_docs.py` 依 VIP 內容、`func_report.csv` 與 `mutation_report.csv` 自動產生，請勿手動修改。

## 1. 概要

| 項目 | 內容 |
|---|---|
| 類別 | Interconnect |
| 類型 | UVM VIP |
| 功能測試 | 2 個檔案，34 個 check，全部通過 |
| Mutation | 38/38 個 mutant 被偵測（100%） |
| 判定 | **✅ Sufficient**（34 個 check，mutation score 100%） |

## 2. 可執行的功能測試

執行：`python3 tools/run_func_tests.py UALink-VIP`（Icarus Verilog 或 Verilator 5.052）。

### `tb/smoke_func_tb.sv`

結果：**PASS**（iverilog，13 checks）

| # | Check | 類型 |
|---|---|---|
| 1 | ready high when idle | check |
| 2 | rsp quiet in reset | check |
| 3 | ready drops after accept | check |
| 4 | write rsp OK | check |
| 5 | rsp completes | check |
| 6 | ready returns | check |
| 7 | read rsp OK | check |
| 8 | read data matches write | check |
| 9 | illegal opcode ERR | check |
| 10 | rsp held until ready | check |
| 11 | rsp clears after ready | check |
| 12 | no response without a request | check |
| 13 | word 0 reads zero after reset | check |

### `ualink_tl/tb/func_ualink_tl_tb.sv`

結果：**PASS**（verilator，21 checks）

模型合約與範圍（摘自測試檔頭）：

```text
FUNC_SIM: verilator

func_ualink_tl_tb.sv -- requesting accelerator for ualink_tl_model, with
its own reference memory and the transaction rules written out
independently of the model:
   * READ / WRITE with byte enables, responses routed to the requester
   * out-of-order responses matched by tag; arrival-order execution
     (a read right after a slower write sees the write)
   * atomics ADD / SWAP / CAS (hit and miss) returning the old value,
     ADD without response (credit back on arrival)
   * status UR (opcode, alignment), address outside the window, poison
     set by a write, kept by a partial write, cleared by a full write
   * misrouted request, duplicate outstanding tag, credit overflow,
     response held stable under back-pressure
   * 600 random requests with random back-pressure
Run: python3 tools/run_func_tests.py UALink-VIP
```

| # | Check | 類型 |
|---|---|---|
| 1 | write, partial write, read back (%0d responses, %0d bad) | check |
| 2 | one credit back per accepted response | check |
| 3 | responses reordered by latency, matched by tag | check |
| 4 | read after write to the same line sees the write; arrival order kept at equal latency | check |
| 5 | ADD without response returns its credit on arrival | check |
| 6 | ADD / SWAP / CAS hit / CAS miss return the old value; no-response ADD applied (%0d bad) | check |
| 7 | opcode / alignment: UR; outside the window: address error; last line inside the window OK | check |
| 8 | response latency 3 + 5 * addr[7:6] for each latency class | check |
| 9 | equal due times leave in arrival order | check |
| 10 | equal due times: arrival order, not response-slot order | check |
| 11 | poisoned line: reads and atomics report poison, atomic leaves it, partial write keeps it, full write clears it | check |
| 12 | request for another accelerator ID dropped | check |
| 13 | second request with an outstanding tag dropped | check |
| 14 | same tag from another source accepted; responses routed to each source | check |
| 15 | request beyond the credits dropped | check |
| 16 | response held stable while not accepted, no credit back | check |
| 17 | all credits back once the responses are taken | check |
| 18 | 600 random requests within credits: no error | check |
| 19 | every random request answered once with the expected status and data (%0d bad, %0d missing) | check |
| 20 | every credit returned (%0d of %0d) | check |
| 21 | after reset line 0 reads zero, not poisoned | check |

## 3. UVM 測試平台內容

UVM agent test（`ualink_func_test`：directed + constrained-random 流量，scoreboard 以 DUT 模型的參考模型逐筆比對，並比對 driver 與 monitor 的 transaction）在 Verilator 上以 `python3 tools/run_uvm_tests.py UALink-VIP` 執行；agent 由 `tools/gen_uvm_agents.py` 依 `tools/uvm_agents/` 的協定 spec 產生。

| 項目 | 數量 | 名稱 |
|---|---|---|
| UVM tests | 2 | `ualink_base_test`, `ualink_func_test` |
| Sequences | 3 | `ualink_base_sequence`, `ualink_directed_sequence`, `ualink_transaction` |
| SVA（assert / cover property） | 4 / 2 | - |
| Covergroups / coverpoints | 1 / 3 | |

## 4. 充分度判定與缺口

判定：**✅ Sufficient**（34 個 check，mutation score 100%）。

無已知缺口。

