# 手寫 UVM 環境在 Verilator 上的首次執行（--smoke）

本文件由 `tools/gen_uvm_smoke_doc.py` 依 `uvm_smoke_report.csv` 產生（`python3 tools/run_uvm_tests.py --smoke`，全部 VIP 約需數小時）。

`tools/run_uvm_tests.py` 的正式 suite（7 個 RAL VIP、47 個產生式 agent）以外，其餘 VIP 的 UVM 環境（driver / monitor / scoreboard / checker / covergroup）之前只做過 pyslang elaboration，從未被模擬器執行。`--smoke` 把 VIP 的全部 `.sv` 以 elab_scan 的順序（package 排在 import 它的檔案之前）、呼叫 `run_test()` 的 module 為 top 建置，執行 base test 的衍生 test（優先選名稱含 VIP 名的那個）。沒有 pass 標記可等，所以 PASS 只代表環境能建置、跑完 sequence 且沒有任何錯誤回報，**不代表** scoreboard 做了有意義的比對。

| 結果 | 意義 | VIP 數 |
|---|---|---|
| PASS | 建置成功、test 跑到結束（時間 > 0），沒有 UVM_ERROR / UVM_FATAL，VIP 自己的 checker 也沒有 warning | 27 |
| WARN | 建置成功、跑完、沒有 UVM_ERROR / UVM_FATAL，但 VIP 自己的 checker / SVA 發出 `UVM_WARNING` | 36 |
| FAIL | 建置成功，但執行時有 UVM_ERROR / UVM_FATAL、逾時，或在時間 0 就結束（test 沒有送出任何流量） | 12 |
| ERROR | Verilator 無法建置（語法、LRM 違規或 Verilator 不支援的寫法） | 0 |
| NONE | 沒有 UVM test（RTL IP 類 VIP，只有 directed testbench） | 2 |

共 77 個 VIP，其中 75 個有 UVM test。

## 失敗原因分類

依第一個錯誤訊息粗分（FAIL / ERROR）：

| 原因 | VIP 數 |
|---|---|
| 建置 | 0 |
| 逾時 / log 洪水 | 0 |
| scoreboard 比對不符 | 12 |
| checker / SVA | 0 |

## Verilator 5.054 的已知限制

- `x dist {...}` 被當成硬性約束：先依權重選值，再和 inline `with { x == ... }` 衝突時整個 randomize 失敗（商用模擬器把 dist 當分布，不會失敗）。帶錯誤注入 dist 的 sequence 因此會偶發 `randomize() failed`。directed 的 `with {...}` 會先 `constraint_mode(0)` 關掉該變數的 dist 約束（DDR / LPDDR、SD、eMMC、UFS、UniPro_Mem、MIPI 家族）；JESD204、eCPRI 把 dist 拆成獨立的 `c_*_dist` 約束，彼此相依的錯誤注入用 `(a == 0) -> b dist {...}` 表示。
- 巢狀 rand 物件裡的 dynamic array `size()` 約束解不出來：MIPI、USB、CXL/PCIe、Ethernet/FC 的 sequence 改為直接 randomize `item.txn`。
- 非 rand 陣列的 `size()` 約束會把長度變數釘在目前大小（0）：DDR / HBM / LPDDR 改在 `post_randomize()` 配置 `rdata`。
- clocking block 的 `inout` 對 `tri` 線不會驅動：ONFI 的 host 改用介面中的 `io_drv` / `io_oe` 驅動 IO 匯流排。
- 在 `$urandom` 上 `case` 時每個 case item 都會重新取值：sequence 先把值存進變數再分派。
- 兩次 clocking 事件之間發出的 drive 會和下一個 `@(cb)` 之後的 drive 落在同一個邊緣，而且順序不保證：driver 在每個 item 開始前先 `@(vif.drv_cb)`（ONFI、HBM）。
- 以 `verilator` 開頭的註解會被當成 pragma（`BADVLTPRAGMA`）。
- covergroup 有取樣但 `get_coverage()` 回傳 0：ONFI 的 100% 覆蓋率門檻在 Verilator 下降為 warning。
- 2-state：`'z` 讀成 0，所以用 `=== 1'bz` 判斷「腳位放開」的邏輯永遠不成立。SPI 用 MOSI 的 `'z` 表示 CPHA=1，monitor 與 slave model 改讀新增的 `mosi_oe`（pad output enable）。

## 逐 VIP 結果

| VIP | Test | 結果 | 原因 | 第一個問題 |
|---|---|---|---|---|
| AVSBus-VIP | `avsbus_random_test` | PASS |  |  |
| CPRI-VIP | `cpri_random_test` | PASS |  |  |
| CSE-VIP | `mipi_cse_test` | PASS |  |  |
| CXL-VIP | `mp_cxl_test` | PASS |  |  |
| DFI-VIP | `dfi_random_test` | PASS |  |  |
| eCPRI-VIP | `ecpri_random_test` | PASS |  |  |
| eMMC-VIP | `emmc_regression_test` | PASS |  |  |
| Ethernet-VIP | `net_ethernet_100g_test` | PASS |  |  |
| Ethernet_AVB_TSN-VIP | `avb_stream_test` | PASS |  |  |
| FC-VIP | `net_fc_test` | PASS |  |  |
| gddr5-VIP | `gddr5_write_test` | PASS |  |  |
| hbm2-VIP | `hbm2_write_test` | PASS |  |  |
| hbm3-VIP | `hbm3_write_test` | PASS |  |  |
| I2S-VIP | `i2s_random_test` | PASS |  |  |
| Interlaken-VIP | `intlkn_random_test` | PASS |  |  |
| LTI-VIP | `lti_random_test` | PASS |  |  |
| PCIe-VIP | `mp_pcie_gen5_test` | PASS |  |  |
| RFFE-VIP | `rffe_random_test` | PASS |  |  |
| SAS-VIP | `sas_random_test` | PASS |  |  |
| SCM_SSD-VIP | `scm_ssd_random_test` | PASS |  |  |
| SD-VIP | `sd_regression_test` | PASS |  |  |
| Security-VIP | `security_random_test` | PASS |  |  |
| UART-VIP | `uart_random_test` | PASS |  |  |
| UFS-VIP | `ufs_regression_test` | PASS |  |  |
| UniPro_Mem-VIP | `memory_coverage_regression_test` | PASS |  |  |
| USB4-VIP | `usb4_test` | PASS |  |  |
| USB_PD-VIP | `usb_pd_test` | PASS |  |  |
| Bluetooth5-VIP | `bt5_adv_test` | WARN |  | rc=0 UVM_ERROR=0 UVM_FATAL=0 VIP_WARNINGS=3366: UVM_WARNING regression/sva/bluetooth5_compliance_checker.sv(59) @ 343750: reporter [BLUETOOTH5_L2] RX CRC OK failed |
| C_PHY-VIP | `mipi_cphy_test` | WARN |  | rc=0 UVM_ERROR=0 UVM_FATAL=0 VIP_WARNINGS=28: UVM_WARNING vip/csi2/csi2_protocol_checker.sv(79) @ 190000: uvm_test_top.env.csi2_chk [CSI2_CHK] CSI-2 payload CRC mismatch |
| CCIX-VIP | `ccix_random_test` | WARN |  | rc=0 UVM_ERROR=0 UVM_FATAL=0 VIP_WARNINGS=5: UVM_WARNING ccix/ccix_driver.svh(59) @ 3085000: uvm_test_top.env.agt.drv [DRV] credit pool did not drain; injecting overflow anyway |
| CSI_2-VIP | `mipi_csi2_test` | WARN |  | rc=0 UVM_ERROR=0 UVM_FATAL=0 VIP_WARNINGS=88: UVM_WARNING rtl/sva/csi_2_compliance_checker.sv(34) @ 202000: reporter [CSI-2_L2] CRC on EOP failed |
| CXS-VIP | `cxs_random_test` | WARN |  | rc=0 UVM_ERROR=0 UVM_FATAL=0 VIP_WARNINGS=4: UVM_WARNING tb/top_tb.sv(84) @ 155000: reporter [DUT] cxs receiver: packet abandoned without cxs_last |
| D_PHY-VIP | `mipi_dphy_test` | WARN |  | rc=0 UVM_ERROR=0 UVM_FATAL=0 VIP_WARNINGS=28: UVM_WARNING vip/csi2/csi2_protocol_checker.sv(79) @ 206000: uvm_test_top.env.csi2_chk [CSI2_CHK] CSI-2 payload CRC mismatch |
| DDR-VIP | `memory_directed_test` | WARN |  | rc=0 UVM_ERROR=0 UVM_FATAL=0 VIP_WARNINGS=2: UVM_WARNING coverage/memory_coverage_pkg.sv(327) @ 39065000: uvm_test_top.env.cov_chk [memory_coverage_report_checker] DDR Coverage below target |
| ddr6-VIP | `ddr6_directed_test` | WARN |  | rc=0 UVM_ERROR=0 UVM_FATAL=0 VIP_WARNINGS=4138: UVM_WARNING ddr6_vip/vip/ddr6/ddr6_data_integrity_checker.sv(16) @ 105000: reporter [DDR6_L2] Burst length 8/16/32 failed |
| ddr7-VIP | `ddr7_directed_test` | WARN |  | rc=0 UVM_ERROR=0 UVM_FATAL=0 VIP_WARNINGS=3760: UVM_WARNING ddr7_vip/vip/ddr7/ddr7_data_integrity_checker.sv(16) @ 105000: reporter [DDR7] Burst length 8/16/32/64 failed |
| DigRF-VIP | `mipi_digrf_test` | WARN |  | rc=0 UVM_ERROR=0 UVM_FATAL=0 VIP_WARNINGS=68: UVM_WARNING rtl/sva/digrf_compliance_checker.sv(59) @ 106000: reporter [DIGRF_L2] Sync valid failed |
| DisplayPort2-VIP | `sata_random_test` | WARN |  | rc=0 UVM_ERROR=0 UVM_FATAL=0 VIP_WARNINGS=633: UVM_WARNING displayport2/displayport2_driver.svh(26) @ 0: uvm_test_top.env.dp2_agt.drv [CONFIG] displayport2 driver: cfg not found, using defaults |
| DPI-VIP | `dpi_random_test` | WARN |  | rc=0 UVM_ERROR=0 UVM_FATAL=0 VIP_WARNINGS=22: UVM_WARNING dpi/dpi_monitor.svh(60) @ 765000: uvm_test_top.env.agt.mon [MON] DE in blanking (line=2 cnt=16) |
| DSI-VIP | `mipi_dsi_test` | WARN |  | rc=0 UVM_ERROR=0 UVM_FATAL=0 VIP_WARNINGS=106: UVM_WARNING rtl/sva/dsi_compliance_checker.sv(34) @ 202000: reporter [DSI_L2] CRC valid failed |
| eUSB2-VIP | `usb_eusb2_test` | WARN |  | rc=0 UVM_ERROR=0 UVM_FATAL=0 VIP_WARNINGS=48612 timeout: UVM_WARNING rtl/sva/eusb2_compliance_checker.sv(76) @ 110000: reporter [EUSB2_L3] Valid dropped before ready failed |
| gddr6-VIP | `gddr6_write_test` | WARN |  | rc=0 UVM_ERROR=0 UVM_FATAL=0 VIP_WARNINGS=494: UVM_WARNING gddr6_vip/vip/gddr6/gddr6_compliance_checker.sv(51) @ 105000: reporter [GDDR6] Speed grade 16Gbps+ failed |
| gddr7-VIP | `gddr7_write_test` | WARN |  | rc=0 UVM_ERROR=0 UVM_FATAL=0 VIP_WARNINGS=430: UVM_WARNING gddr7_vip/vip/gddr7/gddr7_compliance_checker.sv(51) @ 105000: reporter [GDDR7] Speed grade 32Gbps+ failed |
| HBM-VIP | `memory_directed_test` | WARN |  | rc=0 UVM_ERROR=0 UVM_FATAL=0 VIP_WARNINGS=4081: UVM_WARNING env/sva/hbm_compliance_checker.sv(58) @ 165000: reporter [HBM_L3] CKE active failed |
| hbm4-VIP | `hbm4_write_test` | WARN |  | rc=0 UVM_ERROR=0 UVM_FATAL=0 VIP_WARNINGS=494: UVM_WARNING hbm4_vip/vip/hbm4/hbm4_compliance_checker.sv(57) @ 105000: reporter [HBM4] Speed grade 2Gbps+ failed |
| HBM5-VIP | `hbm5_directed_test` | WARN |  | rc=0 UVM_ERROR=0 UVM_FATAL=0 VIP_WARNINGS=8119: UVM_WARNING hbm5_vip/vip/hbm5/hbm5_data_integrity_checker.sv(40) @ 105000: reporter [HBM5] Speed grade 12Gbps+ failed |
| HDMI-VIP | `hdmi_random_test` | WARN |  | rc=0 UVM_ERROR=0 UVM_FATAL=0 VIP_WARNINGS=20: UVM_WARNING hdmi/hdmi_driver.svh(72) @ 1925000: uvm_test_top.env.agt.drv [DRV] hpd dropped mid video data, aborting stream |
| HSI-VIP | `mipi_hsi_test` | WARN |  | rc=0 UVM_ERROR=0 UVM_FATAL=0 VIP_WARNINGS=7: UVM_WARNING rtl/sva/hsi_compliance_checker.sv(70) @ 10514000: reporter [HSI_L2] Error valid failed |
| I2C-VIP | `i2c_random_test` | WARN |  | rc=0 UVM_ERROR=0 UVM_FATAL=0 VIP_WARNINGS=50: UVM_WARNING i2c/i2c_driver.svh(81) @ 935000: uvm_test_top.env.agt.drv [DRV] addr 0x24 NACKed |
| JESD204-VIP | `jesd204_random_test` | WARN |  | rc=0 UVM_ERROR=0 UVM_FATAL=0 VIP_WARNINGS=1: UVM_WARNING jesd204/jesd204_monitor.svh(75) @ 2875000: uvm_test_top.env.agt.mon [MON] ILAS order error: DID in multiframe 3 |
| lpddr5-VIP | `lpddr5_write_test` | WARN |  | rc=0 UVM_ERROR=0 UVM_FATAL=0 VIP_WARNINGS=558: UVM_WARNING lpddr5_vip/vip/lpddr5/lpddr5_compliance_checker.sv(39) @ 105000: reporter [LPDDR5_L2] Burst length 8/16 failed |
| lpddr5x-VIP | `lpddr5x_rw_test` | WARN |  | rc=0 UVM_ERROR=0 UVM_FATAL=0 VIP_WARNINGS=544: UVM_WARNING lpddr5x_vip/vip/lpddr5x/lpddr5x_data_integrity_checker.sv(43) @ 275000: reporter [LPDDR5X_L2] tRP 8-12 cycles failed |
| lpddr7-VIP | `lpddr7_rw_test` | WARN |  | rc=0 UVM_ERROR=0 UVM_FATAL=0 VIP_WARNINGS=1294: UVM_WARNING lpddr7_vip/vip/lpddr7/lpddr7_data_integrity_checker.sv(37) @ 105000: reporter [LPDDR7] Burst length 8/16 failed |
| M_PHY-VIP | `mipi_mphy_test` | WARN |  | rc=0 UVM_ERROR=0 UVM_FATAL=0 VIP_WARNINGS=28: UVM_WARNING vip/csi2/csi2_protocol_checker.sv(79) @ 190000: uvm_test_top.env.csi2_chk [CSI2_CHK] CSI-2 payload CRC mismatch |
| ONFI-VIP | `onfi_deep_test` | WARN |  | rc=0 UVM_ERROR=0 UVM_FATAL=0 VIP_WARNINGS=1: UVM_WARNING coverage/memory_coverage_pkg.sv(158) @ 3762750000: uvm_test_top.env.onfi_cov [onfi_coverage] ONFI Coverage < 100% (not measurable in Verilator) |
| SoundWire-VIP | `soundwire_random_test` | WARN |  | rc=0 UVM_ERROR=0 UVM_FATAL=0 VIP_WARNINGS=2: UVM_WARNING soundwire/soundwire_driver.svh(138) @ 4110000: uvm_test_top.env.agt.drv [DRV] no response from dev 0xf |
| SPI-VIP | `spi_random_test` | WARN |  | rc=0 UVM_ERROR=0 UVM_FATAL=0 VIP_WARNINGS=5: UVM_WARNING spi/spi_driver.svh(78) @ 47405000: uvm_test_top.env.agt.drv [DRV] injecting CS abort after 2 bits |
| SPMI-VIP | `spmi_random_test` | WARN |  | rc=0 UVM_ERROR=0 UVM_FATAL=0 VIP_WARNINGS=37: UVM_WARNING spmi/spmi_driver.svh(89) @ 1235000: uvm_test_top.env.agt.drv [DRV] sa 0x1 NACKed command frame |
| ToggleNAND-VIP | `tnand_random_test` | WARN |  | rc=0 UVM_ERROR=0 UVM_FATAL=0 VIP_WARNINGS=16: UVM_WARNING tb/top_tb.sv(101) @ 14945000: reporter [DUT] cmd 0x80 latched while busy |
| UniPro-VIP | `mipi_unipro_test` | WARN |  | rc=0 UVM_ERROR=0 UVM_FATAL=0 VIP_WARNINGS=28: UVM_WARNING vip/csi2/csi2_protocol_checker.sv(76) @ 194000: uvm_test_top.env.csi2_chk [CSI2_CHK] CSI-2 payload CRC mismatch |
| USB-VIP | `usb_random_regression_test` | WARN |  | rc=0 UVM_ERROR=0 UVM_FATAL=0 VIP_WARNINGS=8134 timeout: UVM_WARNING rtl/sva/usb_compliance_checker.sv(68) @ 106000: reporter [USB_L2] HS preamble failed |
| USB2-VIP | `usb_eusb2_test` | WARN |  | rc=0 UVM_ERROR=0 UVM_FATAL=0 VIP_WARNINGS=1864 timeout: UVM_WARNING vip/base/usb_vip_pkg.sv(937) @ 206000: uvm_test_top.env.sb [SCOREBOARD] Transaction completed with error status |
| USB3-VIP | `usb_random_regression_test` | WARN |  | rc=0 UVM_ERROR=0 UVM_FATAL=0 VIP_WARNINGS=25181 timeout: UVM_WARNING rtl/sva/usb3_compliance_checker.sv(73) @ 102000: reporter [USB3_L2] U1/U2 exit failed |
| CAN-VIP | `can_2_0_test` | FAIL | scoreboard 比對不符 | rc=0 UVM_ERROR=4 UVM_FATAL=0 VIP_WARNINGS=54981: UVM_ERROR env/can_env.sv(63) @ 17065000: uvm_test_top.env.sb [SB] mismatch exp{CAN: type=CAN_2_0 frame=DATA_FRAME id=0x0 ide=0 dlc=0 len=0 rtr=0 fdf=0 brs=0 esi=0 tt=0 err |
| DBI-VIP | `dbi_random_test` | FAIL | scoreboard 比對不符 | rc=0 UVM_ERROR=2 UVM_FATAL=0 VIP_WARNINGS=0: UVM_ERROR env/dbi_env.sv(45) @ 305000: uvm_test_top.env.sb [SB] short WRX not flagged, obs{DBI DBI_CMD_WRITE cmd=0x11 len=0} |
| FlexRay-VIP | `random_test` | FAIL | scoreboard 比對不符 | rc=0 UVM_ERROR=18 UVM_FATAL=0 VIP_WARNINGS=34875: UVM_ERROR env/flexray_env.sv(68) @ 21495000: uvm_test_top.env.sb [SB] mismatch exp{FR: ch=CHANNEL_A seg=STATIC_SEGMENT fid=0 len=0 slot=0 cycle=0 sync=0 start=0 cold=0 wa |
| HDCP-VIP | `hdcp_random_test` | FAIL | scoreboard 比對不符 | rc=0 UVM_ERROR=19 UVM_FATAL=0 VIP_WARNINGS=7: UVM_ERROR env/hdcp_env.sv(67) @ 22775000: uvm_test_top.env.sb [SB] mismatch exp{HDCP aksv=9fb9a6046c bksv=a5c3f01234 riv=e0196b8b431148d4 enc=1 frames=5 err=HDCP_ERR_NONE} ob |
| I3C-VIP | `i3c_random_test` | FAIL | scoreboard 比對不符 | rc=0 UVM_ERROR=51 UVM_FATAL=0 VIP_WARNINGS=41: UVM_ERROR env/i3c_env.sv(84) @ 1355000: uvm_test_top.env.sb [SB] mismatch exp{I3C SDR WR addr=0x20 len=0 nack=1} obs{I3C SDR WR addr=0x00 len=0 nack=1} |
| JTAG-VIP | `jtag_random_test` | FAIL | scoreboard 比對不符 | rc=0 UVM_ERROR=26 UVM_FATAL=0 VIP_WARNINGS=2840: UVM_ERROR env/env_pkg.sv(100) @ 2310000: uvm_test_top.env.jtag_sb [JTAG_SB] mismatch exp{JTAG: op=OP_DR_SCAN ir=0x10 dr_len=103 dr=0xc0853a9f1fd75fb3bfe9441296334044 pause |
| LIN-VIP | `random_test` | FAIL | scoreboard 比對不符 | rc=0 UVM_ERROR=68 UVM_FATAL=0 VIP_WARNINGS=55688: UVM_ERROR common/common_pkg.sv(63) @ 19935000: uvm_test_top.env.agt.chk [PROTOCOL_CHK] [ERROR] PID parity mismatch: expected 01, got 10 (total=1) |
| LPDDR-VIP | `memory_directed_test` | FAIL | scoreboard 比對不符 | rc=0 UVM_ERROR=19 UVM_FATAL=0 VIP_WARNINGS=74: UVM_ERROR env/memory_env_pkg.sv(131) @ 585000: uvm_test_top.env.sb [SB] LPDDR mismatch exp{LPDDR ACT: bank=0 addr=0x7961 bl=8} obs{LPDDR PRE: bank=0 addr=0x0 bl=0} |
| LPI-VIP | `lpi_random_test` | FAIL | scoreboard 比對不符 | rc=0 UVM_ERROR=28 UVM_FATAL=0 VIP_WARNINGS=0: UVM_ERROR env/lpi_env.sv(64) @ 225000: uvm_test_top.env.sb [SB] mismatch exp{LPI request deny=1 -> PENDING (stop=3)} obs{LPI request deny=0 -> ACCEPTED |
| SLIMbus-VIP | `slimbus_random_test` | FAIL | scoreboard 比對不符 | rc=0 UVM_ERROR=49 UVM_FATAL=0 VIP_WARNINGS=2: UVM_ERROR env/slimbus_env.sv(55) @ 1540000: uvm_test_top.env.sb [SB] mismatch exp{SLIMbus SB_CHAN_SETUP la=0x04 ch=11} obs{SLIMbus SB_CHAN_SETUP la=0x00 ch=11} |
| SWD-VIP | `swd_random_test` | FAIL | scoreboard 比對不符 | rc=0 UVM_ERROR=29 UVM_FATAL=0 VIP_WARNINGS=26: UVM_ERROR env/swd_env.sv(107) @ 1125000: uvm_test_top.env.sb [SB] mismatch exp{SWD AP WR a=1 data=0x750d0242 ack=FAULT rdata=0x00000000} obs{SWD AP WR a=1 data=0x7e643f46 ac |
| TypeC-VIP | `typec_random_test` | FAIL | scoreboard 比對不符 | rc=0 UVM_ERROR=5 UVM_FATAL=0 VIP_WARNINGS=4: UVM_ERROR env/typec_env.sv(68) @ 905000: uvm_test_top.env.sb [SB] error-class mismatch exp{TYPEC role=2 rd_rp=0 pd=0 vconn=0 acc=ACC_NONE err=TC_ERR_CC_GLITCH} obs{TYPEC role= |

NVMe-VIP、SATA-VIP 已有 UVM test（`nvme_func_test`、`sata_func_test`，由 `tools/run_uvm_tests.py` 執行；這份快照之後加入）。
