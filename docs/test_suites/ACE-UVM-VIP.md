# ACE 測試套件（ACE-UVM-VIP）

> 由 `tools/gen_test_suite_docs.py` 依 VIP 內容、`func_report.csv` 與 `mutation_report.csv` 自動產生，請勿手動修改。

## 1. 概要

| 項目 | 內容 |
|---|---|
| 類別 | AMBA |
| 類型 | UVM VIP |
| 功能測試 | 1 個檔案，19 個 check，全部通過 |
| Mutation | 10/10 個 mutant 被偵測（100%） |
| 判定 | **✅ Sufficient**（19 個 check，mutation score 100%） |

## 2. 可執行的功能測試

執行：`python3 tools/run_func_tests.py ACE-UVM-VIP`（Icarus Verilog 或 Verilator 5.052）。

### `tb/smoke_func_tb.sv`

結果：**PASS**（verilator，19 checks）

模型合約與範圍（摘自測試檔頭）：

```text
Functional smoke testbench (ACE DUT model)
```

| # | Check | 類型 |
|---|---|---|
| 1 | R / B / AC idle in reset | check |
| 2 | ReadNoSnoop: four beats of 0 | check |
| 3 | WriteNoSnoop: OKAY | check |
| 4 | WriteNoSnoop byte strobes merged | check |
| 5 | ReadOnce of line 5 returns its current contents | check |
| 6 | unsupported ARSNOOP: SLVERR, no data | check |
| 7 | unsupported AWSNOOP: SLVERR | check |
| 8 | read data matches the reference (%0d of %0d wrong) | check |
| 9 | RRESP IsShared / PassDirty and BRESP match the reference (%0d wrong) | check |
| 10 | four R beats per read, one for CleanUnique | check |
| 11 | snoops seen: ReadOnce %0d ReadShared %0d ReadUnique %0d CleanInvalid %0d MakeInvalid %0d | check |
| 12 | no snoop while a RACK is owed | check |
| 13 | snoops still start late in the run (%0d in the last 100 transactions) | check |
| 14 | the peer snoops only with commands its line state allows (no ReadShared / ReadUnique / MakeInvalid for a line it owns dirty, no ReadShared for one it shares) | check |
| 15 | ARREADY low while a write waits for its data | check |
| 16 | AWREADY low while a read waits for RREADY | check |
| 17 | the WriteUnique of line 14 read back | check |
| 18 | ACPROT 0 | check |
| 19 | all 16 lines match the reference at the end (%0d wrong) | check |

## 3. UVM 測試平台內容

UVM agent test（`ace_func_test`：directed + constrained-random 流量，scoreboard 以 DUT 模型的參考模型逐筆比對，並比對 driver 與 monitor 的 transaction）在 Verilator 上以 `python3 tools/run_uvm_tests.py ACE-UVM-VIP` 執行；agent 由 `tools/gen_uvm_agents.py` 依 `tools/uvm_agents/` 的協定 spec 產生。

| 項目 | 數量 | 名稱 |
|---|---|---|
| UVM tests | 2 | `ace_base_test`, `ace_func_test` |
| Sequences | 3 | `ace_base_sequence`, `ace_directed_sequence`, `ace_transaction` |
| SVA（assert / cover property） | 15 / 4 | - |
| Covergroups / coverpoints | 1 / 7 | |

## 4. 充分度判定與缺口

判定：**✅ Sufficient**（19 個 check，mutation score 100%）。

無已知缺口。

