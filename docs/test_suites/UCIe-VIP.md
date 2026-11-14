# UCIe 測試套件（UCIe-VIP）

> 由 `tools/gen_test_suite_docs.py` 依 VIP 內容、`func_report.csv` 與 `mutation_report.csv` 自動產生，請勿手動修改。

## 1. 概要

| 項目 | 內容 |
|---|---|
| 類別 | Interconnect |
| 類型 | UVM VIP |
| 功能測試 | 3 個檔案，130 個 check，全部通過 |
| Mutation | 10/10 個 mutant 被偵測（100%） |
| 判定 | **✅ Sufficient**（130 個 check，mutation score 100%） |

## 2. 可執行的功能測試

執行：`python3 tools/run_func_tests.py UCIe-VIP`（Icarus Verilog 或 Verilator 5.054）。

### `tb/smoke_func_tb.sv`

結果：**PASS**（iverilog，24 checks）

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
| 13 | reference queue matches tready/rvalid/rdata/rlast for 400 clocks (%0d mismatches) | check |
| 14 | random phase reached full, pop at full, and push+pop (seen=%0d) | check |
| 15 | flits queued before reset | check |
| 16 | reset empties the FIFO | check |
| 17 | first flit after reset at head | check |

### `ucie_d2d/tb/func_ucie_d2d_tb.sv`

結果：**PASS**（verilator，70 checks）

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
| 9 | parameter response in SBINIT is unexpected | check |
| 10 | partner's done answered: MBINIT | check |
| 11 | parameter response carries the local max speed 5 | check |
| 12 | lane fault in lanes 8..15: repair response offers x8 | check |
| 13 | repair request x8 | check |
| 14 | MBTRAIN at min(5, 3) = speed 3, width min(16, 8) = 8 | check |
| 15 | speed 3 fails at the partner, 2 locally: trained at 1 (%0d tries) | check |
| 16 | speed 1 after degrade | check |
| 17 | LINKINIT: link not up yet | check |
| 18 | LINKINIT holds until the partner's LINKINIT request | check |
| 19 | LINKINIT request sent once without waiting for the partner | check |
| 20 | ACTIVE: link up, protocol layer may send | check |
| 21 | MBTRAIN response and unknown message in ACTIVE flagged, state kept | check |
| 22 | MBTRAIN request outside training flagged, not answered | check |
| 23 | no flit before the protocol layer offers data | check |
| 24 | 20 flits, sequence 0..19, data intact (%0d sent, %0d bad) | check |
| 25 | flit CRCs good, no error | check |
| 26 | retry buffer full after %0d unacknowledged flits: ready low | check |
| 27 | ACK of 3 flits frees 3 entries (%0d sent) | check |
| 28 | NAK: flits 25..30 replayed, then the waiting flit 31 (%0d, %0d bad) | check |
| 29 | flit 31 sent after the replay | check |
| 30 | no ACK for %0d clocks: flit 31 replayed on timeout | check |
| 31 | fourth replay: replay limit flagged | check |
| 32 | replay limit requests a retrain | check |
| 33 | back to ACTIVE at the trained speed | check |
| 34 | unacknowledged flit kept across the retrain and replayed | check |
| 35 | ACKed: no more replays | check |
| 36 | idle with nothing outstanding: no replay timeout, no retrain | check |
| 37 | three flits delivered in order | check |
| 38 | ACK 2 sent in a NOP flit | check |
| 39 | corrupted flit dropped | check |
| 40 | one NAK with the last good sequence 2 | check |
| 41 | sequence ahead dropped, no second NAK while one is scheduled | check |
| 42 | replayed flit 3 delivered, duplicate 1 not delivered | check |
| 43 | duplicate answered with ACK 3 | check |
| 44 | a new sequence error after recovery NAKs again | check |
| 45 | flits 4 and 5 delivered | check |
| 46 | ACK 6 carried by data flit 32 | check |
| 47 | L1 refused with flit 32 unacknowledged | check |
| 48 | NAK with a single outstanding flit replays it | check |
| 49 | fourth NAK replay: replay limit flagged, retrain requested | check |
| 50 | back to ACTIVE after the NAK replay limit | check |
| 51 | L1 accepted with the retry buffer empty | check |
| 52 | no mainband reception in L1 | check |
| 53 | L1 request while in L1 flagged, not answered | check |
| 54 | L1 exit: MBTRAIN | check |
| 55 | L1 exit retrains to ACTIVE | check |
| 56 | sequence numbers continue after L1 | check |
| 57 | partner retrain request answered: MBTRAIN | check |
| 58 | partner retrain back to ACTIVE | check |
| 59 | local retrain request waits in PHYRETRAIN for the response | check |
| 60 | retrain response: MBTRAIN | check |
| 61 | lt_start low: RESET | check |
| 62 | retrained: speed min(5, 4), x8 on the upper half | check |
| 63 | sequence numbers restart at 0 after RESET | check |
| 64 | receiver expects sequence 0 after RESET | check |
| 65 | faults in both halves: TRAINERROR (state %0d err %h) | check |
| 66 | speeds 2, 1, 0 all fail: TRAINERROR (state %0d err %h n %0d) | check |
| 67 | silent partner: TRAINERROR after %0d clocks (state %0d err %h) | check |
| 68 | TRAINERROR to RESET when lt_start drops | check |
| 69 | no LINKINIT response: TRAINERROR %0d clocks after the partner's request | check |
| 70 | every flit from the model has a good CRC | check |

### `ucie_sb3/tb/func_ucie_sb3_tb.sv`

結果：**PASS**（iverilog，36 checks）

模型合約與範圍（摘自測試檔頭）：

```text
FUNC_SIM: iverilog

func_ucie_sb3_tb.sv -- sideband partner for ucie_sb3_model (UCIe 3.0
sideband additions) with a reference written out independently of the
model:
   * register reads / byte-enabled writes, UR outside the register file,
     completion tag, status, data and parity
   * priority packets overtake the normal queue, queue-full drops
   * management transport: in-order reassembly, 1..8 dwords, SOM restart,
     wrong fragment seq, fragment without SOM, overflow
   * runtime recalibration: pause length, RecalDone, busy while running,
     RecalDone held while the normal queue is full
   * throttle levels, emergency shutdown held until reset, parity errors,
     unknown opcodes
   * 3000 random packets with random back-pressure, checked clock by
     clock against the reference
Run: python3 tools/run_func_tests.py UCIe-VIP
```

| # | Check | 類型 |
|---|---|---|
| 1 | MemWr32: Cpl, tag 3, status 0, even parity | check |
| 2 | byte-enabled write, read back | check |
| 3 | read outside the register file: UR | check |
| 4 | UR write did not alias into the register file | check |
| 5 | register 15 is inside the file | check |
| 6 | queues empty | check |
| 7 | fifth normal request with the normal queue full: dropped (err 2) | check |
| 8 | priority Cpl replaces the waiting normal one | check |
| 9 | priority queue (2) drained first, third priority dropped, then normal in order | check |
| 10 | 3-fragment message reassembled in order | check |
| 11 | single-fragment message (SOM and EOM) | check |
| 12 | SOM restarts the message (err 3 for the dropped partial one) | check |
| 13 | wrong fragment seq: message dropped (err 3) | check |
| 14 | fragment without a started message: dropped | check |
| 15 | 8-dword message | check |
| 16 | 9 dwords: message dropped (err 4) | check |
| 17 | management fragments get no Cpl | check |
| 18 | RecalReq: mainband paused for RECAL_T clocks (%0d) | check |
| 19 | RecalReq accepted (Cpl status 0) | check |
| 20 | RecalDone sent when the pause ends | check |
| 21 | RecalReq accepted | check |
| 22 | second RecalReq while running: busy (status 2) | check |
| 23 | one RecalDone for the accepted request | check |
| 24 | pause continues while RecalDone cannot be queued | check |
| 25 | priority RecalReq while RecalDone waits: busy | check |
| 26 | RecalDone queued after the 4 waiting packets | check |
| 27 | fast throttle level 2 | check |
| 28 | throttle released | check |
| 29 | parity error: dropped (err 0) | check |
| 30 | two flipped bits keep parity: handled as a read | check |
| 31 | unknown opcode: dropped (err 1) | check |
| 32 | emergency shutdown | check |
| 33 | shutdown held; directed packets as the reference | check |
| 34 | %0d random packets: every output as the reference (%0d sent, %0d messages) | check |
| 35 | reset clears shutdown, throttle and queues | check |
| 36 | registers cleared by reset | check |

## 3. UVM 測試平台內容

UVM agent test（`ucie_func_test`：directed + constrained-random 流量，scoreboard 以 DUT 模型的參考模型逐筆比對，並比對 driver 與 monitor 的 transaction）在 Verilator 上以 `python3 tools/run_uvm_tests.py UCIe-VIP` 執行；agent 由 `tools/gen_uvm_agents.py` 依 `tools/uvm_agents/` 的協定 spec 產生。

| 項目 | 數量 | 名稱 |
|---|---|---|
| UVM tests | 2 | `ucie_base_test`, `ucie_func_test` |
| Sequences | 3 | `ucie_base_sequence`, `ucie_directed_sequence`, `ucie_transaction` |
| SVA（assert / cover property） | 3 / 2 | - |
| Covergroups / coverpoints | 1 / 1 | |

## 4. 充分度判定與缺口

判定：**✅ Sufficient**（130 個 check，mutation score 100%）。

無已知缺口。

