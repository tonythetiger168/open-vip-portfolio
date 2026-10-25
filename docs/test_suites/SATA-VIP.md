# SATA 測試套件（SATA-VIP）

> 由 `tools/gen_test_suite_docs.py` 依 VIP 內容、`func_report.csv` 與 `mutation_report.csv` 自動產生，請勿手動修改。

## 1. 概要

| 項目 | 內容 |
|---|---|
| 類別 | Storage/Debug |
| 類型 | UVM VIP |
| 功能測試 | 1 個檔案，28 個 check，全部通過 |
| Mutation | 10/11 個 mutant 被偵測（91%） |
| 判定 | **✅ Sufficient**（28 個 check，mutation score 91%） |

## 2. 可執行的功能測試

執行：`python3 tools/run_func_tests.py SATA-VIP`（Icarus Verilog 或 Verilator 5.052）。

### `tb/func_sata_tb.sv`

結果：**PASS**（verilator，28 checks）

模型合約與範圍（摘自測試檔頭）：

```text
func_sata_tb.sv -- self-checking functional test for the SATA host model
(sata_host_model in tb/top_tb.sv, flattened by smoke/flatten.py).
Run: python3 tools/run_func_tests.py SATA-VIP

Model contract (from tb/top_tb.sv):
   * OOB: after reset release the host drives tx_p for 3 clocks (COMRESET),
     waits for the device's rx_p, and raises link_up 4 clocks later;
     link_speed reports Gen3 (3).
   * once the link is up the host sends Register H2D FISes (fis_type 0x27)
     cycling the commands IDENTIFY 0xEC, READ DMA EXT 0x25, WRITE SECTORS
     0x30, WRITE DMA 0xCA. Each FIS is three dwords D, D+1, D+2 with
     D = {8'h00, command, 8'h80, 8'h27} (Features, Command, C bit, FIS
     type 0x27 as in Register H2D dword 0); fis_start marks the first dword,
     fis_end the last. A dword advances only when ready is high and sync
     is low; one idle clock separates FISes.
   * a reset at any time drops link_up and restarts OOB from COMRESET.
```

| # | Check | 類型 |
|---|---|---|
| 1 | quiet in reset | check |
| 2 | data, primitive and FIS framing outputs idle in reset | check |
| 3 | link speed Gen3 | check |
| 4 | COMRESET starts at reset release | check |
| 5 | COMRESET held until the third clock edge (%0d time units) | check |
| 6 | single COMRESET burst | check |
| 7 | no link and no FIS before the device answers OOB | check |
| 8 | link_up 4 clocks after the device signal (got %0d) | check |
| 9 | every FIS starts with fis_start and ends with fis_end | check |
| 10 | FIS %0d is Register H2D (0x27) | check |
| 11 | FIS %0d: command %h in three consecutive dwords | check |
| 12 | fis_count counts completed FISes | check |
| 13 | dword 0 carries FIS type 0x27 and the C bit | check |
| 14 | ready low holds the FIS dword | check |
| 15 | transfer resumes intact after backpressure | check |
| 16 | SYNC holds the FIS dword | check |
| 17 | reset clears the FIS engine | check |
| 18 | reset drops link_up | check |
| 19 | OOB restarts with COMRESET after reset | check |
| 20 | link comes back up after the repeated OOB | check |

## 3. UVM 測試平台內容

UVM 測試需商用模擬器（VCS / Xcelium / Questa）執行；開源流程只做 elaboration（L1a）。

| 項目 | 數量 | 名稱 |
|---|---|---|
| UVM tests | 0 | - |
| Sequences | 16 | `base_tx`, `nvme_transaction`, `jtag_transaction`, `bluetooth5_transaction`, `displayport2_transaction`, `sata_base_sequence`, `sata_random_sequence`, `sata_reg_h2d_sequence`, `sata_dma_sequence`, `sata_error_inject_sequence`, `sata_back_to_back_seq`, `sata_stress_seq`, `sata_corner_seq`, `sata_reset_seq`, `sata_regression_seq`, `sata_transaction` |
| SVA（assert / cover property） | 31 / 31 | `assert_p_sata_link_speed`, `cover_p_sata_link_speed`, `assert_p_sata_primitive`, `cover_p_sata_primitive`, `assert_p_sata_fis_type`, `cover_p_sata_fis_type`, `assert_p_sata_data_valid`, `cover_p_sata_data_valid`, `assert_p_sata_fis_start`, `cover_p_sata_fis_start`, `assert_p_sata_sync`, `cover_p_sata_sync` … |
| Covergroups / coverpoints | 4 / 10 | |

## 4. 充分度判定與缺口

判定：**✅ Sufficient**（28 個 check，mutation score 91%）。

未被偵測的 mutant（測試缺口或等價 mutant）：

- `dut_sata_host_model.sv:40 0 -> 1 [vif_link_up = 0; vif_link_speed = 3'd3;]`

