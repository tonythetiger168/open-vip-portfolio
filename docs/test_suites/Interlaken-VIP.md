# Interlaken v1.2 測試套件（Interlaken-VIP）

> 由 `tools/gen_test_suite_docs.py` 依 VIP 內容、`func_report.csv` 與 `mutation_report.csv` 自動產生，請勿手動修改。

## 1. 概要

| 項目 | 內容 |
|---|---|
| 類別 | Networking |
| 類型 | UVM VIP |
| 功能測試 | 1 個檔案，23 個 check，全部通過 |
| Mutation | 24/30 個 mutant 被偵測（80%） |
| 判定 | **✅ Sufficient**（23 個 check，mutation score 80%） |

## 2. 可執行的功能測試

執行：`python3 tools/run_func_tests.py Interlaken-VIP`（Icarus Verilog 或 Verilator 5.052）。

### `tb/func_intlkn_tb.sv`

結果：**PASS**（iverilog，23 checks）

模型合約與範圍（摘自測試檔頭）：

```text
func_intlkn_tb.sv -- self-checking functional test for the Interlaken
receiver model (intlkn_rx_dut in tb/top_tb.sv, flattened by smoke/flatten.py).
Run: python3 tools/run_func_tests.py Interlaken-VIP

Model contract (from tb/top_tb.sv and intlkn_defs_pkg):
   * lock: 4 diagnostic words (tx_diag with 0xD1A6_0000_5A5A_3C3C) take the
     receiver from reset through META to SYNC, 4 more to ACTIVE; a data
     word before lock restarts the sequence. A diag-flagged word with any
     other value counts as neither.
   * ACTIVE: data words pass to rx_* with a 3-clock latency, sop/eop kept;
     diagnostic words are not forwarded and reset a watchdog that counts
     idle clocks; the 33rd idle clock without a diagnostic word drops lock.
```

| # | Check | 類型 |
|---|---|---|
| 1 | reset: unlocked, no output | check |
| 2 | data before lock is not forwarded | check |
| 3 | three diagnostic words: META | check |
| 4 | fourth diagnostic word: SYNC | check |
| 5 | seven diagnostic words: still SYNC | check |
| 6 | eighth diagnostic word: ACTIVE | check |
| 7 | eight words forwarded (got %0d) | check |
| 8 | data forwarded in order and unchanged | check |
| 9 | sop on the first word, eop on the last | check |
| 10 | 3-clock latency: output registered on the third edge (%0d) | check |
| 11 | diagnostic words removed from the data stream | check |
| 12 | single-word packet has sop and eop | check |
| 13 | sop/eop on idle or diagnostic cycles never reach rx_sop/rx_eop | check |
| 14 | lock held through 30 idle clocks | check |
| 15 | diagnostic word resets the watchdog; 32 idle clocks tolerated | check |
| 16 | lock lost on the 33rd idle clock without a diagnostic word | check |
| 17 | no data forwarded after losing lock | check |
| 18 | diag-flagged words with the wrong value do not lock | check |
| 19 | back in SYNC | check |
| 20 | data word during SYNC restarts lock | check |
| 21 | data word during META restarts lock | check |
| 22 | reset clears lock and output | check |
| 23 | in-flight word discarded by reset | check |

## 3. UVM 測試平台內容

UVM 測試需商用模擬器（VCS / Xcelium / Questa）執行；開源流程只做 elaboration（L1a）。

| 項目 | 數量 | 名稱 |
|---|---|---|
| UVM tests | 3 | `intlkn_base_test`, `intlkn_random_test`, `intlkn_regression_test` |
| Sequences | 12 | `intlkn_base_sequence`, `intlkn_min_burst_seq`, `intlkn_max_burst_seq`, `intlkn_multi_channel_seq`, `intlkn_back_to_back_seq`, `intlkn_lock_seq`, `intlkn_align_seq`, `intlkn_error_inject_seq`, `intlkn_reset_seq`, `intlkn_random_sequence`, `intlkn_regression_sequence`, `intlkn_transaction` |
| SVA（assert / cover property） | 18 / 3 | `a_intlkn_l1_clk`, `a_intlkn_l1_rst`, `a_intlkn_l1_state`, `a_intlkn_l1_valid`, `a_intlkn_trans_reset`, `a_intlkn_trans_self_test`, `a_intlkn_trans_meta_lock`, `a_intlkn_trans_word_sync`, `a_intlkn_trans_active`, `a_intlkn_l3_reset_idle`, `a_intlkn_l3_lock_prog`, `a_intlkn_l3_full_cycle` … |
| Covergroups / coverpoints | 3 / 8 | |

## 4. 充分度判定與缺口

判定：**✅ Sufficient**（23 個 check，mutation score 80%）。

未被偵測的 mutant（測試缺口或等價 mutant）：

- `dut_intlkn_rx_dut.sv:40 0 -> 1 [diag_cnt <= 0;]`
- `dut_intlkn_rx_dut.sv:41 0 -> 1 [watchdog <= 0;]`
- `dut_intlkn_rx_dut.sv:58 0 -> 1 [rx_st <= RX_RESET; diag_cnt <= 0;]`
- `dut_intlkn_rx_dut.sv:64 0 -> 1 [if (diag_cnt >= INTM_LOCK_DIAGS-1) begin rx_st <= RX_ACTIVE;]`
- `dut_intlkn_rx_dut.sv:66 0 -> 1 [rx_st <= RX_RESET; diag_cnt <= 0;]`
- `dut_intlkn_rx_dut.sv:75 0 -> 1 [watchdog <= 0;]`

