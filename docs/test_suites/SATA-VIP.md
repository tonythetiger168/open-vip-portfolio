# SATA 測試套件（SATA-VIP）

> 由 `tools/gen_test_suite_docs.py` 依 VIP 內容、`func_report.csv` 與 `mutation_report.csv` 自動產生，請勿手動修改。

## 1. 概要

| 項目 | 內容 |
|---|---|
| 類別 | Storage/Debug |
| 類型 | UVM VIP |
| 功能測試 | 1 個檔案，51 個 check，全部通過 |
| Mutation | 24/25 個 mutant 被偵測（96%） |
| 判定 | **✅ Sufficient**（51 個 check，mutation score 96%） |

## 2. 可執行的功能測試

執行：`python3 tools/run_func_tests.py SATA-VIP`（Icarus Verilog 或 Verilator 5.054）。

### `tb/func_sata_tb.sv`

結果：**PASS**（verilator，51 checks）

模型合約與範圍（摘自測試檔頭）：

```text
func_sata_tb.sv -- self-checking functional test for the SATA host model
(sata_host_model in tb/top_tb.sv, flattened by smoke/flatten.py).
Run: python3 tools/run_func_tests.py SATA-VIP

Model contract (from tb/top_tb.sv):
   * OOB: after reset release the host drives tx_p for 3 clocks (COMRESET),
     waits for the device's rx_p, then drives tx_n (COMWAKE, held while the
     link is up) and raises link_up 4 clocks later; link_speed reports
     Gen3 (3) and the idle primitive 0x7B4A4ABC is on the line.
   * once the link is up the host sends Register H2D FISes (fis_type 0x27).
     FIS n carries command n mod 13 of IDENTIFY 0xEC, READ DMA EXT 0x25,
     WRITE DMA EXT 0x35, WRITE SECTORS 0x30, WRITE DMA 0xCA, 0xEA, 0x91,
     READ SECTORS 0x20, READ VERIFY 0x40, READ FPDMA 0x60, SEEK 0x70,
     FLUSH CACHE 0xE7, SET FEATURES 0xEF and LBA 8*n. Each FIS is two
     dwords: {8'h00, command, 8'h80, 8'h27} (Features, Command, C bit, FIS
     type) with fis_start, then {8'h40, LBA[23:0]} (device = LBA mode) with
     fis_end. A FIS starts and a dword advances only when ready is high and
     sync is low; one idle clock separates FISes.
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
| 9 | COMWAKE (tx_n) held while the link is up | check |
| 10 | idle primitive on the line after reset | check |
| 11 | every FIS starts with fis_start and ends with fis_end | check |
| 12 | FIS %0d is Register H2D (0x27) | check |
| 13 | FIS %0d: command %h, then LBA %0d | check |
| 14 | fis_count counts completed FISes | check |
| 15 | dword 0 carries FIS type 0x27 and the C bit | check |
| 16 | ready low holds the FIS dword | check |
| 17 | transfer resumes intact after backpressure | check |
| 18 | SYNC holds the FIS dword | check |
| 19 | no FIS while the device is not ready | check |
| 20 | no FIS starts while the device sends SYNC | check |
| 21 | FIS starts after SYNC is released | check |
| 22 | reset clears the FIS engine | check |
| 23 | reset drops link_up and COMWAKE | check |
| 24 | OOB restarts with COMRESET after reset | check |
| 25 | link comes back up after the repeated OOB | check |

## 3. UVM 測試平台內容

UVM agent test（`sata_func_test`：directed + constrained-random 流量，scoreboard 以 DUT 模型的參考模型逐筆比對，並比對 driver 與 monitor 的 transaction）在 Verilator 上以 `python3 tools/run_uvm_tests.py SATA-VIP` 執行；agent 由 `tools/gen_uvm_agents.py` 依 `tools/uvm_agents/` 的協定 spec 產生。

| 項目 | 數量 | 名稱 |
|---|---|---|
| UVM tests | 2 | `sata_base_test`, `sata_func_test` |
| Sequences | 17 | `base_tx`, `nvme_transaction`, `jtag_transaction`, `bluetooth5_transaction`, `displayport2_transaction`, `sata_base_sequence`, `sata_random_sequence`, `sata_reg_h2d_sequence`, `sata_dma_sequence`, `sata_error_inject_sequence`, `sata_back_to_back_seq`, `sata_stress_seq`, `sata_corner_seq`, `sata_reset_seq`, `sata_regression_seq`, `sata_transaction`, `sata_fis_sequence` |
| SVA（assert / cover property） | 31 / 31 | `assert_p_sata_link_speed`, `cover_p_sata_link_speed`, `assert_p_sata_primitive`, `cover_p_sata_primitive`, `assert_p_sata_fis_type`, `cover_p_sata_fis_type`, `assert_p_sata_data_valid`, `cover_p_sata_data_valid`, `assert_p_sata_fis_start`, `cover_p_sata_fis_start`, `assert_p_sata_sync`, `cover_p_sata_sync` … |
| Covergroups / coverpoints | 4 / 10 | |

## 4. 充分度判定與缺口

判定：**✅ Sufficient**（51 個 check，mutation score 96%）。

未被偵測的 mutant（測試缺口或等價 mutant）：

- `dut_sata_host_model.sv:31 0 -> 1 [int fis_count = 0;]`

