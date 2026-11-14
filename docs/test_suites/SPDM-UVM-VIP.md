# SPDM 1.4 Responder (DSP0274: VCA, measurements, ERROR rules) 測試套件（SPDM-UVM-VIP）

> 由 `tools/gen_test_suite_docs.py` 依 VIP 內容、`func_report.csv` 與 `mutation_report.csv` 自動產生，請勿手動修改。

## 1. 概要

| 項目 | 內容 |
|---|---|
| 類別 | Security |
| 類型 | UVM VIP |
| 功能測試 | 1 個檔案，56 個 check，全部通過 |
| Mutation | 26/26 個 mutant 被偵測（100%） |
| 判定 | **✅ Sufficient**（56 個 check，mutation score 100%） |

## 2. 可執行的功能測試

執行：`python3 tools/run_func_tests.py SPDM-UVM-VIP`（Icarus Verilog 或 Verilator 5.054）。

### `tb/smoke_func_tb.sv`

結果：**PASS**（iverilog，56 checks）

模型合約與範圍（摘自測試檔頭）：

```text
Functional smoke testbench (SPDM DUT model)
```

| # | Check | 類型 |
|---|---|---|
| 1 | reset: no response | check |
| 2 | GET_CAPABILITIES before GET_VERSION: ERROR UnexpectedRequest (SPDMVersion 1.0) | check |
| 3 | GET_VERSION with SPDMVersion 1.1: ERROR VersionMismatch with SPDMVersion 1.0 | check |
| 4 | 5-byte GET_VERSION: ERROR InvalidRequest | check |
| 5 | an invalid GET_VERSION does not start the connection | check |
| 6 | VERSION: SPDMVersion 1.0, one entry 0x1400 (1.4) little-endian | check |
| 7 | GET_CAPABILITIES with SPDMVersion 1.2: VersionMismatch | check |
| 8 | NEGOTIATE_ALGORITHMS before CAPABILITIES: UnexpectedRequest | check |
| 9 | DataTransferSize 41 < MinDataTransferSize 42: InvalidRequest | check |
| 10 | DataTransferSize 42 accepted | check |
| 11 | Param1 bit 0 (Supported Algorithms) without CHUNK_CAP: InvalidRequest | check |
| 12 | MaxSPDMmsgSize < DataTransferSize: InvalidRequest | check |
| 13 | no CHUNK_CAP and MaxSPDMmsgSize != DataTransferSize: InvalidRequest | check |
| 14 | 19-byte GET_CAPABILITIES: InvalidRequest | check |
| 15 | CAPABILITIES: CTExponent 12, MEAS_CAP = 01b only, DataTransferSize = MaxSPDMmsgSize = 64 | check |
| 16 | identical GET_CAPABILITIES retry: CAPABILITIES again | check |
| 17 | non-identical GET_CAPABILITIES: UnexpectedRequest | check |
| 18 | GET_MEASUREMENTS before ALGORITHMS: UnexpectedRequest | check |
| 19 | Length field 34 in a 32-byte request: InvalidRequest | check |
| 20 | 30-byte NEGOTIATE_ALGORITHMS: InvalidRequest | check |
| 21 | ALGORITHMS: Length 36, DMTF, Raw Bit Stream Only, no asymmetric / hash / PQC selection | check |
| 22 | identical NEGOTIATE_ALGORITHMS retry: ALGORITHMS again | check |
| 23 | non-identical NEGOTIATE_ALGORITHMS: UnexpectedRequest | check |
| 24 | GET_CAPABILITIES after ALGORITHMS: UnexpectedRequest | check |
| 25 | operation 0: 3 indices in Param1, no blocks, 50 bytes | check |
| 26 | Nonce: 32 bytes from the Responder's generator | check |
| 27 | OpaqueDataLength 0, Context echoed | check |
| 28 | block 1: DMTF, raw immutable ROM, 4 bytes 12 34 56 78 | check |
| 29 | the Nonce advances per MEASUREMENTS | check |
| 30 | block 3: raw firmware version 04 01 | check |
| 31 | Nonce after block 3 | check |
| 32 | block 2 needs 65 bytes > MaxSPDMmsgSize 64: ResponseTooLarge, ActualSize 65 | check |
| 33 | all blocks: 85 bytes, ResponseTooLarge | check |
| 34 | index 4 does not exist: InvalidRequest | check |
| 35 | SignatureRequested from a MEAS_CAP = 01b Responder: InvalidRequest | check |
| 36 | RawBitStreamRequested: raw block as before | check |
| 37 | Nonce | check |
| 38 | 11-byte GET_MEASUREMENTS: InvalidRequest | check |
| 39 | GET_DIGESTS: UnsupportedRequest naming 0x81 | check |
| 40 | a response code sent as a request: UnsupportedRequest | check |
| 41 | RESPOND_IF_READY with nothing pending: UnexpectedRequest | check |
| 42 | 65-byte request > 64: RequestTooLarge | check |
| 43 | 64-byte request: not too large (UnsupportedRequest for its code) | check |
| 44 | 1-byte message: silently discarded | check |
| 45 | Nonce | check |
| 46 | bytes during a response: dropped (err), the response is whole | check |
| 47 | Nonce | check |
| 48 | GET_VERSION clears the connection: GET_MEASUREMENTS is unexpected | check |
| 49 | MaxSPDMmsgSize 128: all 3 blocks (35-byte record, 85 bytes) | check |
| 50 | Nonce and Context after the record | check |
| 51 | a 61-byte MEASUREMENTS fits MaxSPDMmsgSize 61 exactly | check |
| 52 | Nonce | check |
| 53 | 65 bytes do not | check |
| 54 | CHUNK_CAP Requester: MaxSPDMmsgSize may exceed DataTransferSize | check |
| 55 | no DMTF offered: no measurement specification or hash selected | check |
| 56 | no measurement specification: GET_MEASUREMENTS unexpected | check |

## 3. UVM 測試平台內容

UVM agent test（`spdm_func_test`：directed + constrained-random 流量，scoreboard 以 DUT 模型的參考模型逐筆比對，並比對 driver 與 monitor 的 transaction）在 Verilator 上以 `python3 tools/run_uvm_tests.py SPDM-UVM-VIP` 執行；agent 由 `tools/gen_uvm_agents.py` 依 `tools/uvm_agents/` 的協定 spec 產生。

| 項目 | 數量 | 名稱 |
|---|---|---|
| UVM tests | 2 | `spdm_base_test`, `spdm_func_test` |
| Sequences | 3 | `spdm_base_sequence`, `spdm_directed_sequence`, `spdm_transaction` |
| SVA（assert / cover property） | 6 / 2 | - |
| Covergroups / coverpoints | 1 / 4 | |

## 4. 充分度判定與缺口

判定：**✅ Sufficient**（56 個 check，mutation score 100%）。

無已知缺口。

