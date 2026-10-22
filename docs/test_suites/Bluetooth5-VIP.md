# Bluetooth5 測試套件（Bluetooth5-VIP）

> 由 `tools/gen_test_suite_docs.py` 依 VIP 內容、`func_report.csv` 與 `mutation_report.csv` 自動產生，請勿手動修改。

## 1. 概要

| 項目 | 內容 |
|---|---|
| 類別 | Storage/Debug |
| 類型 | UVM VIP |
| 功能測試 | 1 個檔案，26 個 check，全部通過 |
| Mutation | 11/11 個 mutant 被偵測（100%） |
| 判定 | **✅ Sufficient**（26 個 check，mutation score 100%） |

## 2. 可執行的功能測試

執行：`python3 tools/run_func_tests.py Bluetooth5-VIP`（Icarus Verilog 或 Verilator 5.052）。

### `tb/func_bluetooth5_tb.sv`

結果：**PASS**（verilator，26 checks）

模型合約與範圍（摘自測試檔頭）：

```text
func_bluetooth5_tb.sv -- self-checking functional test for the Bluetooth LE
peer model (bluetooth5_dut in top/top_tb.sv, flattened by smoke/flatten.py).
Run: python3 tools/run_func_tests.py Bluetooth5-VIP

Model contract (from top/top_tb.sv): the peer listens (rx_en) and collects
air bytes while rx_valid is high: preamble, access address (4 bytes, LSB
first), PDU header byte 0, length, payload. When rx_valid drops it decodes
a packet of 7 or more bytes: access_addr, length, and on advertising
channels 37-39 adv_type = header[2:0], on data channels LLID = header[1:0],
NESN = header[2], SN = header[3], MD = header[4]. After a 5-clock
turnaround (rx_en low) it transmits the received bytes back with tx_en and
tx_valid, then listens again.
Known defect (XFAIL): tx_valid rises one clock before the first echoed
byte, so the echo starts with a stale byte (the last byte of the previous
transmission, 0x00 after reset).
```

| # | Check | 類型 |
|---|---|---|
| 1 | advertising access address 0x8E89BED6 after reset | check |
| 2 | LE 1M PHY, listening | check |
| 3 | receiver off during the turnaround | check |
| 4 | transmit starts after a 5-clock turnaround (got %0d) | check |
| 5 | access address and length decoded | check |
| 6 | advertising PDU type decoded on channel 37 | check |
| 7 | packet echoed after the leading byte (%0d bytes) | check |
| 8 | echo starts with the first received byte | XFAIL（模型缺陷） |
| 9 | listening again after the echo | check |
| 10 | SCAN_REQ type and length decoded on channel 39 | check |
| 11 | stale leading byte is the previous packet's last byte | check |
| 12 | data-channel fields untouched on advertising channels | check |
| 13 | connection access address decoded | check |
| 14 | LLID/NESN/SN/MD decoded on a data channel | check |
| 15 | advertising type untouched on data channels | check |
| 16 | data PDU echoed | check |
| 17 | empty PDU: SN=1, length 0 | check |
| 18 | empty PDU echoed | check |
| 19 | 251-byte payload received and echoed | check |
| 20 | packet shorter than 7 bytes leaves the decoded header | check |
| 21 | runt packet still echoed | check |
| 22 | 6-byte packet: header not decoded, echoed | check |
| 23 | single-byte packet echoed | check |
| 24 | never transmitting and receiving at once | check |
| 25 | reset clears the buffer and header | check |
| 26 | reset clears the enables and the decoded header fields | check |

## 3. UVM 測試平台內容

UVM 測試需商用模擬器（VCS / Xcelium / Questa）執行；開源流程只做 elaboration（L1a）。

| 項目 | 數量 | 名稱 |
|---|---|---|
| UVM tests | 8 | `bt5_base_test`, `bt5_adv_test`, `bt5_data_test`, `bt5_phy_test`, `bt5_error_test`, `bt5_corner_test`, `bt5_regression_test`, `full_regression_test` |
| Sequences | 17 | `bluetooth5_base_sequence`, `bluetooth5_random_sequence`, `bluetooth5_adv_sequence`, `bluetooth5_data_sequence`, `bluetooth5_phy_sequence`, `bt5_base_sequence`, `bt5_random_sequence`, `bt5_adv_sequence`, `bt5_data_sequence`, `bt5_phy_update_sequence`, `bt5_error_inject_sequence`, `bt5_back_to_back_sequence`, `bt5_corner_sequence`, `bt5_reset_sequence`, `bt5_regression_sequence`, `bluetooth5_transaction`, `base_tx` |
| SVA（assert / cover property） | 32 / 32 | `assert_p_bt_phy`, `cover_p_bt_phy`, `assert_p_bt_channel`, `cover_p_bt_channel`, `assert_p_bt_adv_type`, `cover_p_bt_adv_type`, `assert_p_bt_llid`, `cover_p_bt_llid`, `assert_p_bt_crc`, `cover_p_bt_crc`, `assert_p_bt_access_addr`, `cover_p_bt_access_addr` … |
| Covergroups / coverpoints | 3 / 15 | |

## 4. 充分度判定與缺口

判定：**✅ Sufficient**（26 個 check，mutation score 100%）。

DUT 模型缺陷（XFAIL check，修好模型後會變成 XPASS 提醒移除標記）：

- echo starts with the first received byte

