# USB2 測試套件（USB2-VIP）

> 由 `tools/gen_test_suite_docs.py` 依 VIP 內容、`func_report.csv` 與 `mutation_report.csv` 自動產生，請勿手動修改。

## 1. 概要

| 項目 | 內容 |
|---|---|
| 類別 | USB |
| 類型 | UVM VIP |
| 功能測試 | 1 個檔案，15 個 check，全部通過 |
| Mutation | 21/30 個 mutant 被偵測（70%） |
| 判定 | **🟡 Partial**（mutation score 70%） |

## 2. 可執行的功能測試

執行：`python3 tools/run_func_tests.py USB2-VIP`（Icarus Verilog 或 Verilator 5.052）。

### `tb/smoke_func_tb.sv`

結果：**PASS**（iverilog，15 checks）

| # | Check | 類型 |
|---|---|---|
| 1 | reset: DEFAULT state, addr 0, DATA0 expected | check |
| 2 | SOF updates frame_num | check |
| 3 | SOF produces no handshake | check |
| 4 | SETUP resets data toggle to DATA0 | check |
| 5 | SETUP data stage ACKed | check |
| 6 | SET_ADDRESS accepted: addr=5, state=ADDRESS | check |
| 7 | OUT DATA0 ACKed | check |
| 8 | toggle flipped to DATA1 after accept | check |
| 9 | duplicate DATA0 ACKed without toggle flip | check |
| 10 | DATA1 accepted, toggle back to DATA0 | check |
| 11 | bad CRC: NAK, toggle held, nak_count=1 | check |
| 12 | endpoint 0xF STALLs | check |
| 13 | IN token: tx_valid=1, first payload byte | check |
| 14 | host ACK consumed data: tx_valid cleared, toggle flipped | check |
| 15 | foreign address ignored (state untouched) | check |

## 3. UVM 測試平台內容

UVM 測試需商用模擬器（VCS / Xcelium / Questa）執行；開源流程只做 elaboration（L1a）。

| 項目 | 數量 | 名稱 |
|---|---|---|
| UVM tests | 10 | `usb_base_test`, `usb_random_regression_test`, `usb_directed_test`, `usb_hs_test`, `usb_ss_test`, `usb_ssp_test`, `usb_ss20_test`, `usb4_test`, `usb_eusb2_test`, `usb_pd_test` |
| Sequences | 12 | `usb_base_sequence`, `usb_normal_seq`, `usb_error_inject_seq`, `usb_reset_seq`, `usb_back_to_back_seq`, `usb_stress_seq`, `usb_corner_seq`, `usb_sof_seq`, `usb_random_sequence`, `usb_regression_sequence`, `usb_directed_regression_sequence`, `usb_sequence_item` |
| SVA（assert / cover property） | 27 / 19 | `assert_p_usb2_linestate_j`, `cover_p_usb2_linestate_j`, `assert_p_usb2_rxactive`, `cover_p_usb2_rxactive`, `assert_p_usb2_op_mode`, `cover_p_usb2_op_mode`, `assert_p_usb2_xcvr_select`, `cover_p_usb2_xcvr_select`, `assert_p_usb2_utmi_txvalid`, `cover_p_usb2_utmi_txvalid`, `assert_p_usb2_linestate_se0`, `cover_p_usb2_linestate_se0` … |
| Covergroups / coverpoints | 14 / 49 | |

## 4. 充分度判定與缺口

判定：**🟡 Partial**（mutation score 70%）。

未被偵測的 mutant（測試缺口或等價 mutant）：

- `dut_usb2_smoke_model.sv:58 == flipped [((rx_addr == 7'h00) && (dev_addr == 7'h00));]`
- `dut_usb2_smoke_model.sv:58 == flipped [((rx_addr == 7'h00) && (dev_addr == 7'h00));]`
- `dut_usb2_smoke_model.sv:58 && flipped [((rx_addr == 7'h00) && (dev_addr == 7'h00));]`
- `dut_usb2_smoke_model.sv:60 && flipped [wire pid_is_data  = pid_valid && (rx_pid[1:0] == PID_CLS_DAT]`
- `dut_usb2_smoke_model.sv:61 && flipped [wire pid_is_hs    = pid_valid && (rx_pid[1:0] == PID_CLS_HS)]`
- `dut_usb2_smoke_model.sv:70 1'b0 inverted [setup_pending <= 1'b0;]`
- `dut_usb2_smoke_model.sv:77 1'b0 inverted [tx_valid      <= 1'b0;]`
- `dut_usb2_smoke_model.sv:126 1'b0 inverted [setup_pending <= 1'b0;]`
- `dut_usb2_smoke_model.sv:150 1'b0 inverted [tx_valid <= 1'b0;]`

