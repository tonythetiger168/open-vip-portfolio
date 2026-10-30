# UALink 測試套件（UALink-VIP）

> 由 `tools/gen_test_suite_docs.py` 依 VIP 內容、`func_report.csv` 與 `mutation_report.csv` 自動產生，請勿手動修改。

## 1. 概要

| 項目 | 內容 |
|---|---|
| 類別 | Interconnect |
| 類型 | UVM VIP |
| 功能測試 | 3 個檔案，90 個 check，全部通過 |
| Mutation | 58/58 個 mutant 被偵測（100%） |
| 判定 | **✅ Sufficient**（90 個 check，mutation score 100%） |

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

### `ualink_inc/tb/func_ualink_inc_tb.sv`

結果：**PASS**（iverilog，55 checks）

模型合約與範圍（摘自測試檔頭）：

```text
FUNC_SIM: iverilog

func_ualink_inc_tb.sv -- accelerator ports and a host for
ualink_inc_model (UALink 2.0 In-Network Compute), with a reference of the
collective rules written out independently of the model:
   * all-reduce SUM / MIN / MAX / AND / OR / XOR over 4 signed lanes,
     hand-computed results, multicast mask and round sequence
   * SUM saturation (both signs) and the saturated status, reset per round
   * every rejection code (non-member, disabled group, busy, wrong round,
     duplicate, bad opcode, opcode mismatch) with no effect on the round
   * round timeout and its exact boundary, partial multicast mask
   * held results under back-pressure, lowest group first, reconfiguration
   * 1500 random contributions on 4 groups with random back-pressure,
     checked clock by clock against the reference
Run: python3 tools/run_func_tests.py UALink-VIP
```

| # | Check | 類型 |
|---|---|---|
| 1 | 3 of 4 contributions accepted, no result yet | check |
| 2 | SUM all-reduce: (10, 0, 250, 0) multicast to ports 0-3, round 0 | check |
| 3 | result delivered exactly once | check |
| 4 | MIN is signed per lane | check |
| 5 | MAX is signed per lane | check |
| 6 | AND per lane | check |
| 7 | OR per lane | check |
| 8 | XOR per lane | check |
| 9 | op %0d: round %0d, status OK | check |
| 10 | SUM saturates at both ends, status saturated | check |
| 11 | exact max is not saturated; flag reset per round | check |
| 12 | exact min is not saturated | check |
| 13 | port not in the group: rejected (1) | check |
| 14 | disabled group: rejected (1) | check |
| 15 | wrong round: rejected (3) | check |
| 16 | first contribution accepted | check |
| 17 | second contribution from the same port: rejected (2) | check |
| 18 | opcode 6: rejected (5) | check |
| 19 | opcode 7: rejected (5) | check |
| 20 | opcode differs from the round: rejected (4) | check |
| 21 | rejections do not complete the round | check |
| 22 | rejected data left out of the result | check |
| 23 | round 1 completes and is held | check |
| 24 | contribution while the result is held: busy (6) | check |
| 25 | round 1 result still held under back-pressure | check |
| 26 | round advanced to 2 on completion, not on the busy contribution | check |
| 27 | round 2 accepts after delivery | check |
| 28 | no abort before the timeout | check |
| 29 | timeout: status 2, data 0, multicast to the ports that contributed | check |
| 30 | completion on the last clock of the window | check |
| 31 | single contribution: no abort one clock early | check |
| 32 | single contribution times out | check |
| 33 | late contribution after delivery: round has advanced (3) | check |
| 34 | single-member group completes on its own contribution | check |
| 35 | delivery held stable under back-pressure | check |
| 36 | group 7 (on the bus first) then group 6 | check |
| 37 | reconfiguring a group drops its held result | check |
| 38 | results held behind a delivery leave lowest group first | check |
| 39 | reconfiguration clears the partial round | check |
| 40 | round restarts from the reconfiguration | check |
| 41 | mask 0 disables the group | check |
| 42 | %0d random contributions: every acknowledge and code as expected | check |
| 43 | random rounds: every delivered result as expected (%0d delivered) | check |
| 44 | every held result delivered | check |
| 45 | group 0: MAX result held under back-pressure | check |
| 46 | group 0 result delivered | check |
| 47 | group 0 round times out | check |
| 48 | group 0 as the reference | check |
| 49 | reset clears the delivery | check |
| 50 | after reset every group is disabled | check |
| 51 | after reset group 0 is disabled too | check |

### `ualink_tl/tb/func_ualink_tl_tb.sv`

結果：**PASS**（verilator，22 checks）

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
| 21 | every response not accepted stayed on the bus unchanged | check |
| 22 | after reset line 0 reads zero, not poisoned | check |

## 3. UVM 測試平台內容

UVM agent test（`ualink_func_test`：directed + constrained-random 流量，scoreboard 以 DUT 模型的參考模型逐筆比對，並比對 driver 與 monitor 的 transaction）在 Verilator 上以 `python3 tools/run_uvm_tests.py UALink-VIP` 執行；agent 由 `tools/gen_uvm_agents.py` 依 `tools/uvm_agents/` 的協定 spec 產生。

| 項目 | 數量 | 名稱 |
|---|---|---|
| UVM tests | 2 | `ualink_base_test`, `ualink_func_test` |
| Sequences | 3 | `ualink_base_sequence`, `ualink_directed_sequence`, `ualink_transaction` |
| SVA（assert / cover property） | 4 / 2 | - |
| Covergroups / coverpoints | 1 / 3 | |

## 4. 充分度判定與缺口

判定：**✅ Sufficient**（90 個 check，mutation score 100%）。

無已知缺口。

