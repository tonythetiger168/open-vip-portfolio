# DisplayPort2 測試套件（DisplayPort2-VIP）

> 由 `tools/gen_test_suite_docs.py` 依 VIP 內容、`func_report.csv` 與 `mutation_report.csv` 自動產生，請勿手動修改。

## 1. 概要

| 項目 | 內容 |
|---|---|
| 類別 | Storage/Debug |
| 類型 | UVM VIP |
| 功能測試 | 1 個檔案，14 個 check，全部通過 |
| Mutation | 18/18 個 mutant 被偵測（100%） |
| 判定 | **✅ Sufficient**（14 個 check，mutation score 100%） |

## 2. 可執行的功能測試

執行：`python3 tools/run_func_tests.py DisplayPort2-VIP`（Icarus Verilog 或 Verilator 5.052）。

### `tb/func_displayport2_tb.sv`

結果：**PASS**（iverilog，14 checks）

模型合約與範圍（摘自測試檔頭）：

```text
func_displayport2_tb.sv -- self-checking functional test for the
DisplayPort 2 sink model (displayport2_sink_model in top/top_tb.sv,
flattened by smoke/flatten.py).
Run: python3 tools/run_func_tests.py DisplayPort2-VIP

Model contract (from top/top_tb.sv), one event per clock:
   * msa_valid counts a frame; with main_stream_active the MSA is checked:
     hactive > htotal or vactive > vtotal is one timing error, hsync_end <
     hsync_start or vsync_end < vsync_start another (each `uvm_error).
   * sdp_valid counts an SDP; type 0x30 (PSR) is also counted as PSR.
   * the sink becomes "trained" on K28.5 (0xBC) on all four lanes; after
     that a K character during active video is counted (`uvm_warning).
Known defect (XFAIL): lane_data is 4 bits wide but is compared with the
32-bit {4{8'hBC}}, so the sink never becomes trained and K characters in
the video stream are never flagged.
```

| # | Check | 類型 |
|---|---|---|
| 1 | K28.5 on all four lanes completes training | XFAIL（模型缺陷） |
| 2 | three legal 1080p MSAs counted, no error | check |
| 3 | active == total and sync end == start are legal | check |
| 4 | hactive > htotal flagged | check |
| 5 | vactive > vtotal flagged | check |
| 6 | hsync end before start flagged | check |
| 7 | vsync end before start flagged | check |
| 8 | active and sync violations in one MSA are both flagged | check |
| 9 | MSA without main stream counted, not checked | check |
| 10 | every SDP counted | check |
| 11 | PSR SDPs (type 0x30) counted | check |
| 12 | K character during active video after training is flagged | XFAIL（模型缺陷） |
| 13 | no K-character check before link training is done | check |
| 14 | reset clears the training state | check |

## 3. UVM 測試平台內容

UVM 測試需商用模擬器（VCS / Xcelium / Questa）執行；開源流程只做 elaboration（L1a）。

| 項目 | 數量 | 名稱 |
|---|---|---|
| UVM tests | 14 | `base_test`, `sata_random_test`, `sata_regression_test`, `nvme_random_test`, `nvme_regression_test`, `jtag_random_test`, `jtag_regression_test`, `bt5_random_test`, `bt5_regression_test`, `dp2_random_test`, `dp2_regression_test`, `dp2_error_test`, `dp2_psr_test`, `full_regression_test` |
| Sequences | 21 | `bluetooth5_transaction`, `bluetooth5_random_sequence`, `base_tx`, `displayport2_base_sequence`, `displayport2_random_sequence`, `displayport2_uhbr_sequence`, `displayport2_dsc_sequence`, `displayport2_8k_sequence`, `displayport2_error_sequence`, `displayport2_back_to_back_sequence`, `displayport2_reset_sequence`, `displayport2_psr_sequence`, `displayport2_stress_sequence`, `displayport2_regression_sequence`, `displayport2_transaction`, `jtag_transaction`, `jtag_random_sequence`, `nvme_transaction`, `nvme_random_sequence`, `sata_transaction` |
| SVA（assert / cover property） | 31 / 31 | `assert_p_dp_link_rate`, `cover_p_dp_link_rate`, `assert_p_dp_lane_count`, `cover_p_dp_lane_count`, `assert_p_dp_bpp`, `cover_p_dp_bpp`, `assert_p_dp_sdp`, `cover_p_dp_sdp`, `assert_p_dp_training`, `cover_p_dp_training`, `assert_p_dp_msa`, `cover_p_dp_msa` … |
| Covergroups / coverpoints | 3 / 12 | |

## 4. 充分度判定與缺口

判定：**✅ Sufficient**（14 個 check，mutation score 100%）。

DUT 模型缺陷（XFAIL check，修好模型後會變成 XPASS 提醒移除標記）：

- K28.5 on all four lanes completes training
- K character during active video after training is flagged

