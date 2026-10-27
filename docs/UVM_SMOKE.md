# 手寫 UVM 環境在 Verilator 上的首次執行（--smoke）

本文件由 `tools/gen_uvm_smoke_doc.py` 依 `uvm_smoke_report.csv` 產生（`python3 tools/run_uvm_tests.py --smoke`，全部 VIP 約需數小時）。

`tools/run_uvm_tests.py` 的正式 suite（5 個 RAL VIP、29 個產生式 agent）以外，其餘 VIP 的 UVM 環境（driver / monitor / scoreboard / checker / covergroup）之前只做過 pyslang elaboration，從未被模擬器執行。`--smoke` 把 VIP 的全部 `.sv` 以 elab_scan 的順序（package 排在 import 它的檔案之前）、呼叫 `run_test()` 的 module 為 top 建置，執行 base test 的衍生 test（優先選名稱含 VIP 名的那個）。沒有 pass 標記可等，所以 PASS 只代表環境能建置、跑完 sequence 且沒有任何錯誤回報，**不代表** scoreboard 做了有意義的比對。

| 結果 | 意義 | VIP 數 |
|---|---|---|
| PASS | 建置成功、test 跑到結束（時間 > 0），沒有 UVM_ERROR / UVM_FATAL，VIP 自己的 checker 也沒有 warning | 7 |
| WARN | 建置成功、跑完、沒有 UVM_ERROR / UVM_FATAL，但 VIP 自己的 checker / SVA 發出 `UVM_WARNING` | 10 |
| FAIL | 建置成功，但執行時有 UVM_ERROR / UVM_FATAL、逾時，或在時間 0 就結束（test 沒有送出任何流量） | 59 |
| ERROR | Verilator 無法建置（語法、LRM 違規或 Verilator 不支援的寫法） | 1 |
| NONE | 沒有 UVM test（RTL IP 類 VIP，只有 directed testbench） | 24 |

共 101 個 VIP，其中 77 個有 UVM test。

## 失敗原因分類

依第一個錯誤訊息粗分（FAIL / ERROR）：

| 原因 | VIP 數 |
|---|---|
| 建置 | 1 |
| 逾時 / log 洪水 | 9 |
| randomize 失敗 | 13 |
| 缺 vif / config | 2 |
| scoreboard 比對不符 | 24 |
| checker / SVA | 11 |

## Verilator 5.052 的已知限制

- `x dist {...}` 被當成硬性約束：先依權重選值，再和 inline `with { x == ... }` 衝突時整個 randomize 失敗（商用模擬器把 dist 當分布，不會失敗）。帶錯誤注入 dist 的 sequence 因此會偶發 `randomize() failed`；DDR / LPDDR 的固定命令已用 `c_cmd_dist.constraint_mode(0)` 繞過，其餘 VIP 列為已知限制。
- 巢狀 rand 物件裡的 dynamic array `size()` 約束解不出來：MIPI、USB、CXL/PCIe、Ethernet/FC 的 sequence 改為直接 randomize `item.txn`。
- 非 rand 陣列的 `size()` 約束會把長度變數釘在目前大小（0）：DDR / HBM / LPDDR 改在 `post_randomize()` 配置 `rdata`。

## 逐 VIP 結果

| VIP | Test | 結果 | 原因 | 第一個問題 |
|---|---|---|---|---|
| AVSBus-VIP | `avsbus_random_test` | PASS |  |  |
| CPRI-VIP | `cpri_random_test` | PASS |  |  |
| DFI-VIP | `dfi_random_test` | PASS |  |  |
| I2S-VIP | `i2s_random_test` | PASS |  |  |
| Interlaken-VIP | `intlkn_random_test` | PASS |  |  |
| LTI-VIP | `lti_random_test` | PASS |  |  |
| RFFE-VIP | `rffe_random_test` | PASS |  |  |
| Bluetooth5-VIP | `bt5_adv_test` | WARN |  | rc=0 UVM_ERROR=0 UVM_FATAL=0 VIP_WARNINGS=3366: UVM_WARNING regression/sva/bluetooth5_compliance_checker.sv(59) @ 343750: reporter [BLUETOOTH5_L2] RX CRC OK failed |
| CCIX-VIP | `ccix_random_test` | WARN |  | rc=0 UVM_ERROR=0 UVM_FATAL=0 VIP_WARNINGS=5: UVM_WARNING ccix/ccix_driver.svh(59) @ 3085000: uvm_test_top.env.agt.drv [DRV] credit pool did not drain; injecting overflow anyway |
| CXS-VIP | `cxs_random_test` | WARN |  | rc=0 UVM_ERROR=0 UVM_FATAL=0 VIP_WARNINGS=4: UVM_WARNING tb/top_tb.sv(84) @ 155000: reporter [DUT] cxs receiver: packet abandoned without cxs_last |
| DDR-VIP | `memory_directed_test` | WARN |  | rc=0 UVM_ERROR=0 UVM_FATAL=0 VIP_WARNINGS=2: UVM_WARNING coverage/memory_coverage_pkg.sv(327) @ 39065000: uvm_test_top.env.cov_chk [memory_coverage_report_checker] DDR Coverage below target |
| DisplayPort2-VIP | `sata_random_test` | WARN |  | rc=0 UVM_ERROR=0 UVM_FATAL=0 VIP_WARNINGS=633: UVM_WARNING displayport2/displayport2_driver.svh(26) @ 0: uvm_test_top.env.dp2_agt.drv [CONFIG] displayport2 driver: cfg not found, using defaults |
| DPI-VIP | `dpi_random_test` | WARN |  | rc=0 UVM_ERROR=0 UVM_FATAL=0 VIP_WARNINGS=22: UVM_WARNING dpi/dpi_monitor.svh(60) @ 765000: uvm_test_top.env.agt.mon [MON] DE in blanking (line=2 cnt=16) |
| HDMI-VIP | `hdmi_random_test` | WARN |  | rc=0 UVM_ERROR=0 UVM_FATAL=0 VIP_WARNINGS=20: UVM_WARNING hdmi/hdmi_driver.svh(72) @ 1925000: uvm_test_top.env.agt.drv [DRV] hpd dropped mid video data, aborting stream |
| I2C-VIP | `i2c_random_test` | WARN |  | rc=0 UVM_ERROR=0 UVM_FATAL=0 VIP_WARNINGS=50: UVM_WARNING i2c/i2c_driver.svh(81) @ 935000: uvm_test_top.env.agt.drv [DRV] addr 0x24 NACKed |
| SoundWire-VIP | `soundwire_random_test` | WARN |  | rc=0 UVM_ERROR=0 UVM_FATAL=0 VIP_WARNINGS=2: UVM_WARNING soundwire/soundwire_driver.svh(138) @ 4110000: uvm_test_top.env.agt.drv [DRV] no response from dev 0xf |
| SPMI-VIP | `spmi_random_test` | WARN |  | rc=0 UVM_ERROR=0 UVM_FATAL=0 VIP_WARNINGS=37: UVM_WARNING spmi/spmi_driver.svh(89) @ 1235000: uvm_test_top.env.agt.drv [DRV] sa 0x1 NACKed command frame |
| C_PHY-VIP | `mipi_cphy_test` | FAIL | checker / SVA | rc=0 UVM_ERROR=58 UVM_FATAL=0 VIP_WARNINGS=28: UVM_ERROR vip/cphy/cphy_protocol_checker.sv(54) @ 186000: uvm_test_top.env.cphy_chk [CPHY_CHK] C-PHY triplet did not toggle |
| CAN-VIP | `can_2_0_test` | FAIL | scoreboard 比對不符 | rc=0 UVM_ERROR=4 UVM_FATAL=0 VIP_WARNINGS=54981: UVM_ERROR env/can_env.sv(63) @ 17065000: uvm_test_top.env.sb [SB] mismatch exp{CAN: type=CAN_2_0 frame=DATA_FRAME id=0x0 ide=0 dlc=0 len=0 rtr=0 fdf=0 brs=0 esi=0 tt=0 err |
| CSE-VIP | `mipi_cse_test` | FAIL | scoreboard 比對不符 | rc=0 UVM_ERROR=19 UVM_FATAL=1 VIP_WARNINGS=0: UVM_ERROR vip/base/mipi_vip_pkg.sv(563) @ 130000: uvm_test_top.env.sb [mipi_sb] CSE SB: observed MIPI_CSE pkt=PKT_FS vc=0 wc=0 cse_cmd=0 op=0x00 resp=0x00 with no expected it |
| CSI_2-VIP | `mipi_csi2_test` | FAIL | randomize 失敗 | rc=0 UVM_ERROR=2 UVM_FATAL=0 VIP_WARNINGS=90: UVM_ERROR vip/base/mipi_vip_pkg.sv(709) @ 1646000: uvm_test_top.env.agt.sqr@@cor [RANDFAIL] randomize() failed |
| CXL-VIP | `mp_cxl_test` | FAIL | checker / SVA | rc=0 UVM_ERROR=2261 UVM_FATAL=0 VIP_WARNINGS=51990: UVM_ERROR vip/cxl/cxl_protocol_checker.sv(62) @ 3754000: uvm_test_top.env.cxl_chk [CXL_CHK] SOP asserted in the middle of a TLP (total=1) |
| D_PHY-VIP | `mipi_dphy_test` | FAIL | randomize 失敗 | rc=0 UVM_ERROR=2 UVM_FATAL=0 VIP_WARNINGS=28: UVM_ERROR vip/base/mipi_vip_pkg.sv(709) @ 1646000: uvm_test_top.env.agt.sqr@@cor [RANDFAIL] randomize() failed |
| DBI-VIP | `dbi_random_test` | FAIL | scoreboard 比對不符 | rc=0 UVM_ERROR=2 UVM_FATAL=0 VIP_WARNINGS=0: UVM_ERROR env/dbi_env.sv(45) @ 305000: uvm_test_top.env.sb [SB] short WRX not flagged, obs{DBI DBI_CMD_WRITE cmd=0x11 len=0} |
| ddr6-VIP | `ddr6_directed_test` | FAIL | checker / SVA | rc=0 UVM_ERROR=200 UVM_FATAL=0 VIP_WARNINGS=4181: UVM_ERROR ddr6_vip/sva/ddr6_compliance_checker.sv(82) @ 155000: reporter [SVA_L2] DDR6: command issued with CKE low |
| ddr7-VIP | `ddr7_directed_test` | FAIL | checker / SVA | rc=0 UVM_ERROR=251 UVM_FATAL=0 VIP_WARNINGS=3801: UVM_ERROR ddr7_vip/sva/ddr7_compliance_checker.sv(82) @ 155000: reporter [SVA_L2] DDR7: command issued with CKE low |
| DigRF-VIP | `mipi_digrf_test` | FAIL | checker / SVA | rc=1 UVM_ERROR=0 UVM_FATAL=0 VIP_WARNINGS=0: UVM_ERROR vip/digrf/digrf_protocol_checker.sv(27) @ 106000: reporter [DIGRF_CHK] DigRF frame sync without valid: %Error: rtl/mipi_vip_if.sv:193: Verilog $stop |
| DSI-VIP | `mipi_dsi_test` | FAIL | randomize 失敗 | rc=0 UVM_ERROR=2 UVM_FATAL=0 VIP_WARNINGS=106: UVM_ERROR vip/base/mipi_vip_pkg.sv(709) @ 1646000: uvm_test_top.env.agt.sqr@@cor [RANDFAIL] randomize() failed |
| eCPRI-VIP | `ecpri_random_test` | FAIL | randomize 失敗 | rc=0 UVM_ERROR=2 UVM_FATAL=0 VIP_WARNINGS=0: UVM_ERROR ecpri/ecpri_sequences.svh(18) @ 4610000: uvm_test_top.env.agt.sqr@@seq [RANDFAIL] randomize() failed |
| eMMC-VIP | `emmc_regression_test` | FAIL | randomize 失敗 | rc=0 UVM_ERROR=179 UVM_FATAL=0 VIP_WARNINGS=112: UVM_ERROR emmc/emmc_pkg.sv(528) @ 100000: uvm_test_top.env.emmc_ag.sqr@@i [emmc_init_seq] Rand failed |
| Ethernet-VIP | `net_ethernet_100g_test` | FAIL | 缺 vif / config | rc=0 UVM_ERROR=0 UVM_FATAL=1 VIP_WARNINGS=0: UVM_FATAL tests/net_base_test.sv(38) @ 0: uvm_test_top [NOVIF] virtual interface eth_100g_vif not found |
| Ethernet_AVB_TSN-VIP | `avb_stream_test` | FAIL | 逾時 / log 洪水 | rc=125 UVM_ERROR=0 UVM_FATAL=0 VIP_WARNINGS=41291 log flood (>512 MB, killed): UVM_ERROR common/common_pkg.sv(72) @ 228000: uvm_test_top.env.agt.chk [PROTOCOL_CHK] [ERROR] Source address is multicast (total=1) |
| eUSB2-VIP | `usb_eusb2_test` | FAIL | 逾時 / log 洪水 | rc=0 UVM_ERROR=74068 UVM_FATAL=0 VIP_WARNINGS=36661 timeout: UVM_ERROR rtl/usb_vip_if.sv(295) @ 114000: reporter [USB_IF] MAC SOP-EOP alignment violation |
| FC-VIP | `net_fc_test` | FAIL | 缺 vif / config | rc=0 UVM_ERROR=0 UVM_FATAL=1 VIP_WARNINGS=0: UVM_FATAL tests/net_base_test.sv(38) @ 0: uvm_test_top [NOVIF] virtual interface fc_vif not found |
| FlexRay-VIP | `random_test` | FAIL | scoreboard 比對不符 | rc=0 UVM_ERROR=18 UVM_FATAL=0 VIP_WARNINGS=34875: UVM_ERROR env/flexray_env.sv(68) @ 21495000: uvm_test_top.env.sb [SB] mismatch exp{FR: ch=CHANNEL_A seg=STATIC_SEGMENT fid=0 len=0 slot=0 cycle=0 sync=0 start=0 cold=0 wa |
| gddr5-VIP | `gddr5_write_test` | FAIL | scoreboard 比對不符 | rc=0 UVM_ERROR=66 UVM_FATAL=0 VIP_WARNINGS=0: UVM_ERROR gddr5_vip/env/gddr5_env.sv(47) @ 330000: uvm_test_top.env.sb [SB] mismatch exp{cmd=GDDR5_CMD_WR bg=0 ba=2 stack=0 row=0xf42f col=0x008 data=0x45af9baedd5f5eba rdata |
| gddr6-VIP | `gddr6_write_test` | FAIL | scoreboard 比對不符 | rc=0 UVM_ERROR=66 UVM_FATAL=0 VIP_WARNINGS=494: UVM_ERROR gddr6_vip/env/gddr6_env.sv(47) @ 310000: uvm_test_top.env.sb [SB] mismatch exp{cmd=GDDR6_CMD_WR bg=0 ba=2 stack=0 row=0xf42f col=0x008 data=0x45af9baedd5f5eba rda |
| gddr7-VIP | `gddr7_write_test` | FAIL | scoreboard 比對不符 | rc=0 UVM_ERROR=66 UVM_FATAL=0 VIP_WARNINGS=430: UVM_ERROR gddr7_vip/env/gddr7_env.sv(47) @ 290000: uvm_test_top.env.sb [SB] mismatch exp{cmd=GDDR7_CMD_WR bg=0 ba=2 stack=0 row=0xf42f col=0x008 data=0x45af9baedd5f5eba rda |
| HBM-VIP | `memory_directed_test` | FAIL | scoreboard 比對不符 | rc=0 UVM_ERROR=40 UVM_FATAL=0 VIP_WARNINGS=3327: UVM_ERROR env/memory_env_pkg.sv(131) @ 1545000: uvm_test_top.env.sb [SB] HBM mismatch exp{HBM ACT: ch=1 bank=2 addr=0xa0eb bl=8} obs{HBM PRE: ch=7 bank=2 addr=0x0 bl=0} |
| hbm2-VIP | `hbm2_write_test` | FAIL | scoreboard 比對不符 | rc=0 UVM_ERROR=66 UVM_FATAL=0 VIP_WARNINGS=0: UVM_ERROR hbm2_vip/env/hbm2_env.sv(47) @ 370000: uvm_test_top.env.sb [SB] mismatch exp{cmd=HBM2_CMD_WR bg=0 ba=2 stack=0 row=0xf42f col=0x008 data=0x45af9baedd5f5eba rdata=0x |
| hbm3-VIP | `hbm3_write_test` | FAIL | scoreboard 比對不符 | rc=0 UVM_ERROR=66 UVM_FATAL=0 VIP_WARNINGS=0: UVM_ERROR hbm3_vip/env/hbm3_env.sv(47) @ 350000: uvm_test_top.env.sb [SB] mismatch exp{cmd=HBM3_CMD_WR bg=0 ba=2 stack=0 row=0xf42f col=0x008 data=0x45af9baedd5f5eba rdata=0x |
| hbm4-VIP | `hbm4_write_test` | FAIL | scoreboard 比對不符 | rc=0 UVM_ERROR=66 UVM_FATAL=0 VIP_WARNINGS=494: UVM_ERROR hbm4_vip/env/hbm4_env.sv(47) @ 310000: uvm_test_top.env.sb [SB] mismatch exp{cmd=HBM4_CMD_WR bg=0 ba=2 stack=0 row=0xf42f col=0x008 data=0x45af9baedd5f5eba rdata= |
| HBM5-VIP | `hbm5_directed_test` | FAIL | checker / SVA | rc=0 UVM_ERROR=230 UVM_FATAL=0 VIP_WARNINGS=8119: UVM_ERROR hbm5_vip/sva/hbm5_compliance_checker.sv(82) @ 155000: reporter [SVA_L2] HBM5: command issued with CKE low |
| HDCP-VIP | `hdcp_random_test` | FAIL | scoreboard 比對不符 | rc=0 UVM_ERROR=19 UVM_FATAL=0 VIP_WARNINGS=7: UVM_ERROR env/hdcp_env.sv(67) @ 22775000: uvm_test_top.env.sb [SB] mismatch exp{HDCP aksv=9fb9a6046c bksv=a5c3f01234 riv=e0196b8b431148d4 enc=1 frames=5 err=HDCP_ERR_NONE} ob |
| HSI-VIP | `mipi_hsi_test` | FAIL | checker / SVA | rc=0 UVM_ERROR=39 UVM_FATAL=0 VIP_WARNINGS=5: UVM_ERROR vip/csi2/csi2_protocol_checker.sv(27) @ 306000: reporter [CSI2_CHK] CSI-2 VC out of range |
| HSI-VIP | `mipi_hsi_test` | FAIL | checker / SVA | rc=0 UVM_ERROR=39 UVM_FATAL=0 VIP_WARNINGS=5: UVM_ERROR vip/csi2/csi2_protocol_checker.sv(27) @ 306000: reporter [CSI2_CHK] CSI-2 VC out of range |
| I3C-VIP | `i3c_random_test` | FAIL | scoreboard 比對不符 | rc=0 UVM_ERROR=51 UVM_FATAL=0 VIP_WARNINGS=41: UVM_ERROR env/i3c_env.sv(84) @ 1355000: uvm_test_top.env.sb [SB] mismatch exp{I3C SDR WR addr=0x20 len=0 nack=1} obs{I3C SDR WR addr=0x00 len=0 nack=1} |
| JESD204-VIP | `jesd204_random_test` | FAIL | randomize 失敗 | rc=0 UVM_ERROR=44 UVM_FATAL=0 VIP_WARNINGS=1: UVM_ERROR jesd204/jesd204_sequences.svh(18) @ 415000: uvm_test_top.env.agt.sqr@@seq [RANDFAIL] randomize() failed |
| JTAG-VIP | `jtag_random_test` | FAIL | scoreboard 比對不符 | rc=0 UVM_ERROR=26 UVM_FATAL=0 VIP_WARNINGS=2840: UVM_ERROR env/env_pkg.sv(100) @ 2310000: uvm_test_top.env.jtag_sb [JTAG_SB] mismatch exp{JTAG: op=OP_DR_SCAN ir=0x10 dr_len=103 dr=0xc0853a9f1fd75fb3bfe9441296334044 pause |
| LIN-VIP | `random_test` | FAIL | scoreboard 比對不符 | rc=0 UVM_ERROR=68 UVM_FATAL=0 VIP_WARNINGS=55688: UVM_ERROR common/common_pkg.sv(63) @ 19935000: uvm_test_top.env.agt.chk [PROTOCOL_CHK] [ERROR] PID parity mismatch: expected 01, got 10 (total=1) |
| LPDDR-VIP | `memory_directed_test` | FAIL | scoreboard 比對不符 | rc=0 UVM_ERROR=19 UVM_FATAL=0 VIP_WARNINGS=74: UVM_ERROR env/memory_env_pkg.sv(131) @ 585000: uvm_test_top.env.sb [SB] LPDDR mismatch exp{LPDDR ACT: bank=0 addr=0x7961 bl=8} obs{LPDDR PRE: bank=0 addr=0x0 bl=0} |
| lpddr5-VIP | `lpddr5_write_test` | FAIL | scoreboard 比對不符 | rc=0 UVM_ERROR=66 UVM_FATAL=0 VIP_WARNINGS=558: UVM_ERROR lpddr5_vip/env/lpddr5_env.sv(47) @ 330000: uvm_test_top.env.sb [SB] mismatch exp{cmd=LPDDR5_CMD_WR bg=0 ba=2 stack=0 row=0xf42f col=0x008 data=0x45af9baedd5f5eba  |
| lpddr5x-VIP | `lpddr5x_rw_test` | FAIL | checker / SVA | rc=0 UVM_ERROR=301 UVM_FATAL=0 VIP_WARNINGS=344: UVM_ERROR lpddr5x_vip/sva/lpddr5x_compliance_checker.sv(147) @ 215000: reporter [SVA_L4] lpddr5x: RD/WR without preceding ACT |
| lpddr7-VIP | `lpddr7_rw_test` | FAIL | checker / SVA | rc=0 UVM_ERROR=301 UVM_FATAL=0 VIP_WARNINGS=1244: UVM_ERROR lpddr7_vip/sva/lpddr7_compliance_checker.sv(147) @ 215000: reporter [SVA_L4] lpddr7: RD/WR without preceding ACT |
| LPI-VIP | `lpi_random_test` | FAIL | scoreboard 比對不符 | rc=0 UVM_ERROR=28 UVM_FATAL=0 VIP_WARNINGS=0: UVM_ERROR env/lpi_env.sv(64) @ 225000: uvm_test_top.env.sb [SB] mismatch exp{LPI request deny=1 -> PENDING (stop=3)} obs{LPI request deny=0 -> ACCEPTED  |
| M_PHY-VIP | `mipi_mphy_test` | FAIL | randomize 失敗 | rc=0 UVM_ERROR=2 UVM_FATAL=0 VIP_WARNINGS=28: UVM_ERROR vip/base/mipi_vip_pkg.sv(709) @ 1190000: uvm_test_top.env.agt.sqr@@cor [RANDFAIL] randomize() failed |
| M_PHY-VIP | `mipi_mphy_test` | FAIL | randomize 失敗 | rc=0 UVM_ERROR=2 UVM_FATAL=0 VIP_WARNINGS=28: UVM_ERROR vip/base/mipi_vip_pkg.sv(709) @ 1190000: uvm_test_top.env.agt.sqr@@cor [RANDFAIL] randomize() failed |
| PCIe-VIP | `mp_pcie_gen5_test` | FAIL | checker / SVA | rc=0 UVM_ERROR=11071 UVM_FATAL=0 VIP_WARNINGS=14654: UVM_ERROR vip/pcie/pcie_protocol_checker.sv(64) @ 3754000: uvm_test_top.env.pcie_chk [PCIE_CHK] SOP asserted in the middle of a TLP (total=1) |
| SAS-VIP | `sas_random_test` | FAIL | 逾時 / log 洪水 | rc=124 UVM_ERROR=0 UVM_FATAL=0 VIP_WARNINGS=0 timeout |
| SD-VIP | `sd_regression_test` | FAIL | randomize 失敗 | rc=0 UVM_ERROR=180 UVM_FATAL=0 VIP_WARNINGS=98: UVM_ERROR sd/sd_pkg.sv(543) @ 100000: uvm_test_top.env.sd_ag.sqr@@i [sd_init_seq] Rand failed |
| Security-VIP | `security_random_test` | FAIL | 逾時 / log 洪水 | rc=124 UVM_ERROR=0 UVM_FATAL=0 VIP_WARNINGS=0 timeout |
| SLIMbus-VIP | `slimbus_random_test` | FAIL | scoreboard 比對不符 | rc=0 UVM_ERROR=49 UVM_FATAL=0 VIP_WARNINGS=2: UVM_ERROR env/slimbus_env.sv(55) @ 1540000: uvm_test_top.env.sb [SB] mismatch exp{SLIMbus SB_CHAN_SETUP la=0x04 ch=11} obs{SLIMbus SB_CHAN_SETUP la=0x00 ch=11} |
| SPI-VIP | `spi_random_test` | FAIL | scoreboard 比對不符 | rc=0 UVM_ERROR=23 UVM_FATAL=0 VIP_WARNINGS=5: UVM_ERROR env/spi_env.sv(64) @ 4195000: uvm_test_top.env.sb [SB] mismatch exp{SPI mode=3(CPOL=1,CPHA=1) nbits=32 tx=0x80000778 rx=0x00000000 } obs{SPI mode=2(CPOL=1,CPHA=0) n |
| SWD-VIP | `swd_random_test` | FAIL | scoreboard 比對不符 | rc=0 UVM_ERROR=29 UVM_FATAL=0 VIP_WARNINGS=26: UVM_ERROR env/swd_env.sv(107) @ 1125000: uvm_test_top.env.sb [SB] mismatch exp{SWD AP WR a=1 data=0x750d0242 ack=FAULT rdata=0x00000000} obs{SWD AP WR a=1 data=0x7e643f46 ac |
| ToggleNAND-VIP | `tnand_random_test` | FAIL | scoreboard 比對不符 | rc=0 UVM_ERROR=14 UVM_FATAL=0 VIP_WARNINGS=11: UVM_ERROR env/tnand_env.sv(62) @ 6265000: uvm_test_top.env.sb [SB] mismatch exp{TNAND STATUS cmd=0x70 addr=0xfdae6c6ee7 len=18 status=0x40 err=TNAND_ERR_BUSY } obs{TNAND STA |
| TypeC-VIP | `typec_random_test` | FAIL | scoreboard 比對不符 | rc=0 UVM_ERROR=5 UVM_FATAL=0 VIP_WARNINGS=4: UVM_ERROR env/typec_env.sv(68) @ 905000: uvm_test_top.env.sb [SB] error-class mismatch exp{TYPEC role=2 rd_rp=0 pd=0 vconn=0 acc=ACC_NONE err=TC_ERR_CC_GLITCH} obs{TYPEC role= |
| UART-VIP | `uart_random_test` | FAIL | scoreboard 比對不符 | rc=0 UVM_ERROR=85 UVM_FATAL=0 VIP_WARNINGS=0: UVM_ERROR env/uart_env.sv(83) @ 11935000: uvm_test_top.env.sb [SB] mismatch exp{UART TX data=0x02 parity_en=0 stop2=0 baud_div=16 } obs{UART TX data=0x3f parity_en=0 stop2=0  |
| UFS-VIP | `ufs_regression_test` | FAIL | randomize 失敗 | rc=0 UVM_ERROR=80 UVM_FATAL=0 VIP_WARNINGS=242: UVM_ERROR ufs/ufs_pkg.sv(490) @ 100000: uvm_test_top.env.ufs_ag.sqr@@q [ufs_query_seq] Rand failed |
| UniPro-VIP | `mipi_unipro_test` | FAIL | randomize 失敗 | rc=0 UVM_ERROR=2 UVM_FATAL=0 VIP_WARNINGS=28: UVM_ERROR vip/base/mipi_vip_pkg.sv(701) @ 1086000: uvm_test_top.env.agt.sqr@@cor [RANDFAIL] randomize() failed |
| UniPro-VIP | `mipi_unipro_test` | FAIL | randomize 失敗 | rc=0 UVM_ERROR=2 UVM_FATAL=0 VIP_WARNINGS=28: UVM_ERROR vip/base/mipi_vip_pkg.sv(701) @ 1086000: uvm_test_top.env.agt.sqr@@cor [RANDFAIL] randomize() failed |
| UniPro_Mem-VIP | `memory_coverage_regression_test` | FAIL | randomize 失敗 | rc=0 UVM_ERROR=170 UVM_FATAL=0 VIP_WARNINGS=92: UVM_ERROR unipro/unipro_pkg.sv(295) @ 26570000: uvm_test_top.env.unipro_ag.sqr@@unipro_cov_msg_seq [unipro_cov_msg_seq] Rand failed |
| USB-VIP | `usb_random_regression_test` | FAIL | 逾時 / log 洪水 | rc=0 UVM_ERROR=82158 UVM_FATAL=0 VIP_WARNINGS=7279 timeout: UVM_ERROR sequences/usb_random_sequence.sv(55) @ 100000: uvm_test_top.env.usb3_agent.sqr@@seq_u3 [SEQ] Randomization failed |
| USB2-VIP | `usb_eusb2_test` | FAIL | 逾時 / log 洪水 | rc=0 UVM_ERROR=74068 UVM_FATAL=0 VIP_WARNINGS=1223 timeout: UVM_ERROR rtl/usb_vip_if.sv(295) @ 114000: reporter [USB_IF] MAC SOP-EOP alignment violation |
| USB3-VIP | `usb_random_regression_test` | FAIL | 逾時 / log 洪水 | rc=0 UVM_ERROR=82158 UVM_FATAL=0 VIP_WARNINGS=11226 timeout: UVM_ERROR sequences/usb_random_sequence.sv(55) @ 100000: uvm_test_top.env.usb3_agent.sqr@@seq_u3 [SEQ] Randomization failed |
| USB4-VIP | `usb4_test` | FAIL | 逾時 / log 洪水 | rc=0 UVM_ERROR=56030 UVM_FATAL=0 VIP_WARNINGS=4 timeout: UVM_ERROR sequences/usb_random_sequence.sv(55) @ 100000: uvm_test_top.env.usb4_agent.sqr@@seq [SEQ] Randomization failed |
| USB_PD-VIP | `usb_pd_test` | FAIL | 逾時 / log 洪水 | rc=0 UVM_ERROR=55962 UVM_FATAL=0 VIP_WARNINGS=2910 timeout: UVM_ERROR sequences/usb_random_sequence.sv(55) @ 100000: uvm_test_top.env.usbpd_agent.sqr@@seq [SEQ] Randomization failed |
| ONFI-VIP | `onfi_deep_test` | ERROR | 建置 | %Error: env/vip/onfi/onfi_timing_checker.sv:41:51: Internal: Unexpected Call |

沒有 UVM test：ACE-VIP、ACE_Lite-VIP、ATB-VIP、AXI4-VIP、AXI4_Lite-VIP、AXI_Stream-VIP、Avalon_MM-VIP、Avalon_ST-VIP、CHI-VIP、DDR4-VIP、GMII-VIP、GPIO-VIP、LPDDR4-VIP、MDIO-VIP、NVMe-VIP、OneWire-VIP、PWM-VIP、QSPI-VIP、RGMII-VIP、SATA-VIP、SDIO-VIP、WTB-VIP、Wishbone-VIP、XGMII-VIP。
