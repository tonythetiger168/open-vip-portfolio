# MIPI I3C 測試套件（I3C-VIP）

> 由 `tools/gen_test_suite_docs.py` 依 VIP 內容、`func_report.csv` 與 `mutation_report.csv` 自動產生，請勿手動修改。

## 1. 概要

| 項目 | 內容 |
|---|---|
| 類別 | MIPI |
| 類型 | UVM VIP |
| 功能測試 | 1 個檔案，25 個 check，全部通過 |
| Mutation | 9/11 個 mutant 被偵測（82%） |
| 判定 | **✅ Sufficient**（25 個 check，mutation score 82%） |

## 2. 可執行的功能測試

執行：`python3 tools/run_func_tests.py I3C-VIP`（Icarus Verilog 或 Verilator 5.052）。

### `tb/func_i3c_tb.sv`

結果：**PASS**（verilator，25 checks）

模型合約與範圍（摘自測試檔頭）：

```text
FUNC_SIM: verilator  (vvp 12 segfaults in the target model's ENTDAA ID transmit)

func_i3c_tb.sv -- self-checking functional test for the I3C target model
(i3c_target_model, flattened by smoke/flatten.py), with two targets on an
open-drain SDA bus as in tb/top_tb.sv. Run: python3 tools/run_func_tests.py I3C-VIP

Model contract (from tb/top_tb.sv), I3C SDR subset:
   * broadcast 0x7E/W is ACKed; supported broadcast CCCs: ENEC 0x00,
     DISEC 0x01, RSTDAA 0x06, ENTDAA 0x07, 0x20; others are NACKed.
   * ENTDAA: Sr, 0x7E/R, each unassigned target sends PID[47:0], BCR, DCR
     (8 bytes, a 9th clock after each), losing arbitration on a 0 it did not
     send; the winner ACKs the dynamic address byte {addr, parity}.
   * private write to the dynamic address: first byte < 0x80 sets the
     register pointer, following bytes are stored with auto-increment;
     a first byte >= 0x80 is a direct CCC (ENEC 0x80 / DISEC 0x81).
   * private read returns bytes from the pointer until the master NACKs.
   * a repeated START restarts byte reception: ENTDAA uses Sr before
     0x7E/R, and a private write of the pointer followed by Sr + addr/R
     reads from that pointer.
   * ENEC with ENINT (bit 3) arms an In-Band Interrupt: after 30 idle clocks
     the target pulls SDA low for 3 clocks.
```

| # | Check | 類型 |
|---|---|---|
| 1 | bits clocked without a START are not ACKed | check |
| 2 | broadcast 7E/W and ENTDAA CCC are ACKed | check |
| 3 | 7E/R is ACKed by an unassigned target | check |
| 4 | ENTDAA arbitration: lowest PID wins and its PID/BCR/DCR is read | check |
| 5 | winner ACKs and takes dynamic address 0x0A; loser stays unassigned | check |
| 6 | second ENTDAA assigns 0x0B to the remaining target | check |
| 7 | ENTDAA with every target assigned: 7E/R is NACKed | check |
| 8 | private write to 0x0A: address, pointer and data bytes ACKed | check |
| 9 | private write stores bytes with pointer auto-increment | check |
| 10 | the other target is not written | check |
| 11 | pointer write + Sr + read returns bytes from the pointer until NACK | check |
| 12 | the Sr header byte is not stored as data | check |
| 13 | pointer write, STOP, then a separate read also works | check |
| 14 | transfer after a STOP inside an address byte works | check |
| 15 | transfer after a STOP inside a bit cell works | check |
| 16 | transfer after an empty START-STOP works | check |
| 17 | unassigned address 0x0C is NACKed | check |
| 18 | unsupported broadcast CCC is NACKed | check |
| 19 | ENEC with ENINT is ACKed and enables IBIs | check |
| 20 | no IBI before 30 idle clocks | check |
| 21 | IBI request (SDA pulled low) after the bus is idle | check |
| 22 | IBI pulse released, request cleared | check |
| 23 | DISEC with ENINT disables IBIs | check |
| 24 | RSTDAA clears the dynamic addresses | check |
| 25 | old dynamic address is NACKed after RSTDAA | check |

## 3. UVM 測試平台內容

UVM 測試需商用模擬器（VCS / Xcelium / Questa）執行；開源流程只做 elaboration（L1a）。

| 項目 | 數量 | 名稱 |
|---|---|---|
| UVM tests | 3 | `i3c_base_test`, `i3c_random_test`, `i3c_regression_test` |
| Sequences | 11 | `i3c_base_sequence`, `i3c_entdaa_seq`, `i3c_ccc_bcast_seq`, `i3c_ccc_direct_seq`, `i3c_sdr_write_seq`, `i3c_sdr_read_seq`, `i3c_ibi_seq`, `i3c_error_inject_seq`, `i3c_random_sequence`, `i3c_regression_sequence`, `i3c_transaction` |
| SVA（assert / cover property） | 20 / 2 | `a_i3c_l1_clk`, `a_i3c_l1_rst`, `a_i3c_l1_state`, `a_i3c_l1_valid`, `a_i3c_trans_idle`, `a_i3c_trans_entdaa`, `a_i3c_trans_ccc`, `a_i3c_trans_hdr_ddr`, `a_i3c_trans_sdr`, `a_i3c_trans_ibi`, `a_i3c_l3_reset_idle`, `a_i3c_l3_no_stuck` … |
| Covergroups / coverpoints | 4 / 11 | |

## 4. 充分度判定與缺口

判定：**✅ Sufficient**（25 個 check，mutation score 82%）。

未被偵測的 mutant（測試缺口或等價 mutant）：

- `dut_i3c_target_model.sv:72 1'b1 inverted [else if (vif_sda_i === 1'b1 && pd === 1'b0 && vif_scl_i === ]`
- `dut_i3c_target_model.sv:243 0 -> 1 [else idle_cnt = 0;]`

