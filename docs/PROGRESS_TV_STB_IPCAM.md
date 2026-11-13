# TV／STB／IPCAM 驗證進度

依 `docs/TV_STB_IPCAM_IMPROVEMENT_PLAN_2026-10-26.md` 的「共通交付與驗收」：每次更新記錄台北時間、commit、
完成／待驗收／阻塞、測試命令與結果、下一步。沒有結果的項目不填 PASS。需求對照見
`docs/design/media_system_verification.md`。

## 2026-11-12 08:07（Asia/Taipei）

基準 commit：`f581062`（main）。

### 完成

| 項目 | 證據 | 測試命令與結果 |
|---|---|---|
| TV VIP（IR_Remote、HDMI_CEC、MPEG_TS、SPDIF、VbyOne_HS、HDMI_Source） | PR #21 | Verilator 5.052 + uvm-core，scoreboard checks：IR 124、CEC 122、TSI 164、S/PDIF 132、V-by-One 92、HDMI source 104；mutation 100% |
| IP camera VIP（CSI2_Sensor、GMII_PHY、I2S_Codec、SPI_NOR、SCCB_Sensor、SD_Card、eMMC_Device、SDMMC_Card） | PR #21 | CSI-2 sensor 248、GMII PHY 128、I2S codec 106、SPI NOR 132、SCCB 104、SD card 162、eMMC 160、SDMMC card 176；mutation 100% |
| STB VIP（Smartcard_ISO7816、CI_CAM） | PR #21 | smartcard 132、CI CAM 150；CI_CAM 另對 open-ip `CI_Plus_Host_top`（CIS 讀取、COR、兩次 message round trip、TS 經 CAM） |
| SoC device model | PR #21，`soc/device_models/run.sh` | CSI-2 11、GMII 7、I2S 10 checks，對 open-ip-portfolio RTL |
| DRAM timing model | PR #21，`soc/dram_timing/run.sh` | 35 checks（Verilator） |
| 需求對照文件 | 本 PR：`docs/design/media_system_verification.md` | 文件 |

### 待驗收（PR 已開，尚未合併）

| 項目 | PR | 結果 |
|---|---|---|
| TV／STB／IPCAM 架構圖 | #17 | 文件 |
| I2S_Codec checker 誤報（25–32 週期 burst） | #24 | minisim：I2S_Codec 通過 |
| AXI-VIP 合法激勵（4 KB、對齊、WRAP 長度）與 coverage | #37 | minisim：`amba_axi_cov_test` SB_PASS checks=254，covergroup 100%；Verilator 未跑 |
| I2C RAL（SCCB 類控制介面同型） | #38 | minisim：`i2c_ral_test` RAL_PASS checks=137；Verilator 未跑 |

### 阻塞／未開始

| 項目 | 原因 |
|---|---|
| frame manager、secure／nonsecure 隔離、越權 DMA、malformed descriptors | 需 SoC RTL 與 system bench，本 repo 只有 VIP |
| codec golden／conformance corpus | 沒有 codec VIP；需先決定公開參考 decoder 與授權 |
| SD 斷電、AXI abort drain、DECERR、multiple outstanding | 尚未排入 |
| Ethernet-VIP、Security-VIP smoke 逾時；HDCP-VIP scoreboard 不符 | #28 與 smoke 修正 |
| CSI-2 ECC／CRC、Ethernet FCS 的獨立參考向量 | 與 #34 一起做 |

### 下一步

1. 合併 #17、#24、#37、#38 後，以 Verilator 重跑 `tools/run_uvm_tests.py` 並更新本表。
2. 建 CSI-2 → AXI → DRAM → display 的端到端 bench（`soc/`）。
3. 為 CSI-2 ECC／CRC 與 Ethernet FCS 加入公開參考向量。
