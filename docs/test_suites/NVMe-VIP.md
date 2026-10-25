# NVMe 測試套件（NVMe-VIP）

> 由 `tools/gen_test_suite_docs.py` 依 VIP 內容、`func_report.csv` 與 `mutation_report.csv` 自動產生，請勿手動修改。

## 1. 概要

| 項目 | 內容 |
|---|---|
| 類別 | Storage/Debug |
| 類型 | UVM VIP |
| 功能測試 | 2 個檔案，57 個 check，全部通過 |
| Mutation | 8/8 個 mutant 被偵測（100%） |
| 判定 | **✅ Sufficient**（57 個 check，mutation score 100%） |

## 2. 可執行的功能測試

執行：`python3 tools/run_func_tests.py NVMe-VIP`（Icarus Verilog 或 Verilator 5.052）。

### `tb/func_nvme_tb.sv`

結果：**PASS**（verilator，24 checks）

模型合約與範圍（摘自測試檔頭）：

```text
func_nvme_tb.sv -- self-checking functional test for the NVMe controller
model (nvme_controller_model, flattened by smoke/flatten.py).
Run: python3 tools/run_func_tests.py NVMe-VIP

Model contract (from tb/top_tb.sv):
   Every change of the SQ tail doorbell is one command: the controller
   tags SQ entry word 0 ({16'd1, 0x80 admin / 0x01 I/O}), raises a 2-DW
   TLP at address 0x1000 * command count and holds TLP valid until ready.
   The accepted TLP completes the command: payload {addr, count, 16'h5A5A},
   status 0x00 (0x01 for QID > 7), IRQ asserted until CQ head == SQ tail.
   NVM command set (0) commands store the TLP data word in the namespace.
```

| # | Check | 類型 |
|---|---|---|
| 1 | TLP, IRQ and status idle in reset | check |
| 2 | SQ / CQ entry words cleared at start | check |
| 3 | requester ID 0x0100, TLP type 1 | check |
| 4 | no TLP / IRQ without a doorbell | check |
| 5 | TLP valid one clock after the doorbell | check |
| 6 | admin SQ entry tagged 0x80 | check |
| 7 | TLP length 2 DW | check |
| 8 | TLP valid drops after the handshake | check |
| 9 | TLP payload {addr, count, 5A5A} | check |
| 10 | completion: IRQ, success status | check |
| 11 | NVM command set stores one namespace word | check |
| 12 | IRQ held while CQ head lags SQ tail | check |
| 13 | IRQ cleared when CQ head == SQ tail | check |
| 14 | IRQ stays low with no new command | check |
| 15 | TLP valid and address held while ready is low | check |
| 16 | I/O SQ entry tagged 0x01 | check |
| 17 | non-NVM command set does not touch the namespace | check |
| 18 | QID 7 completes with success | check |
| 19 | QID 8 completes with invalid-queue status | check |
| 20 | CQ entry carries this command's status | check |
| 21 | next CQ entry carries success, not the previous error | check |
| 22 | 40 random commands: address, payload, status and IRQ correct | check |
| 23 | exactly one TLP per doorbell | check |
| 24 | reset clears TLP, IRQ and status | check |

### `tb/smoke_func_tb.sv`

結果：**PASS**（verilator，33 checks）

| # | Check | 類型 |
|---|---|---|
| 1 | tlp_valid quiet out of reset | check |
| 2 | irq quiet out of reset | check |
| 3 | status clean out of reset | check |
| 4 | requester id initialised | check |
| 5 | no TLP while idle | check |
| 6 | no IRQ while idle | check |
| 7 | TLP type is memory read | check |
| 8 | TLP length 2 DW | check |
| 9 | doorbell 1 addr = 0x1000 | check |
| 10 | doorbell produced a TLP pulse | check |
| 11 | completion raised IRQ | check |
| 12 | submission entry tagged admin (0x80) | check |
| 13 | TLP payload = {addr, count, 5A5A} | check |
| 14 | qid 0 -> success status | check |
| 15 | IRQ cleared when cq_head == sq_tail | check |
| 16 | doorbell 2 addr = 0x2000 | check |
| 17 | second doorbell produced TLP | check |
| 18 | second completion raised IRQ | check |
| 19 | second TLP payload | check |
| 20 | qid 8 -> invalid queue status | check |
| 21 | IRQ cleared again | check |
| 22 | non-admin doorbell also produces TLP | check |
| 23 | non-admin entry tagged 0x01 | check |

## 3. UVM 測試平台內容

UVM 測試需商用模擬器（VCS / Xcelium / Questa）執行；開源流程只做 elaboration（L1a）。

| 項目 | 數量 | 名稱 |
|---|---|---|
| UVM tests | 0 | - |
| Sequences | 16 | `base_tx`, `sata_transaction`, `jtag_transaction`, `bluetooth5_transaction`, `displayport2_transaction`, `nvme_base_sequence`, `nvme_random_sequence`, `nvme_admin_sequence`, `nvme_io_rw_sequence`, `nvme_error_inject_sequence`, `nvme_back_to_back_seq`, `nvme_stress_seq`, `nvme_corner_seq`, `nvme_reset_seq`, `nvme_regression_seq`, `nvme_transaction` |
| SVA（assert / cover property） | 32 / 32 | `assert_p_nvme_tlp_type`, `cover_p_nvme_tlp_type`, `assert_p_nvme_tag`, `cover_p_nvme_tag`, `assert_p_nvme_tc`, `cover_p_nvme_tc`, `assert_p_nvme_length`, `cover_p_nvme_length`, `assert_p_nvme_sq_tail`, `cover_p_nvme_sq_tail`, `assert_p_nvme_cq_head`, `cover_p_nvme_cq_head` … |
| Covergroups / coverpoints | 4 / 12 | |

## 4. 充分度判定與缺口

判定：**✅ Sufficient**（57 個 check，mutation score 100%）。

無已知缺口。

