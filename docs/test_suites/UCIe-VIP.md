# UCIe 測試套件（UCIe-VIP）

> 由 `tools/gen_test_suite_docs.py` 依 VIP 內容、`func_report.csv` 與 `mutation_report.csv` 自動產生，請勿手動修改。

## 1. 概要

| 項目 | 內容 |
|---|---|
| 類別 | Interconnect |
| 類型 | UVM VIP |
| 功能測試 | 2 個檔案，83 個 check，全部通過 |
| Mutation | 43/43 個 mutant 被偵測（100%） |
| 判定 | **✅ Sufficient**（83 個 check，mutation score 100%） |

## 2. 可執行的功能測試

執行：`python3 tools/run_func_tests.py UCIe-VIP`（Icarus Verilog 或 Verilator 5.052）。

### `tb/smoke_func_tb.sv`

結果：**PASS**（iverilog，19 checks）

| # | Check | 類型 |
|---|---|---|
| 1 | tready high when empty | check |
| 2 | rvalid low when empty | check |
| 3 | flit0 head of queue | check |
| 4 | flit1 loopback order | check |
| 5 | flit2 loopback with tlast | check |
| 6 | drained after 3 flits | check |
| 7 | accept while not full | check |
| 8 | tready low when full | check |
| 9 | oldest flit at head | check |
| 10 | fully drained after backpressure test | check |
| 11 | tready high when empty | check |
| 12 | all 6 burst flits delivered | check |

### `ucie_d2d/tb/func_ucie_d2d_tb.sv`

結果：**PASS**（verilator，64 checks）

模型合約與範圍（摘自測試檔頭）：

```text
FUNC_SIM: verilator

func_ucie_d2d_tb.sv -- link partner for ucie_d2d_model: a sideband
responder, a flit transmitter / receiver with its own CRC-16 (checked
first against the CRC-16/CCITT-FALSE check value) and a protocol-layer
driver. Covers:
   * training: SBINIT pattern and done handshakes, MBINIT parameter and
     lane-repair exchange (x16, x8 on either half, both halves failed),
     MBTRAIN speed degrade on remote and local failures, LINKINIT, ACTIVE
   * TRAINERROR on sideband timeout, unrepairable lanes and no trainable
     speed; RESET on lt_start low; unexpected sideband messages
   * retry: sequence numbers, ACK purge, retry-buffer back-pressure,
     receiver CRC / sequence errors with a single NAK, duplicates, NAK
     replay, replay timeout, replay limit -> retrain, data kept across
     the retrain
   * PHY retrain by the partner, L1 entry refused with flits outstanding,
     accepted when empty, L1 exit
Run: python3 tools/run_func_tests.py UCIe-VIP
```

| # | Check | 類型 |
|---|---|---|
| 1 | bench CRC-16 matches the CRC-16/CCITT-FALSE check value 29B1 | check |
| 2 | RESET after reset | check |
| 3 | no flit, delivery or sideband message during and after reset | check |
| 4 | SBINIT: patterns, no done before two partner patterns | check |
| 5 | SBINIT patterns every 4 clocks | check |
| 6 | done request before the patterns is unexpected | check |
| 7 | done request after two partner patterns | check |
| 8 | SBINIT holds until the partner's done request is answered | check |
| 9 | partner's done answered: MBINIT | check |
| 10 | parameter response carries the local max speed 5 | check |
| 11 | lane fault in lanes 8..15: repair response offers x8 | check |
| 12 | repair request x8 | check |
| 13 | MBTRAIN at min(5, 3) = speed 3, width min(16, 8) = 8 | check |
| 14 | speed 3 fails at the partner, 2 locally: trained at 1 (%0d tries) | check |
| 15 | speed 1 after degrade | check |
| 16 | LINKINIT: link not up yet | check |
| 17 | LINKINIT holds until the partner's LINKINIT request | check |
| 18 | ACTIVE: link up, protocol layer may send | check |
| 19 | MBTRAIN response and unknown message in ACTIVE flagged, state kept | check |
| 20 | MBTRAIN request outside training flagged | check |
| 21 | no flit before the protocol layer offers data | check |
| 22 | 20 flits, sequence 0..19, data intact (%0d sent, %0d bad) | check |
| 23 | flit CRCs good, no error | check |
| 24 | retry buffer full after %0d unacknowledged flits: ready low | check |
| 25 | ACK of 3 flits frees 3 entries (%0d sent) | check |
| 26 | NAK: flits 25..30 replayed, then the waiting flit 31 (%0d, %0d bad) | check |
| 27 | flit 31 sent after the replay | check |
| 28 | no ACK for %0d clocks: flit 31 replayed on timeout | check |
| 29 | fourth replay: replay limit flagged | check |
| 30 | replay limit requests a retrain | check |
| 31 | back to ACTIVE at the trained speed | check |
| 32 | unacknowledged flit kept across the retrain and replayed | check |
| 33 | ACKed: no more replays | check |
| 34 | idle with nothing outstanding: no replay timeout, no retrain | check |
| 35 | three flits delivered in order | check |
| 36 | ACK 2 sent in a NOP flit | check |
| 37 | corrupted flit dropped | check |
| 38 | one NAK with the last good sequence 2 | check |
| 39 | sequence ahead dropped, no second NAK while one is scheduled | check |
| 40 | replayed flit 3 delivered, duplicate 1 not delivered | check |
| 41 | duplicate answered with ACK 3 | check |
| 42 | a new sequence error after recovery NAKs again | check |
| 43 | flits 4 and 5 delivered | check |
| 44 | ACK 6 carried by data flit 32 | check |
| 45 | L1 refused with flit 32 unacknowledged | check |
| 46 | L1 accepted with the retry buffer empty | check |
| 47 | no mainband reception in L1 | check |
| 48 | L1 exit: MBTRAIN | check |
| 49 | L1 exit retrains to ACTIVE | check |
| 50 | sequence numbers continue after L1 | check |
| 51 | partner retrain request answered: MBTRAIN | check |
| 52 | partner retrain back to ACTIVE | check |
| 53 | local retrain request waits in PHYRETRAIN for the response | check |
| 54 | retrain response: MBTRAIN | check |
| 55 | lt_start low: RESET | check |
| 56 | retrained: speed min(5, 4), x8 on the upper half | check |
| 57 | sequence numbers restart at 0 after RESET | check |
| 58 | receiver expects sequence 0 after RESET | check |
| 59 | faults in both halves: TRAINERROR (state %0d err %h) | check |
| 60 | speeds 2, 1, 0 all fail: TRAINERROR (state %0d err %h n %0d) | check |
| 61 | silent partner: TRAINERROR after %0d clocks (state %0d err %h) | check |
| 62 | TRAINERROR to RESET when lt_start drops | check |
| 63 | no LINKINIT response: TRAINERROR %0d clocks after the partner's request | check |
| 64 | every flit from the model has a good CRC | check |

## 3. UVM 測試平台內容

UVM agent test（`ucie_func_test`：directed + constrained-random 流量，scoreboard 以 DUT 模型的參考模型逐筆比對，並比對 driver 與 monitor 的 transaction）在 Verilator 上以 `python3 tools/run_uvm_tests.py UCIe-VIP` 執行；agent 由 `tools/gen_uvm_agents.py` 依 `tools/uvm_agents/` 的協定 spec 產生。

| 項目 | 數量 | 名稱 |
|---|---|---|
| UVM tests | 2 | `ucie_base_test`, `ucie_func_test` |
| Sequences | 3 | `ucie_base_sequence`, `ucie_directed_sequence`, `ucie_transaction` |
| SVA（assert / cover property） | 3 / 2 | - |
| Covergroups / coverpoints | 1 / 1 | |

## 4. 充分度判定與缺口

判定：**✅ Sufficient**（83 個 check，mutation score 100%）。

無已知缺口。

