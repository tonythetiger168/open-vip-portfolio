# 手寫 UVM 環境在 Verilator 上的首次執行（--smoke）

本文件由 `tools/gen_uvm_smoke_doc.py` 依 `uvm_smoke_report.csv` 產生（`python3 tools/run_uvm_tests.py --smoke`，全部 VIP 約需數小時）。

`tools/run_uvm_tests.py` 的正式 suite（9 個 RAL VIP、71 個產生式 agent）以外，其餘 VIP 的 UVM 環境（driver / monitor / scoreboard / checker / covergroup）之前只做過 pyslang elaboration，從未被模擬器執行。`--smoke` 把 VIP 的全部 `.sv` 以 elab_scan 的順序（package 排在 import 它的檔案之前）、呼叫 `run_test()` 的 module 為 top 建置，執行 base test 的衍生 test（優先選名稱含 VIP 名的那個）。沒有 pass 標記可等，所以 PASS 只代表環境能建置、跑完 sequence 且沒有任何錯誤回報，**不代表** scoreboard 做了有意義的比對。

| 結果 | 意義 | VIP 數 |
|---|---|---|
| PASS | 建置成功、test 跑到結束（時間 > 0），沒有 UVM_ERROR / UVM_FATAL，VIP 自己的 checker 也沒有 warning | 33 |
| WARN | 建置成功、跑完、沒有 UVM_ERROR / UVM_FATAL，但 VIP 自己的 checker / SVA 發出 `UVM_WARNING` | 4 |
| FAIL | 建置成功，但執行時有 UVM_ERROR / UVM_FATAL、逾時，或在時間 0 就結束（test 沒有送出任何流量） | 0 |
| ERROR | Verilator 無法建置（語法、LRM 違規或 Verilator 不支援的寫法） | 0 |
| NONE | 沒有 UVM test（RTL IP 類 VIP，只有 directed testbench） | 0 |

共 37 個 VIP，其中 37 個有 UVM test。

## 失敗原因分類

依第一個錯誤訊息粗分（FAIL / ERROR）：

| 原因 | VIP 數 |
|---|---|

## Verilator 5.054 的已知限制

- `x dist {...}` 被當成硬性約束：先依權重選值，再和 inline `with { x == ... }` 衝突時整個 randomize 失敗（商用模擬器把 dist 當分布，不會失敗）。帶錯誤注入 dist 的 sequence 因此會偶發 `randomize() failed`。directed 的 `with {...}` 會先 `constraint_mode(0)` 關掉該變數的 dist 約束（DDR / LPDDR、SD、eMMC、UFS、UniPro_Mem、MIPI 家族）；JESD204、eCPRI 把 dist 拆成獨立的 `c_*_dist` 約束，彼此相依的錯誤注入用 `(a == 0) -> b dist {...}` 表示。
- 巢狀 rand 物件裡的 dynamic array `size()` 約束解不出來：MIPI、USB、CXL/PCIe、Ethernet/FC 的 sequence 改為直接 randomize `item.txn`。
- 非 rand 陣列的 `size()` 約束會把長度變數釘在目前大小（0）：DDR / HBM / LPDDR 改在 `post_randomize()` 配置 `rdata`。
- 2-state：`'z` 讀成 0，所以用 `=== 1'bz` 判斷「腳位放開」的邏輯永遠不成立。SPI 用 MOSI 的 `'z` 表示 CPHA=1，monitor 與 slave model 改讀新增的 `mosi_oe`（pad output enable）。
- clocking block 的 `inout` 對 `tri` 線不會驅動：ONFI 的 host 改用介面中的 `io_drv` / `io_oe` 驅動 IO 匯流排。
- 在 `$urandom` 上 `case` 時每個 case item 都會重新取值：sequence 先把值存進變數再分派。
- 兩次 clocking 事件之間發出的 drive 會和下一個 `@(cb)` 之後的 drive 落在同一個邊緣，而且順序不保證：driver 在每個 item 開始前先 `@(vif.drv_cb)`（ONFI、HBM）。
- 以 `verilator` 開頭的註解會被當成 pragma（`BADVLTPRAGMA`）。
- covergroup 的 `get_coverage()` 與 enum transition bins 在 5.054 可用，但 transition 的 `[*n]` 重複不支援，需展開寫。

DDR、HBM、LPDDR、UFS、eMMC、SD、ONFI、NVMe、SATA、hbm3 等已有正式 UVM test 的 VIP 由 `tools/run_uvm_tests.py` 的正式 suite 執行（CI），不在本表。

## 逐 VIP 結果

| VIP | Test | 結果 | 原因 | 第一個問題 |
|---|---|---|---|---|
| Bluetooth5-VIP | `bt5_adv_test` | PASS |  |  |
| CAN-VIP | `can_2_0_test` | PASS |  |  |
| CPRI-VIP | `cpri_random_test` | PASS |  |  |
| CXS-VIP | `cxs_random_test` | PASS |  |  |
| eCPRI-VIP | `ecpri_random_test` | PASS |  |  |
| Ethernet-VIP | `net_ethernet_100g_test` | PASS |  |  |
| Ethernet_AVB_TSN-VIP | `avb_stream_test` | PASS |  |  |
| FC-VIP | `net_fc_test` | PASS |  |  |
| FlexRay-VIP | `random_test` | PASS |  |  |
| gddr5-VIP | `gddr5_write_test` | PASS |  |  |
| gddr6-VIP | `gddr6_write_test` | PASS |  |  |
| gddr7-VIP | `gddr7_write_test` | PASS |  |  |
| hbm2-VIP | `hbm2_write_test` | PASS |  |  |
| hbm4-VIP | `hbm4_write_test` | PASS |  |  |
| I2S-VIP | `i2s_random_test` | PASS |  |  |
| I3C-VIP | `i3c_random_test` | PASS |  |  |
| Interlaken-VIP | `intlkn_random_test` | PASS |  |  |
| JESD204-VIP | `jesd204_random_test` | PASS |  |  |
| JTAG-VIP | `jtag_random_test` | PASS |  |  |
| LIN-VIP | `random_test` | PASS |  |  |
| lpddr5-VIP | `lpddr5_write_test` | PASS |  |  |
| lpddr5x-VIP | `lpddr5x_rw_test` | PASS |  |  |
| LPI-VIP | `lpi_random_test` | PASS |  |  |
| LTI-VIP | `lti_random_test` | PASS |  |  |
| SAS-VIP | `sas_random_test` | PASS |  |  |
| Security-VIP | `security_random_test` | PASS |  |  |
| SPI-VIP | `spi_random_test` | PASS |  |  |
| SWD-VIP | `swd_random_test` | PASS |  |  |
| ToggleNAND-VIP | `tnand_random_test` | PASS |  |  |
| TypeC-VIP | `typec_random_test` | PASS |  |  |
| UART-VIP | `uart_random_test` | PASS |  |  |
| USB4-VIP | `usb4_test` | PASS |  |  |
| USB_PD-VIP | `usb_pd_test` | PASS |  |  |
| eUSB2-VIP | `usb_eusb2_test` | WARN |  | rc=0 UVM_ERROR=0 UVM_FATAL=0 VIP_WARNINGS=48612 timeout: UVM_WARNING rtl/sva/eusb2_compliance_checker.sv(76) @ 110000: reporter [EUSB2_L3] Valid dropped before ready failed |
| USB-VIP | `usb_random_regression_test` | WARN |  | rc=0 UVM_ERROR=0 UVM_FATAL=0 VIP_WARNINGS=8134 timeout: UVM_WARNING rtl/sva/usb_compliance_checker.sv(68) @ 106000: reporter [USB_L2] HS preamble failed |
| USB2-VIP | `usb_eusb2_test` | WARN |  | rc=0 UVM_ERROR=0 UVM_FATAL=0 VIP_WARNINGS=1864 timeout: UVM_WARNING vip/base/usb_vip_pkg.sv(937) @ 206000: uvm_test_top.env.sb [SCOREBOARD] Transaction completed with error status |
| USB3-VIP | `usb_random_regression_test` | WARN |  | rc=0 UVM_ERROR=0 UVM_FATAL=0 VIP_WARNINGS=25181 timeout: UVM_WARNING rtl/sva/usb3_compliance_checker.sv(73) @ 102000: reporter [USB3_L2] U1/U2 exit failed |
