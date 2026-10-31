# CXL 測試套件（CXL-VIP）

> 由 `tools/gen_test_suite_docs.py` 依 VIP 內容、`func_report.csv` 與 `mutation_report.csv` 自動產生，請勿手動修改。

## 1. 概要

| 項目 | 內容 |
|---|---|
| 類別 | Interconnect |
| 類型 | UVM VIP |
| 功能測試 | 3 個檔案，76 個 check，全部通過 |
| Mutation | 9/10 個 mutant 被偵測（90%） |
| 判定 | **✅ Sufficient**（76 個 check，mutation score 90%） |

## 2. 可執行的功能測試

執行：`python3 tools/run_func_tests.py CXL-VIP`（Icarus Verilog 或 Verilator 5.052）。

### `cxl_bundle/tb/func_cxl_bundle_tb.sv`

結果：**PASS**（iverilog，34 checks）

| # | Check | 類型 |
|---|---|---|
| 1 | bundle of 4 ports: width 4 | check |
| 2 | 8 flits striped over 4 ports delivered in order | check |
| 3 | skewed port: flits wait for the late one, no retry | check |
| 4 | mask 1011: width 3 | check |
| 5 | striping over ports 0, 1, 3 | check |
| 6 | flit on a port outside the bundle: dropped (err 0), no retry | check |
| 7 | flit on the wrong port: dropped, retry from 6 | check |
| 8 | while the retry is pending later flits are dropped silently | check |
| 9 | replay from 6 delivered | check |
| 10 | flit behind next: duplicate, dropped, no retry | check |
| 11 | duplicate of a buffered flit dropped | check |
| 12 | flit beyond the window: retry from next | check |
| 13 | replay fills the window | check |
| 14 | flit at next + W - 1 is inside the window | check |
| 15 | bad flit: retry from the next undelivered flit | check |
| 16 | flits buffered before the bad one in the same clock are cleared | check |
| 17 | replay delivered after a bad flit | check |
| 18 | no retry before the gap timeout | check |
| 19 | gap timeout after GTMO clocks: retry from 0 | check |
| 20 | gap filled on the last clock: no retry | check |
| 21 | port 1 lost: width 3, retry from 4 | check |
| 22 | replay striped over ports 0, 2, 3 | check |
| 23 | flit on the lost port dropped | check |
| 24 | port_down on a port already out: no effect | check |
| 25 | bundle of one port | check |
| 26 | only buffer slot 0 held (flit 8): gap timeout, retry from 1 | check |
| 27 | reconfiguration empties every buffer slot | check |
| 28 | flit 2048 ahead counts as behind: duplicate, no retry | check |
| 29 | port 0 lost: width 3, retry | check |
| 30 | directed: every output as the reference | check |
| 31 | %0d random flits: deliveries, retries, width and errors as the reference (%0d delivered, %0d retries) | check |
| 32 | random run exercised retries and deliveries | check |
| 33 | reset clears the bundle | check |
| 34 | after reset no port is in the bundle | check |

### `cxl_mem/tb/func_cxl_mem_tb.sv`

結果：**PASS**（verilator，29 checks）

| # | Check | 類型 |
|---|---|---|
| 1 | MemWr: one Cmp per write, tag and old Meta0-State | check |
| 2 | MemRd: MemData with the written line and Meta0-State | check |
| 3 | completions return out of order, matched by tag | check |
| 4 | MemWrPtl merges by byte enable; poison stored, kept and returned | check |
| 5 | an unpoisoned MemWr clears the poison | check |
| 6 | a read in the same clock as a write to the line sees the write | check |
| 7 | Meta0-State: MemRd / MemInv update it, MemRdData and No-Op do not | check |
| 8 | MemSpecRd: no response, credit returned | check |
| 9 | no error so far | check |
| 10 | MemRdFwd rejected without a response | check |
| 11 | outside the HDM range: poisoned read, write dropped | check |
| 12 | a ninth Req beyond 8 credits: overflow | check |
| 13 | the eight Req within the credits complete | check |
| 14 | every Req credit is returned (the dropped ninth took none) | check |
| 15 | four host NDR credits: four Cmp, two waiting | check |
| 16 | returned NDR credits release the waiting responses | check |
| 17 | every RwD credit is returned | check |
| 18 | a fifth RwD beyond 4 credits: overflow | check |
| 19 | the dropped MemWr did not write; the other four completed | check |
| 20 | no DRS credit: both reads wait | check |
| 21 | one DRS credit: the earliest-due read is sent | check |
| 22 | next credit: the second read | check |
| 23 | no NDR credit: both Cmp wait | check |
| 24 | one NDR credit: the earliest-due Cmp is sent | check |
| 25 | next credit: the second Cmp | check |
| 26 | all %0d NDR and %0d DRS responses as expected | check |
| 27 | reset drops the pending responses and clears the errors | check |
| 28 | RwD with a reserved opcode rejected without a response | check |
| 29 | memory reads zero after reset | check |

### `tb/smoke_func_tb.sv`

結果：**PASS**（verilator，13 checks）

| # | Check | 類型 |
|---|---|---|
| 1 | channel beat during reset is ignored | check |
| 2 | no transfer in progress after reset | check |
| 3 | beat without SOP outside a transaction is dropped | check |
| 4 | single-beat transaction counted once | check |
| 5 | single-beat transaction data stored at address | check |
| 6 | channel busy between SOP and EOP | check |
| 7 | multi-beat transaction counted once at EOP | check |
| 8 | channel idle after EOP | check |
| 9 | payload DW0 at addr+0 | check |
| 10 | payload DW1 at addr+4 | check |
| 11 | payload DW2 at addr+8 | check |
| 12 | back-to-back transaction counted | check |
| 13 | later transaction overwrites previous contents | check |

## 3. UVM 測試平台內容

UVM 測試需商用模擬器（VCS / Xcelium / Questa）執行；開源流程只做 elaboration（L1a）。

| 項目 | 數量 | 名稱 |
|---|---|---|
| UVM tests | 5 | `mp_base_test`, `mp_cxl_test`, `mp_error_inject_test`, `mp_power_mgmt_test`, `mp_random_regression_test` |
| Sequences | 10 | `mp_base_sequence`, `mp_back_to_back_sequence`, `mp_stress_sequence`, `mp_corner_case_sequence`, `mp_reset_sequence`, `mp_error_inject_sequence`, `mp_power_mgmt_sequence`, `mp_random_sequence`, `mp_regression_sequence`, `mp_sequence_item` |
| SVA（assert / cover property） | 24 / 21 | `assert_valid_ready`, `assert_sop_eop`, `assert_link_state`, `assert_p_cxl_h2d_valid`, `cover_p_cxl_h2d_valid`, `assert_p_cxl_cache_id`, `cover_p_cxl_cache_id`, `assert_p_cxl_link_state`, `cover_p_cxl_link_state`, `assert_p_cxl_sop_data`, `cover_p_cxl_sop_data`, `assert_p_cxl_no_x_data` … |
| Covergroups / coverpoints | 7 / 20 | |

## 4. 充分度判定與缺口

判定：**✅ Sufficient**（76 個 check，mutation score 90%）。

未被偵測的 mutant（測試缺口或等價 mutant）：

- `dut_cxl_mem_model.sv:102 1'b1 inverted [if (k < 0) err[1] <= 1'b1;]`

