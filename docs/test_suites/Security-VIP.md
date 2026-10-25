# Crypto / Security Engine 測試套件（Security-VIP）

> 由 `tools/gen_test_suite_docs.py` 依 VIP 內容、`func_report.csv` 與 `mutation_report.csv` 自動產生，請勿手動修改。

## 1. 概要

| 項目 | 內容 |
|---|---|
| 類別 | Security |
| 類型 | UVM VIP |
| 功能測試 | 1 個檔案，17 個 check，全部通過 |
| Mutation | 25/25 個 mutant 被偵測（100%） |
| 判定 | **✅ Sufficient**（17 個 check，mutation score 100%） |

## 2. 可執行的功能測試

執行：`python3 tools/run_func_tests.py Security-VIP`（Icarus Verilog 或 Verilator 5.052）。

### `tb/func_security_tb.sv`

結果：**PASS**（iverilog，17 checks）

模型合約與範圍（摘自測試檔頭）：

```text
func_security_tb.sv -- self-checking functional test for the security
(block cipher) engine model (security_engine_model, flattened by
smoke/flatten.py). Run: python3 tools/run_func_tests.py Security-VIP

Model contract (from tb/top_tb.sv and security_defs_pkg):
   key_valid loads a 64-bit key (key_loaded=1, IDLE->LOAD_KEY->IDLE);
   key_clear zeroises it. start runs one 64-bit block: ENCRYPT
   (rotl8(d) ^ k) for mode=0, DECRYPT (rotr8(e ^ k)) for mode=1; busy is high
   while the block is processed and data_out is presented with a one-clock
   out_valid. start without a key, or a mode change while busy, enters
   ERROR with err high for 2 clocks; no output is produced.
```

| # | Check | 類型 |
|---|---|---|
| 1 | outputs cleared in reset | check |
| 2 | idle, no key after reset | check |
| 3 | start without a key: err for 2 clocks, no output | check |
| 4 | engine returns to IDLE after the error | check |
| 5 | key_valid loads the key | check |
| 6 | encrypt matches the reference cipher | check |
| 7 | out_valid is a single-clock pulse | check |
| 8 | busy asserted while the block is processed | check |
| 9 | fixed block latency: out_valid 4 clocks after start | check |
| 10 | busy cleared once the block is done | check |
| 11 | decrypt(encrypt(P)) round-trips to the plaintext | check |
| 12 | decrypt matches the reference cipher | check |
| 13 | new key changes the ciphertext | check |
| 14 | mode change while busy aborts with err for 2 clocks, no output | check |
| 15 | key_clear zeroises the key | check |
| 16 | start after key_clear is rejected | check |
| 17 | reset clears the key and state | check |

## 3. UVM 測試平台內容

UVM 測試需商用模擬器（VCS / Xcelium / Questa）執行；開源流程只做 elaboration（L1a）。

| 項目 | 數量 | 名稱 |
|---|---|---|
| UVM tests | 3 | `security_base_test`, `security_random_test`, `security_regression_test` |
| Sequences | 12 | `security_base_sequence`, `security_encrypt_seq`, `security_decrypt_seq`, `security_roundtrip_seq`, `security_corner_seq`, `security_same_key_seq`, `security_no_key_seq`, `security_mode_flip_seq`, `security_reset_seq`, `security_random_sequence`, `security_regression_sequence`, `security_transaction` |
| SVA（assert / cover property） | 20 / 3 | `a_security_l1_clk`, `a_security_l1_rst`, `a_security_l1_state`, `a_security_l1_valid`, `a_security_trans_idle`, `a_security_trans_load_key`, `a_security_trans_encrypt`, `a_security_trans_decrypt`, `a_security_trans_done`, `a_security_trans_error`, `a_security_l3_reset_idle`, `a_security_l3_no_stuck` … |
| Covergroups / coverpoints | 3 / 7 | |

## 4. 充分度判定與缺口

判定：**✅ Sufficient**（17 個 check，mutation score 100%）。

無已知缺口。

