# TV／STB／IPCAM 系統驗證需求對照（media system verification）

日期：2026-11-12（Asia/Taipei）。依據：`docs/TV_STB_IPCAM_IMPROVEMENT_PLAN_2026-10-26.md`（下稱「計畫」）。
進度與證據見 `docs/PROGRESS_TV_STB_IPCAM.md`；架構圖見 PR #17（`docs/architecture/TV-STB-IPCAM-diagrams.md`，尚未合併）。

本 repo 只提供 verification IP（VIP、device model、測試）。本文件不代表對應的 controller／PHY RTL
已完成，也不把 VIP 存在、coverage 百分比或 mutation score 當成協定 conformance 或產品成熟度。

## 1. 驗證層級

| 層級 | 意義 | 本 repo 的證據 |
|---|---|---|
| elaboration | 檔案能被前端完整解析 | `tools/elab_scan.py`（`ELAB_ERRORS=0`） |
| smoke | UVM test 能在模擬器上跑完 | `tools/run_uvm_tests.py --smoke`、`docs/UVM_SMOKE.md` |
| functional | 有非零檢查點的 scoreboard／checker 測試 | 各 VIP `README.md` 的 L1c／L1d 結果、`docs/RAL.md` |
| conformance | 對照規格的獨立參考（公開向量、標準 decoder、第三方實作） | 目前只有少數項目有，見各節 |
| system | SoC 端到端（多 IP、DMA、frame buffer、軟體） | `soc/device_models`、`soc/dram_timing` 提供零件；端到端 bench 尚未建立 |

## 2. 子系統需求對照

狀態：**有**＝VIP／測試已涵蓋並有非零檢查點；**部分**＝只涵蓋其中幾項；**無**＝本 repo 沒有。
獨立性：VIP 的 scoreboard 與 driver 是否來自同一份模板（計畫要求不能以 same-template 自我驗證）。

### 2.1 AXI4（系統匯流排）

| 需求 | 狀態 | VIP／測試 | 獨立性與備註 |
|---|---|---|---|
| burst（INCR／WRAP／FIXED） | 有 | AXI-VIP：`axi_incr_burst_seq`、`axi_wrap_burst_seq`、`amba_axi_cov_test`（PR #37） | scoreboard 以 slave memory 讀回比對；RAL `amba_ral_test`（`docs/RAL.md`） |
| 4KB boundary | 部分 | AXI-VIP `c_axi_legal` 讓 INCR 不跨 4 KB（PR #37） | 只保證合法激勵；沒有「故意跨 4 KB 要被抓到」的負向測試 |
| IDs／outstanding | 部分 | AXI-VIP L3 SVA 檢查 ID ordering | driver 一次只發一筆，沒有 multiple outstanding；ACE／CHI VIP 另計 |
| backpressure | 部分 | AXI-VIP SVA（VALID 在 READY 前保持）；AXI_Stream-UVM-VIP TREADY back-pressure | AXI4 slave model 沒有隨機 READY 延遲 |
| error／timeout | 部分 | AXI-VIP SLVERR 區（`0xEE00_0000`）、`axi_error_inject_seq`；ready 檢查 `##[0:16]` | 沒有 DECERR、沒有 timeout 後的 recovery |
| abort drain | 無 | — | 需 SoC 層的 DMA abort 情境 |

### 2.2 Video stream

| 需求 | 狀態 | VIP／測試 | 獨立性與備註 |
|---|---|---|---|
| SOF／EOL（frame／line 邊界） | 部分 | CSI2_Sensor-UVM-VIP（FS／FE／LS／LE short packet）；AXI_Stream-UVM-VIP（TLAST） | AXI-Stream video 慣用的 TUSER=SOF 沒有建模 |
| valid lane／pixel packing | 部分 | VbyOne_HS-UVM-VIP（8 lane、4-byte mode、pixel group zero padding）；HDMI_Source-UVM-VIP（TMDS） | |
| frame size | 部分 | HDMI_Source-UVM-VIP（CTA-861 timing preset）；CSI2_Sensor-UVM-VIP（每行 payload 長度） | |
| stall stability | 部分 | AXI_Stream-UVM-VIP back-pressure；VbyOne_HS K28.5 underrun filler | 沒有 video pipeline 在 stall 下 frame 不破的端到端檢查 |
| frame-boundary config | 無 | — | 需 SoC 層（設定只能在 frame 邊界生效） |

### 2.3 Frame manager

| 需求 | 狀態 | 備註 |
|---|---|---|
| ownership／refcount／多 consumer | 無 | 屬 SoC 軟硬體協定，沒有對應 VIP |
| reuse／free | 無 | 同上 |
| secure／nonsecure 隔離 | 無 | 需 TrustZone 類 bus attribute（AXI `AxPROT[1]`）的系統測試；AXI-VIP 只會產生 `prot` 欄位 |

### 2.4 Camera

| 需求 | 狀態 | VIP／測試 | 獨立性與備註 |
|---|---|---|---|
| CSI lane／VC／DT | 有 | CSI2_Sensor-UVM-VIP（任意 VC；RAW8、RAW10、YUV422、RGB888）；CSI_2-VIP、D_PHY-VIP、C_PHY-VIP | CSI2_Sensor 搭配 open-ip-portfolio `CSI_2_top` 做過 device model 測試（`soc/device_models/run.sh`，11 checks） |
| ECC／CRC 錯誤 | 有 | CSI2_Sensor-UVM-VIP：header 每個位置的單 bit 錯（修正）、2 bit 錯（丟棄）、ECC byte 錯、payload／CRC-16 錯 | ECC 與 CRC 的獨立參考向量尚未加入（見 #34 的同類問題） |
| RAW packing | 部分 | CSI2_Sensor-UVM-VIP RAW8／RAW10 | RAW12／RAW14 沒有 |
| sensor 不可回壓時的 overflow 策略 | 無 | — | 需要 receiver RTL 的 buffer 行為；VIP 端可加「接收端不讀時繼續送」的情境 |
| 時間戳 | 無 | — | CSI-2 frame number（FS／FE data field）有傳，但沒有時間戳檢查 |
| 控制介面 | 有 | SCCB_Sensor-UVM-VIP（16-bit register address）、I2C-VIP（RAL，PR #38） | |

### 2.5 Codec

| 需求 | 狀態 | 備註 |
|---|---|---|
| 標準 decoder／encoder golden | 無 | 本 repo 沒有 codec VIP。需以公開參考 decoder（例如 H.264／HEVC 的 reference software）產生 golden，且注意授權 |
| conformance corpus 清單 | 無 | 可列 ITU-T／ISO 公開 conformance bitstream 清單；本 repo 不存放 bitstream |
| 合法／損毀 bitstream | 無 | |
| 長時間及多 context | 無 | |
| （周邊）傳輸流 | 有 | MPEG_TS-UVM-VIP：188-byte TS、sync、PID、CC、adaptation field、error flag |

### 2.6 Display／network／storage

| 需求 | 狀態 | VIP／測試 | 獨立性與備註 |
|---|---|---|---|
| display underflow | 部分 | VbyOne_HS-UVM-VIP（K28.5 underrun filler，scoreboard 逐行比對像素） | 沒有 display controller 的 underflow 偵測／恢復 |
| frame pacing | 無 | — | |
| HDMI／DP 輸出 | 部分 | HDMI_Source-UVM-VIP（TMDS running disparity、data island BCH ECC、InfoFrame）、HDMI-VIP、DisplayPort2-VIP、HDMI_CEC-UVM-VIP、HDCP-VIP | HDCP-VIP smoke 為 FAIL（scoreboard 不符，`docs/UVM_SMOKE.md`） |
| MAC／FCS／PAUSE | 有 | GMII_PHY-UVM-VIP（bad FCS、symbol error、runt、oversize、VLAN、PAUSE，有／無 PAUSE opcode；scoreboard 自行計算 CRC residue）；Ethernet-VIP | `soc/device_models` 的 `gmii_phy_model` 對 `Ethernet_top` 7 checks；Ethernet-VIP smoke 為 FAIL（逾時，#28） |
| SD 斷電 | 無 | SD_Card-UVM-VIP、SDMMC_Card-UVM-VIP、eMMC_Device-UVM-VIP 有 CRC7／CRC16、busy、錯誤命令，但沒有斷電／重新上電 | eMMC_Device 有 RST_n 保留 block |
| DMA 錯誤 | 無 | — | 需 SoC 層 |

### 2.7 Security／power

| 需求 | 狀態 | 備註 |
|---|---|---|
| 越權 DMA | 無 | 需 SoC 層 |
| debug 鎖 | 無 | JTAG-VIP／SWD-VIP 只測協定，沒有 lock 狀態 |
| reset／clock-gate／retention | 無 | 低功耗 VIP 沒有涵蓋 |
| malformed descriptors | 無 | 需 DMA descriptor 模型 |
| 加解密引擎 | 部分 | Security-VIP 只有 AES-like 可逆模型（`enc = rol8(d)^k`），不是 AES；smoke 逾時（#28）。STB：Smartcard_ISO7816-UVM-VIP、CI_CAM-UVM-VIP（CI+ TS descrambling） |

## 3. 驗收規則（計畫「驗收」與「共通交付」）

| 規則 | 目前做法 | 缺口 |
|---|---|---|
| 不能 same-template 自我驗證 | 每個 VIP 有 mutation 測試（PR #21：16 個 VIP mutation score 100%，等價 mutant 記在 `tools/mutation_equivalent.csv`）；`soc/device_models` 對 open-ip-portfolio RTL 測試 | scoreboard 多數仍與 driver 同模板產生；CRC／ECC／FEC 缺獨立參考向量（#34） |
| 保留 seed／config／tool／version／非零檢查點 | `uvm_report.csv`、`uvm_smoke_report.csv`；pass 規則要求 `checks=<n>` 非零 | seed 沒有統一記錄 |
| waiver 逐條 | `ignore_bins` 帶 `REACHABILITY` 註解（PR #37）、`tools/mutation_equivalent.csv` | coverage waiver 尚未集中成一份清單 |
| mutation 證明 scoreboard 能抓錯 | 見上；RAL test 另做 DUT mutation（`docs/RAL.md` 3.2、6.2、8.2） | |
| 效能以實測記錄 | — | 本 repo 沒有效能量測 |

## 4. 下一步（依影響排序）

1. 端到端 system bench：CSI-2 sensor → CSI_2_top → AXI → DRAM（`dram_timing`）→ display，量 frame 完整性與頻寬。
2. Frame manager 與 secure／nonsecure 隔離的 SoC 測試（需要 RTL）。
3. Codec：列出公開 conformance corpus 與授權，決定 golden decoder 來源。
4. CSI-2 ECC／CRC、Ethernet FCS 加入公開參考向量（與 #34 一起做）。
5. SD／eMMC 斷電、AXI abort drain、DECERR、multiple outstanding。
