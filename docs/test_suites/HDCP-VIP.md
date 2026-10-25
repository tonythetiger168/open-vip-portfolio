# HDCP 2.3 Content Protection 測試套件（HDCP-VIP）

> 由 `tools/gen_test_suite_docs.py` 依 VIP 內容、`func_report.csv` 與 `mutation_report.csv` 自動產生，請勿手動修改。

## 1. 概要

| 項目 | 內容 |
|---|---|
| 類別 | Security |
| 類型 | UVM VIP |
| 功能測試 | 1 個檔案，20 個 check，全部通過 |
| Mutation | 10/12 個 mutant 被偵測（83%） |
| 判定 | **✅ Sufficient**（20 個 check，mutation score 83%） |

## 2. 可執行的功能測試

執行：`python3 tools/run_func_tests.py HDCP-VIP`（Icarus Verilog 或 Verilator 5.052）。

### `tb/func_hdcp_tb.sv`

結果：**PASS**（verilator，20 checks）

模型合約與範圍（摘自測試檔頭）：

```text
FUNC_SIM: verilator  (vvp 12 segfaults in the model's DDC slave)

func_hdcp_tb.sv -- self-checking functional test for the HDCP receiver
model (hdcp_receiver_model in tb/top_tb.sv, flattened by smoke/flatten.py).
Run: python3 tools/run_func_tests.py HDCP-VIP

Model contract (from tb/top_tb.sv and hdcp_defs_pkg):
   * DDC slave at 7-bit address 0x3A (0x74 write / 0x75 read) on an open-drain SDA. A write sets a
     register offset and appends the following bytes: AKE_INIT (0x01)
     shifts them into Aksv, LC_INIT (0x03) into rN; other offsets are
     ACKed and ignored. A read returns Bksv, 5 bytes MSB first, until the
     master NACKs; Bksv is A5C3F01234, or DEADBEEF01 when rcv_revoked.
   * Ri: on entering ENCRYPTED, ri = ri_compute(Aksv, Bksv, 0) and then
     ri_compute(..., k) every 16 clocks, with ri_compute = aksv[15:0] ^
     bksv[15:0] ^ {k[7:0], ~k[7:0]} ^ 0x9E37.
```

| # | Check | 類型 |
|---|---|---|
| 1 | receiver answers at the HDCP DDC read address 0x75 | check |
| 2 | other DDC addresses are not ACKed | check |
| 3 | old 7-bit 0x74 address is not ACKed | check |
| 4 | Bksv read back, 5 bytes MSB first | check |
| 5 | master NACK ends the Bksv read early | check |
| 6 | revoked receiver presents the revoked Bksv | check |
| 7 | AKE_INIT write: all bytes ACKed, Aksv stored | check |
| 8 | LC_INIT write: rN stored | check |
| 9 | LC_INIT does not touch Aksv | check |
| 10 | SKE write ACKed without changing Aksv or rN | check |
| 11 | write to another address ignored | check |
| 12 | no Ri before encryption | check |
| 13 | Ri(0) on entering ENCRYPTED | check |
| 14 | Ri held for 16 clocks | check |
| 15 | Ri(1) after 16 clocks | check |
| 16 | Ri(4) after 64 clocks | check |
| 17 | Ri follows the presented Bksv | check |
| 18 | Ri held outside ENCRYPTED | check |
| 19 | new Aksv: Ri restarts at frame 0 | check |
| 20 | reset clears Ri | check |

## 3. UVM 測試平台內容

UVM 測試需商用模擬器（VCS / Xcelium / Questa）執行；開源流程只做 elaboration（L1a）。

| 項目 | 數量 | 名稱 |
|---|---|---|
| UVM tests | 3 | `hdcp_base_test`, `hdcp_random_test`, `hdcp_regression_test` |
| Sequences | 12 | `hdcp_base_sequence`, `hdcp_auth_seq`, `hdcp_auth_only_seq`, `hdcp_revoked_bksv_seq`, `hdcp_ri_mismatch_seq`, `hdcp_short_frame_seq`, `hdcp_long_frame_seq`, `hdcp_reauth_seq`, `hdcp_reset_seq`, `hdcp_random_sequence`, `hdcp_regression_sequence`, `hdcp_transaction` |
| SVA（assert / cover property） | 21 / 2 | `a_hdcp_l1_clk`, `a_hdcp_l1_rst`, `a_hdcp_l1_state`, `a_hdcp_l1_valid`, `a_hdcp_trans_idle`, `a_hdcp_trans_ake_init`, `a_hdcp_trans_ake_send_cert`, `a_hdcp_trans_lc_init`, `a_hdcp_trans_ske_send_eks`, `a_hdcp_trans_encrypted`, `a_hdcp_l3_reset_idle`, `a_hdcp_l3_no_stuck` … |
| Covergroups / coverpoints | 3 / 9 | |

## 4. 充分度判定與缺口

判定：**✅ Sufficient**（20 個 check，mutation score 83%）。

未被偵測的 mutant（測試缺口或等價 mutant）：

- `dut_hdcp_receiver_model.sv:23 0 -> 1 [int frame_cnt = 0;]`
- `dut_hdcp_receiver_model.sv:42 0 -> 1 [fcnt <= 0;]`

