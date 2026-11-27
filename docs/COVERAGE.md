# VIP Portfolio Coverage 報告

> 由 `tools/gen_coverage_doc.py` 依 `coverage_report.csv`（`tools/coverage.py`，Verilator 5.054 `--coverage`）自動產生，請勿手動修改。

## 1. 結論

- 117 個 VIP 中 117 個量到 code coverage（131 個功能測試中 130 個在 Verilator 上帶 coverage 執行）。
- Line / branch coverage（全部 DUT model 合計）：93.8%（5056/5389）。
- Toggle coverage（全部 DUT model 合計）：50.2%（52989/105572）。
- Expression coverage（全部 DUT model 合計）：89.8%（3330/3709）。
- Line coverage 100% 的 VIP 43 個，≥ 90% 的 97 個，低於 90% 的 20 個（見第 4 節）。
- Functional coverage（covergroup bins，在 Verilator 上量得的 ACE-UVM-VIP / ACE_Lite-UVM-VIP / AHB-VIP / APB-VIP / ATB-UVM-VIP / AVSBus-VIP / AXI-VIP / AXI4_Lite-UVM-VIP / AXI_Stream-UVM-VIP / Avalon_MM-UVM-VIP / Avalon_ST-UVM-VIP / BoW-UVM-VIP / CAN_FD-UVM-VIP / CAN_XL-UVM-VIP / CHI-UVM-VIP / CHI_H-UVM-VIP / CI_CAM-UVM-VIP / DDR-VIP / DDR5-VIP / ETH800G-VIP / EtherCAT-VIP / GMII-UVM-VIP / GMII_PHY-UVM-VIP / GPIO-UVM-VIP / HBM-VIP / HBM3E-VIP / HyperBus-UVM-VIP / I2C-VIP / I2S_Codec-UVM-VIP / IO_Link-VIP / IR_Remote-UVM-VIP / LPDDR-VIP / LPDDR6-VIP / MACsec-UVM-VIP / MCTP-UVM-VIP / MDIO-UVM-VIP / MIL_STD_1553-VIP / MPEG_TS-UVM-VIP / NC-SI-UVM-VIP / NVMe-VIP / OBI-UVM-VIP / OCP-VIP / ONFI-VIP / OneWire-UVM-VIP / PTP-VIP / PWM-UVM-VIP / RGMII-UVM-VIP / RVFI-UVM-VIP / RapidIO-VIP / SATA-VIP / SCCB_Sensor-UVM-VIP / SD-VIP / SDIO-UVM-VIP / SDMMC_Card-UVM-VIP / SD_Card-UVM-VIP / SENT-VIP / SGMII-UVM-VIP / SMBus-UVM-VIP / SPDIF-UVM-VIP / SPDM-UVM-VIP / SPI_NOR-UVM-VIP / SUE-UVM-VIP / Smartcard_ISO7816-UVM-VIP / SpaceWire-UVM-VIP / T1S_PLCA-UVM-VIP / TDM-UVM-VIP / TileLink-VIP / UEC-VIP / UFS-VIP / USXGMII-UVM-VIP / VbyOne_HS-UVM-VIP / WTB-UVM-VIP / Wishbone-UVM-VIP / XGMII-UVM-VIP / eMMC-VIP / eMMC_Device-UVM-VIP / eSPI-UVM-VIP / hbm3-VIP / xSPI-UVM-VIP）：33.8%（2327/6883），其餘 UVM 環境的 covergroup 需商用模擬器（見第 2 節）。

## 2. 方法

`tools/coverage.py` 把每個功能測試（`tools/run_func_tests.py` 的同一組測試與編譯組合）加上 `--coverage-line --coverage-toggle --coverage-expr --coverage-user` 重新以 Verilator 建置並執行，再依 VIP 合併各測試的 `coverage.dat`。只計算被測的程式碼：UVM VIP 為 `smoke/<VIP>/dut_*.sv`（flatten 後的 DUT model），RTL IP 為 `rtl/*.sv`；testbench 與 package 不計。同一個 coverage point 在任一測試、任一 instance 被觸發即算命中。

| 指標 | 意義 |
|---|---|
| Line / branch | 每個 statement block 與每個 if/case 分支是否執行過 |
| Toggle | 每個 signal 的每個 bit 是否都出現過 0→1 與 1→0 |
| Expression | 多項條件式中每一項的組合是否都出現過（類似 FEC / condition coverage） |
| Cover (SVA) | `cover property` / `cover` 是否觸發過（只有部分 model 有） |
| Functional | covergroup 的 bins 命中數（`v_covergroup`） |

限制：
- Toggle 包含寬資料匯流排的高位元與測試中固定不動的 sideband / 其他協定的 tie-off，所以普遍低於 line coverage，是參考值而非目標。
- Functional coverage 只在功能測試建置含 covergroup 的 VIP 量測（例如範本 agent 的 `<p>_func_test` / `<p>_ral_test`、APB / AHB / AXI 的 `amba_ral_test`、OCP 的 `ocp_ral_test`、TileLink 的 `tilelink_ral_test`，見 [RAL.md](RAL.md)）；AMBA VIP 共用 APB/AHB/AXI checker，只計算該 VIP 協定與共用 interface 的 covergroup。其他 VIP 的 covergroup 在 UVM monitor / coverage collector 裡，需用各 VIP 的 `scripts/coverage.mk`（VCS / Xcelium / Questa）量測。
- 只能在 Icarus 上跑的測試（例如要比對 `1'bz` 的 tri-state 檢查）量不到 coverage；在 coverage 建置下結果不同的測試仍計入其 coverage，兩者都列在第 5 節。

## 3. 各 VIP Coverage

| VIP | 測試 | Line / branch | Toggle | Expression | Cover (SVA) | Functional (covergroup) |
|---|---|---|---|---|---|---|
| [ACE-UVM-VIP](test_suites/ACE-UVM-VIP.md) | 1/1 | 92.6% (112/121) | 64.5% (1001/1552) | 91.5% (86/94) | 100.0% (4/4) | 81.8% (36/44) |
| [ACE_Lite-UVM-VIP](test_suites/ACE_Lite-UVM-VIP.md) | 1/1 | 100.0% (11/11) | 8.0% (183/2282) | 94.4% (17/18) | 100.0% (2/2) | 100.0% (22/22) |
| [AHB-VIP](test_suites/AHB-VIP.md) | 2/2 | 100.0% (13/13) | 56.3% (364/646) | 100.0% (15/15) | 81.2% (13/16) | 93.3% (83/89) |
| [APB-VIP](test_suites/APB-VIP.md) | 2/2 | 100.0% (19/19) | 37.8% (196/518) | 100.0% (20/20) | 100.0% (14/14) | 96.6% (86/89) |
| [ATB-UVM-VIP](test_suites/ATB-UVM-VIP.md) | 1/1 | 100.0% (3/3) | 20.0% (16/80) | 100.0% (8/8) | 100.0% (2/2) | 100.0% (5/5) |
| [AVSBus-VIP](test_suites/AVSBus-VIP.md) | 1/1 | 95.7% (22/23) | 64.3% (18/28) | 87.5% (14/16) | - | 15.4% (21/136) |
| [AXI-VIP](test_suites/AXI-VIP.md) | 2/2 | 92.1% (35/38) | 61.6% (548/890) | 100.0% (35/35) | 46.7% (7/15) | 93.2% (205/220) |
| [AXI4_Lite-UVM-VIP](test_suites/AXI4_Lite-UVM-VIP.md) | 1/1 | 100.0% (33/33) | 70.7% (338/478) | 100.0% (54/54) | 100.0% (4/4) | 92.9% (39/42) |
| [AXI_Stream-UVM-VIP](test_suites/AXI_Stream-UVM-VIP.md) | 1/1 | 100.0% (32/32) | 89.2% (403/452) | 100.0% (47/47) | 100.0% (4/4) | 8.4% (29/344) |
| [Avalon_MM-UVM-VIP](test_suites/Avalon_MM-UVM-VIP.md) | 1/1 | 100.0% (10/10) | 91.0% (162/178) | 100.0% (21/21) | 100.0% (2/2) | 100.0% (11/11) |
| [Avalon_ST-UVM-VIP](test_suites/Avalon_ST-UVM-VIP.md) | 2/2 | 100.0% (9/9) | 100.0% (218/218) | 100.0% (13/13) | 100.0% (2/2) | 100.0% (3/3) |
| [Bluetooth5-VIP](test_suites/Bluetooth5-VIP.md) | 1/1 | 95.8% (23/24) | 34.7% (131/378) | 90.9% (10/11) | - | - |
| [BoW-UVM-VIP](test_suites/BoW-UVM-VIP.md) | 1/1 | 98.7% (74/75) | 99.6% (1331/1336) | 96.5% (55/57) | 100.0% (7/7) | 100.0% (20/20) |
| [CAN-VIP](test_suites/CAN-VIP.md) | 1/1 | 85.6% (89/104) | 74.5% (891/1196) | 86.5% (45/52) | - | - |
| [CAN_FD-UVM-VIP](test_suites/CAN_FD-UVM-VIP.md) | 1/1 | 100.0% (11/11) | 75.0% (24/32) | 100.0% (9/9) | 100.0% (2/2) | 87.5% (7/8) |
| [CAN_XL-UVM-VIP](test_suites/CAN_XL-UVM-VIP.md) | 1/1 | 90.1% (82/91) | 65.0% (515/792) | 83.8% (57/68) | 100.0% (2/2) | 81.1% (30/37) |
| [CHI-UVM-VIP](test_suites/CHI-UVM-VIP.md) | 1/2 | 91.7% (11/12) | 30.2% (70/232) | 100.0% (2/2) | 100.0% (2/2) | 100.0% (6/6) |
| [CHI_H-UVM-VIP](test_suites/CHI_H-UVM-VIP.md) | 1/1 | 97.4% (76/78) | 79.3% (2479/3128) | 95.3% (61/64) | 100.0% (9/9) | 100.0% (34/34) |
| [CI_CAM-UVM-VIP](test_suites/CI_CAM-UVM-VIP.md) | 1/1 | 98.6% (146/148) | 52.4% (1350/2576) | 93.3% (84/90) | 100.0% (1/1) | 6.2% (2/32) |
| [CPRI-VIP](test_suites/CPRI-VIP.md) | 1/1 | 94.4% (17/18) | 92.1% (140/152) | 100.0% (9/9) | - | - |
| [CXS-VIP](test_suites/CXS-VIP.md) | 1/1 | 100.0% (13/13) | 94.3% (164/174) | 100.0% (18/18) | - | - |
| [DDR-VIP](test_suites/DDR-VIP.md) | 1/1 | 100.0% (23/23) | 17.0% (216/1274) | 91.7% (22/24) | 82.8% (24/29) | 97.1% (102/105) |
| [DDR5-VIP](test_suites/DDR5-VIP.md) | 2/2 | 88.8% (238/268) | 64.5% (2524/3914) | 87.2% (109/125) | 100.0% (4/4) | 100.0% (46/46) |
| [DFI-VIP](test_suites/DFI-VIP.md) | 1/1 | 96.3% (26/27) | 46.5% (318/684) | 81.8% (9/11) | - | - |
| [ETH800G-VIP](test_suites/ETH800G-VIP.md) | 2/2 | 100.0% (15/15) | 92.0% (613/666) | 86.4% (19/22) | 100.0% (2/2) | 100.0% (9/9) |
| [EtherCAT-VIP](test_suites/EtherCAT-VIP.md) | 1/1 | 100.0% (5/5) | 32.6% (30/92) | 100.0% (4/4) | 100.0% (2/2) | 100.0% (8/8) |
| [Ethernet-VIP](test_suites/Ethernet-VIP.md) | 2/2 | 96.2% (50/52) | 98.3% (1062/1080) | 90.9% (20/22) | - | - |
| [Ethernet_AVB_TSN-VIP](test_suites/Ethernet_AVB_TSN-VIP.md) | 1/1 | 86.5% (32/37) | 37.2% (254/682) | 88.9% (16/18) | - | - |
| [FC-VIP](test_suites/FC-VIP.md) | 1/1 | 96.4% (54/56) | 97.6% (1080/1106) | 94.4% (34/36) | - | - |
| [FlexRay-VIP](test_suites/FlexRay-VIP.md) | 1/1 | 96.3% (52/54) | 46.3% (544/1176) | 94.7% (18/19) | - | - |
| [GMII-UVM-VIP](test_suites/GMII-UVM-VIP.md) | 1/1 | 100.0% (3/3) | 97.7% (43/44) | 100.0% (2/2) | 100.0% (2/2) | 100.0% (5/5) |
| [GMII_PHY-UVM-VIP](test_suites/GMII_PHY-UVM-VIP.md) | 1/1 | 96.3% (79/82) | 88.8% (627/706) | 96.4% (54/56) | 100.0% (2/2) | 100.0% (12/12) |
| [GPIO-UVM-VIP](test_suites/GPIO-UVM-VIP.md) | 1/1 | 100.0% (3/3) | 98.5% (67/68) | 100.0% (2/2) | 100.0% (2/2) | 100.0% (6/6) |
| [HBM-VIP](test_suites/HBM-VIP.md) | 1/1 | 100.0% (23/23) | 23.8% (342/1434) | 95.7% (22/23) | 79.2% (19/24) | 93.3% (97/104) |
| [HBM3E-VIP](test_suites/HBM3E-VIP.md) | 3/3 | 93.9% (124/132) | 74.3% (4400/5918) | 92.1% (70/76) | 100.0% (2/2) | 100.0% (17/17) |
| [HyperBus-UVM-VIP](test_suites/HyperBus-UVM-VIP.md) | 1/1 | 95.1% (58/61) | 81.6% (408/500) | 94.4% (34/36) | 100.0% (2/2) | 89.3% (25/28) |
| [I2C-VIP](test_suites/I2C-VIP.md) | 1/1 | 82.8% (24/29) | 1.2% (24/2080) | 92.3% (12/13) | - | 31.4% (11/35) |
| [I2S-VIP](test_suites/I2S-VIP.md) | 1/1 | 88.5% (23/26) | 98.2% (110/112) | 92.3% (12/13) | - | - |
| [I2S_Codec-UVM-VIP](test_suites/I2S_Codec-UVM-VIP.md) | 1/1 | 100.0% (29/29) | 99.5% (205/206) | 100.0% (20/20) | 100.0% (1/1) | 100.0% (7/7) |
| [I3C-VIP](test_suites/I3C-VIP.md) | 1/1 | 81.0% (162/200) | 1.6% (67/4240) | 72.9% (140/192) | - | - |
| [IO_Link-VIP](test_suites/IO_Link-VIP.md) | 1/1 | 96.2% (25/26) | 74.1% (86/116) | 100.0% (8/8) | 100.0% (2/2) | 100.0% (9/9) |
| [IR_Remote-UVM-VIP](test_suites/IR_Remote-UVM-VIP.md) | 1/1 | 94.1% (80/85) | 82.7% (248/300) | 96.7% (29/30) | 100.0% (3/3) | 100.0% (12/12) |
| [Interlaken-VIP](test_suites/Interlaken-VIP.md) | 1/1 | 92.0% (23/25) | 50.5% (278/550) | 100.0% (20/20) | - | - |
| [JESD204-VIP](test_suites/JESD204-VIP.md) | 1/1 | 86.1% (31/36) | 61.6% (90/146) | 100.0% (8/8) | - | - |
| [JTAG-VIP](test_suites/JTAG-VIP.md) | 1/1 | 98.6% (68/69) | 82.4% (216/262) | 100.0% (41/41) | - | - |
| [LIN-VIP](test_suites/LIN-VIP.md) | 1/1 | 88.6% (78/88) | 80.2% (629/784) | 45.1% (23/51) | - | - |
| [LPDDR-VIP](test_suites/LPDDR-VIP.md) | 1/1 | 95.7% (22/23) | 8.0% (94/1170) | 100.0% (3/3) | 79.2% (19/24) | 94.0% (109/116) |
| [LPDDR6-VIP](test_suites/LPDDR6-VIP.md) | 2/2 | 100.0% (14/14) | 100.0% (1080/1080) | 100.0% (12/12) | 100.0% (2/2) | 100.0% (19/19) |
| [LPI-VIP](test_suites/LPI-VIP.md) | 1/1 | 100.0% (10/10) | 100.0% (12/12) | 100.0% (12/12) | - | - |
| [LTI-VIP](test_suites/LTI-VIP.md) | 1/1 | 100.0% (12/12) | 80.9% (304/376) | 100.0% (5/5) | - | - |
| [MACsec-UVM-VIP](test_suites/MACsec-UVM-VIP.md) | 1/1 | 98.7% (76/77) | 62.7% (2715/4328) | 85.2% (46/54) | 100.0% (2/2) | 100.0% (19/19) |
| [MCTP-UVM-VIP](test_suites/MCTP-UVM-VIP.md) | 1/1 | 100.0% (76/76) | 71.2% (403/566) | 96.1% (74/77) | 100.0% (3/3) | 90.9% (30/33) |
| [MDIO-UVM-VIP](test_suites/MDIO-UVM-VIP.md) | 2/2 | 92.6% (25/27) | 95.6% (195/204) | 84.6% (11/13) | 100.0% (2/2) | 100.0% (8/8) |
| [MIL_STD_1553-VIP](test_suites/MIL_STD_1553-VIP.md) | 1/1 | 100.0% (9/9) | 32.3% (31/96) | 100.0% (6/6) | 100.0% (2/2) | 100.0% (9/9) |
| [MPEG_TS-UVM-VIP](test_suites/MPEG_TS-UVM-VIP.md) | 1/1 | 95.5% (42/44) | 89.4% (161/180) | 95.8% (23/24) | 100.0% (2/2) | 100.0% (15/15) |
| [NC-SI-UVM-VIP](test_suites/NC-SI-UVM-VIP.md) | 1/1 | 99.0% (102/103) | 29.8% (1256/4210) | 94.6% (35/37) | 100.0% (2/2) | 100.0% (26/26) |
| [NVMe-VIP](test_suites/NVMe-VIP.md) | 2/2 | 100.0% (23/23) | 10.9% (297/2724) | 100.0% (15/15) | 100.0% (32/32) | 7.0% (27/384) |
| [OBI-UVM-VIP](test_suites/OBI-UVM-VIP.md) | 1/1 | 100.0% (17/17) | 59.0% (333/564) | 100.0% (31/31) | 100.0% (3/3) | 81.8% (27/33) |
| [OCP-VIP](test_suites/OCP-VIP.md) | 1/1 | 100.0% (16/16) | 85.8% (295/344) | 100.0% (5/5) | - | 93.1% (27/29) |
| [ONFI-VIP](test_suites/ONFI-VIP.md) | 1/1 | 90.5% (86/95) | 83.1% (118/142) | 100.0% (35/35) | 100.0% (35/35) | 13.2% (68/515) |
| [OneWire-UVM-VIP](test_suites/OneWire-UVM-VIP.md) | 1/1 | 90.9% (10/11) | 87.5% (21/24) | 85.7% (6/7) | 100.0% (2/2) | 100.0% (5/5) |
| [PTP-VIP](test_suites/PTP-VIP.md) | 1/1 | 100.0% (7/7) | 6.3% (25/398) | 100.0% (5/5) | 100.0% (2/2) | 100.0% (2/2) |
| [PWM-UVM-VIP](test_suites/PWM-UVM-VIP.md) | 1/1 | 100.0% (6/6) | 19.8% (21/106) | 100.0% (9/9) | 100.0% (2/2) | 100.0% (7/7) |
| [RGMII-UVM-VIP](test_suites/RGMII-UVM-VIP.md) | 1/1 | 100.0% (3/3) | 95.8% (23/24) | 100.0% (2/2) | 100.0% (2/2) | 100.0% (3/3) |
| [RVFI-UVM-VIP](test_suites/RVFI-UVM-VIP.md) | 1/1 | 85.0% (91/107) | 33.9% (1166/3440) | 91.4% (74/81) | 100.0% (2/2) | 81.7% (49/60) |
| [RapidIO-VIP](test_suites/RapidIO-VIP.md) | 1/1 | 100.0% (5/5) | 73.0% (111/152) | 100.0% (2/2) | 100.0% (2/2) | 100.0% (7/7) |
| [SAS-VIP](test_suites/SAS-VIP.md) | 1/1 | 91.4% (106/116) | 16.3% (278/1702) | 85.7% (36/42) | - | - |
| [SATA-VIP](test_suites/SATA-VIP.md) | 1/1 | 87.5% (21/24) | 32.0% (144/450) | 78.9% (15/19) | 71.0% (22/31) | 20.8% (22/106) |
| [SCCB_Sensor-UVM-VIP](test_suites/SCCB_Sensor-UVM-VIP.md) | 1/1 | 100.0% (42/42) | 79.2% (141/178) | 100.0% (36/36) | 100.0% (1/1) | 100.0% (9/9) |
| [SD-VIP](test_suites/SD-VIP.md) | 1/1 | 92.2% (95/103) | 40.7% (918/2258) | 83.0% (73/88) | 97.1% (33/34) | 11.1% (103/932) |
| [SDIO-UVM-VIP](test_suites/SDIO-UVM-VIP.md) | 1/1 | 94.1% (16/17) | 95.3% (225/236) | 88.9% (8/9) | 100.0% (2/2) | 83.3% (5/6) |
| [SDMMC_Card-UVM-VIP](test_suites/SDMMC_Card-UVM-VIP.md) | 1/1 | 96.9% (157/162) | 89.7% (1162/1296) | 86.7% (117/135) | 100.0% (1/1) | 26.1% (6/23) |
| [SD_Card-UVM-VIP](test_suites/SD_Card-UVM-VIP.md) | 1/1 | 98.0% (96/98) | 93.3% (1299/1392) | 81.0% (64/79) | 100.0% (1/1) | 25.0% (4/16) |
| [SENT-VIP](test_suites/SENT-VIP.md) | 1/1 | 100.0% (9/9) | 82.0% (41/50) | 100.0% (10/10) | 100.0% (2/2) | 90.6% (29/32) |
| [SGMII-UVM-VIP](test_suites/SGMII-UVM-VIP.md) | 1/1 | 100.0% (97/97) | 99.3% (151/152) | 90.4% (47/52) | 100.0% (3/3) | 100.0% (13/13) |
| [SMBus-UVM-VIP](test_suites/SMBus-UVM-VIP.md) | 1/1 | 96.3% (79/82) | 57.3% (172/300) | 93.1% (81/87) | 100.0% (3/3) | 90.6% (29/32) |
| [SPDIF-UVM-VIP](test_suites/SPDIF-UVM-VIP.md) | 1/1 | 96.1% (49/51) | 81.6% (279/342) | 89.7% (26/29) | 100.0% (2/2) | 90.0% (9/10) |
| [SPDM-UVM-VIP](test_suites/SPDM-UVM-VIP.md) | 1/1 | 100.0% (67/67) | 26.0% (1245/4788) | 95.7% (44/46) | 50.0% (1/2) | 87.8% (43/49) |
| [SPI-VIP](test_suites/SPI-VIP.md) | 1/1 | 88.0% (22/25) | 92.0% (46/50) | 76.9% (10/13) | - | - |
| [SPI_NOR-UVM-VIP](test_suites/SPI_NOR-UVM-VIP.md) | 1/1 | 96.2% (50/52) | 84.9% (146/172) | 97.6% (41/42) | 100.0% (1/1) | 100.0% (17/17) |
| [SUE-UVM-VIP](test_suites/SUE-UVM-VIP.md) | 1/1 | 96.9% (31/32) | 40.0% (928/2320) | 94.4% (17/18) | 100.0% (2/2) | 100.0% (14/14) |
| [SWD-VIP](test_suites/SWD-VIP.md) | 1/1 | 93.6% (44/47) | 9.0% (24/268) | 75.0% (18/24) | - | - |
| [Security-VIP](test_suites/Security-VIP.md) | 1/1 | 96.2% (25/26) | 79.6% (532/668) | 100.0% (8/8) | - | - |
| [Smartcard_ISO7816-UVM-VIP](test_suites/Smartcard_ISO7816-UVM-VIP.md) | 1/1 | 94.1% (128/136) | 70.4% (362/514) | 89.4% (76/85) | 100.0% (1/1) | 10.5% (2/19) |
| [SpaceWire-UVM-VIP](test_suites/SpaceWire-UVM-VIP.md) | 1/1 | 98.1% (51/52) | 81.9% (295/360) | 93.8% (45/48) | 100.0% (4/4) | 89.7% (26/29) |
| [T1S_PLCA-UVM-VIP](test_suites/T1S_PLCA-UVM-VIP.md) | 1/1 | 100.0% (27/27) | 85.0% (153/180) | 98.0% (48/49) | 100.0% (2/2) | 100.0% (8/8) |
| [TDM-UVM-VIP](test_suites/TDM-UVM-VIP.md) | 1/1 | 100.0% (12/12) | 99.8% (543/544) | 88.9% (8/9) | 75.0% (3/4) | 80.0% (12/15) |
| [TileLink-VIP](test_suites/TileLink-VIP.md) | 1/1 | 100.0% (13/13) | 82.0% (287/350) | 100.0% (5/5) | - | 93.8% (30/32) |
| [ToggleNAND-VIP](test_suites/ToggleNAND-VIP.md) | 1/1 | 93.9% (46/49) | 42.1% (106/252) | 92.7% (38/41) | - | - |
| [TypeC-VIP](test_suites/TypeC-VIP.md) | 1/1 | 88.9% (8/9) | 100.0% (18/18) | 100.0% (2/2) | - | - |
| [UART-VIP](test_suites/UART-VIP.md) | 1/1 | 90.0% (18/20) | 90.0% (9/10) | 100.0% (4/4) | - | - |
| [UEC-VIP](test_suites/UEC-VIP.md) | 1/1 | 100.0% (4/4) | 13.5% (566/4204) | 100.0% (12/12) | 100.0% (2/2) | 100.0% (7/7) |
| [UFS-VIP](test_suites/UFS-VIP.md) | 1/1 | 86.5% (45/52) | 56.9% (247/434) | 96.3% (26/27) | 96.9% (31/32) | 10.1% (127/1253) |
| [USB-VIP](test_suites/USB-VIP.md) | 1/1 | 93.9% (31/33) | 54.3% (125/230) | 96.3% (26/27) | - | - |
| [USB2-VIP](test_suites/USB2-VIP.md) | 1/1 | 93.9% (31/33) | 61.7% (111/180) | 92.6% (25/27) | - | - |
| [USB3-VIP](test_suites/USB3-VIP.md) | 1/1 | 94.9% (37/39) | 59.1% (78/132) | 95.2% (20/21) | - | - |
| [USB4-VIP](test_suites/USB4-VIP.md) | 1/1 | 91.4% (32/35) | 78.7% (118/150) | 100.0% (11/11) | - | - |
| [USB_PD-VIP](test_suites/USB_PD-VIP.md) | 1/1 | 96.4% (27/28) | 70.3% (121/172) | 100.0% (30/30) | - | - |
| [USXGMII-UVM-VIP](test_suites/USXGMII-UVM-VIP.md) | 1/1 | 100.0% (49/49) | 97.4% (567/582) | 100.0% (24/24) | 100.0% (3/3) | 97.4% (38/39) |
| [VbyOne_HS-UVM-VIP](test_suites/VbyOne_HS-UVM-VIP.md) | 1/1 | 97.1% (34/35) | 92.6% (250/270) | 95.2% (20/21) | 100.0% (1/1) | 83.3% (5/6) |
| [WTB-UVM-VIP](test_suites/WTB-UVM-VIP.md) | 1/1 | 100.0% (3/3) | 20.0% (16/80) | 100.0% (8/8) | 100.0% (2/2) | 100.0% (5/5) |
| [Wishbone-UVM-VIP](test_suites/Wishbone-UVM-VIP.md) | 2/2 | 100.0% (9/9) | 95.6% (1174/1228) | 100.0% (18/18) | 100.0% (2/2) | 100.0% (50/50) |
| [XGMII-UVM-VIP](test_suites/XGMII-UVM-VIP.md) | 1/1 | 100.0% (3/3) | 99.3% (147/148) | 100.0% (2/2) | 100.0% (2/2) | 8.7% (6/69) |
| [eCPRI-VIP](test_suites/eCPRI-VIP.md) | 1/1 | 91.9% (34/37) | 70.8% (358/506) | 100.0% (17/17) | - | - |
| [eMMC-VIP](test_suites/eMMC-VIP.md) | 1/1 | 92.7% (89/96) | 56.6% (738/1304) | 84.1% (58/69) | 97.0% (32/33) | 11.2% (126/1120) |
| [eMMC_Device-UVM-VIP](test_suites/eMMC_Device-UVM-VIP.md) | 1/1 | 98.0% (97/99) | 92.3% (1078/1168) | 86.4% (57/66) | 100.0% (1/1) | 31.2% (5/16) |
| [eSPI-UVM-VIP](test_suites/eSPI-UVM-VIP.md) | 1/1 | 100.0% (78/78) | 25.5% (444/1744) | 100.0% (39/39) | 100.0% (2/2) | 94.6% (35/37) |
| [eUSB2-VIP](test_suites/eUSB2-VIP.md) | 1/1 | 97.0% (32/33) | 81.8% (72/88) | 92.3% (24/26) | - | - |
| [gddr5-VIP](test_suites/gddr5-VIP.md) | 1/1 | 85.7% (12/14) | 67.9% (186/274) | 58.3% (7/12) | - | - |
| [gddr6-VIP](test_suites/gddr6-VIP.md) | 1/1 | 85.7% (12/14) | 67.9% (186/274) | 58.3% (7/12) | - | - |
| [gddr7-VIP](test_suites/gddr7-VIP.md) | 1/1 | 85.7% (12/14) | 67.9% (186/274) | 58.3% (7/12) | - | - |
| [hbm2-VIP](test_suites/hbm2-VIP.md) | 1/1 | 85.7% (12/14) | 67.9% (186/274) | 58.3% (7/12) | - | - |
| [hbm3-VIP](test_suites/hbm3-VIP.md) | 1/1 | 84.4% (135/160) | 40.5% (1841/4550) | 79.4% (77/97) | 100.0% (4/4) | 100.0% (56/56) |
| [hbm4-VIP](test_suites/hbm4-VIP.md) | 1/1 | 85.7% (12/14) | 67.9% (186/274) | 58.3% (7/12) | - | - |
| [lpddr5-VIP](test_suites/lpddr5-VIP.md) | 1/1 | 85.7% (12/14) | 67.9% (186/274) | 58.3% (7/12) | - | - |
| [lpddr5x-VIP](test_suites/lpddr5x-VIP.md) | 1/1 | 100.0% (35/35) | 26.1% (397/1522) | 96.4% (27/28) | - | - |
| [xSPI-UVM-VIP](test_suites/xSPI-UVM-VIP.md) | 1/1 | 96.1% (49/51) | 30.1% (237/788) | 86.4% (51/59) | 100.0% (2/2) | 85.7% (24/28) |

## 4. Line coverage 低於 90% 的 VIP

未執行到的行號可對照 `build/cov/<VIP>/annotated/`（`%000000` 開頭的行）。大多是 model 的錯誤處理，或未被測試觸發的協定模式。

| VIP | Line | 未執行到的行 |
|---|---|---|
| I3C-VIP | 81.0% | dut_i3c_target_model.sv:40-41,48,79,104,111,128-129,135,137,139,141,166,170,196,203,205,211-212,214,220,222,226,242,258 |
| I2C-VIP | 82.8% | dut_i2c_slave_model.sv:52,54-55,82 |
| hbm3-VIP | 84.4% | dut_hbm3_dev_model.sv:62,141,148,175,208,220-221,229-230,236-239,242,252,261,270,272,274,277,284,296-297,312,321 |
| RVFI-UVM-VIP | 85.0% | dut_rvfi_model.sv:108,133-134,136-137,150-154,198,203 |
| CAN-VIP | 85.6% | dut_can_node_model.sv:83,87,91,93,121,133,165,174,250,259,262,271,284,334 |
| gddr5-VIP | 85.7% | dut_gddr5_mem_model.sv:64 |
| gddr6-VIP | 85.7% | dut_gddr6_mem_model.sv:64 |
| gddr7-VIP | 85.7% | dut_gddr7_mem_model.sv:64 |
| hbm2-VIP | 85.7% | dut_hbm2_mem_model.sv:64 |
| hbm4-VIP | 85.7% | dut_hbm4_mem_model.sv:64 |
| lpddr5-VIP | 85.7% | dut_lpddr5_mem_model.sv:64 |
| JESD204-VIP | 86.1% | dut_jesd204_adc_dut.sv:31,33-35,132 |
| Ethernet_AVB_TSN-VIP | 86.5% | dut_eth_avb_tsn_dut.sv:120,130,136-137,144 |
| UFS-VIP | 86.5% | dut_ufs_device_dut.sv:45-49,79,144 |
| SATA-VIP | 87.5% | dut_sata_host_model.sv:50,61,64 |
| SPI-VIP | 88.0% | dut_spi_slave_model.sv:43,46,64 |
| I2S-VIP | 88.5% | dut_i2s_receiver_loopback.sv:28,31,69 |
| LIN-VIP | 88.6% | dut_lin_slave_model.sv:55,57-59,101,147,224,241,268,275 |
| DDR5-VIP | 88.8% | dut_ddr5_ca_decoder.sv:93,111,118,122; dut_ddr5_dev_model.sv:108,111,123,137-138,149,157,163,174-177,179,187-188,190-191,194-195,202,214 |
| TypeC-VIP | 88.9% | dut_typec_partner_model.sv:49 |

### Functional coverage 未命中的 bins

| VIP | Functional | 未命中 bins（covergroup.coverpoint(數量)） |
|---|---|---|
| ACE-UVM-VIP | 81.8% (36/44) | ace_pkg::ace_coverage::ace_cg.cp_cmd(1); ace_pkg::ace_coverage::ace_cg.cp_rs(1); ace_pkg::ace_coverage::ace_cg.cp_ru(1); ace_pkg::ace_coverage::ace_cg.x_snoop_cr(5) |
| ACE_Lite-UVM-VIP | 100.0% (22/22) | - |
| AHB-VIP | 93.3% (83/89) | ahb_protocol_checker_sva.cg_ahb.cg_ahb(2); amba_vip_if.cg_amba_ahb.cg_amba_ahb(1); amba_vip_pkg::ahb_coverage::cg_fsm.cp_state(1); amba_vip_pkg::ahb_coverage::cg_fsm.cp_trans(1); amba_vip_pkg::ahb_coverage::cg_protocol.cp_burst(1) |
| APB-VIP | 96.6% (86/89) | amba_vip_if.cg_amba_apb.cg_amba_apb(1); apb_protocol_checker_sva.cg_apb.cg_apb(2) |
| ATB-UVM-VIP | 100.0% (5/5) | - |
| AVSBus-VIP | 15.4% (21/136) | avsbus_pkg::avsbus_coverage::cg_error.cp_illegal(1); avsbus_pkg::avsbus_coverage::cg_error.cp_no_resp(1); avsbus_pkg::avsbus_coverage::cg_error.cx_op_status(2); avsbus_pkg::avsbus_coverage::cg_fsm.cp_state(3); avsbus_pkg::avsbus_coverage::cg_fsm.cp_trans(3); avsbus_pkg::avsbus_coverage::cg_protocol.cp_opcode(14); avsbus_pkg::avsbus_coverage::cg_protocol.cp_resp(1); avsbus_pkg::avsbus_coverage::cg_protocol.cx_op_resp(30); avsbus_pkg::avsbus_coverage::cg_protocol.cx_op_volt(60) |
| AXI-VIP | 93.2% (205/220) | amba_vip_if.cg_amba_axi.cg_amba_axi(1); amba_vip_pkg::amba_cov::cg_axi.cp_prot(1); amba_vip_pkg::amba_cov::cg_axi.cp_resp(2); amba_vip_pkg::amba_cov::cg_axi.cp_size(1); amba_vip_pkg::amba_cov::cg_axi.cross_burst_len(1); amba_vip_pkg::axi_coverage::cg_protocol.cp_resp(1); amba_vip_pkg::axi_coverage::cg_protocol.cx_burst_len(1); axi_protocol_checker_sva.cg_axi.cg_axi(7) |
| AXI4_Lite-UVM-VIP | 92.9% (39/42) | axi4_lite_pkg::axi4_lite_coverage::axi4_lite_cg.cp_resp(1); axi4_lite_pkg::axi4_lite_coverage::axi4_lite_cg.x_priv(2) |
| AXI_Stream-UVM-VIP | 8.4% (29/344) | axi_stream_pkg::axi_stream_coverage::axi_stream_cg.cp_tail(63); axi_stream_pkg::axi_stream_coverage::axi_stream_cg.x_len_tail(252) |
| Avalon_MM-UVM-VIP | 100.0% (11/11) | - |
| Avalon_ST-UVM-VIP | 100.0% (3/3) | - |
| BoW-UVM-VIP | 100.0% (20/20) | - |
| CAN_FD-UVM-VIP | 87.5% (7/8) | can_fd_pkg::can_fd_coverage::can_fd_cg.cp_serr(1) |
| CAN_XL-UVM-VIP | 81.1% (30/37) | can_xl_pkg::can_xl_coverage::can_xl_cg.x_err_len(7) |
| CHI-UVM-VIP | 100.0% (6/6) | - |
| CHI_H-UVM-VIP | 100.0% (34/34) | - |
| CI_CAM-UVM-VIP | 6.2% (2/32) | cam_pkg::cam_coverage::cam_cg.cp_kind(15); cam_pkg::cam_coverage::cam_cg.cp_tim(15) |
| DDR-VIP | 97.1% (102/105) | memory_coverage_pkg::ddr_coverage::ddr_bank_state_cg.cmd(1); memory_coverage_pkg::ddr_coverage::ddr_bank_state_cg.state_x_cmd(1); memory_coverage_pkg::ddr_coverage::ddr_cmd_cg.cmd(1) |
| DDR5-VIP | 100.0% (46/46) | - |
| ETH800G-VIP | 100.0% (9/9) | - |
| EtherCAT-VIP | 100.0% (8/8) | - |
| GMII-UVM-VIP | 100.0% (5/5) | - |
| GMII_PHY-UVM-VIP | 100.0% (12/12) | - |
| GPIO-UVM-VIP | 100.0% (6/6) | - |
| HBM-VIP | 93.3% (97/104) | memory_coverage_pkg::hbm_coverage::hbm_bank_state_cg.cmd(1); memory_coverage_pkg::hbm_coverage::hbm_bank_state_cg.state_x_cmd(1); memory_coverage_pkg::hbm_coverage::hbm_cmd_cg.burst(4); memory_coverage_pkg::hbm_coverage::hbm_cmd_cg.cmd(1) |
| HBM3E-VIP | 100.0% (17/17) | - |
| HyperBus-UVM-VIP | 89.3% (25/28) | hyperbus_pkg::hyperbus_coverage::hyperbus_cg.cp_lat(3) |
| I2C-VIP | 31.4% (11/35) | i2c_pkg::i2c_coverage::cg_error.cp_addr_nack(1); i2c_pkg::i2c_coverage::cg_fsm.cp_state(6); i2c_pkg::i2c_coverage::cg_fsm.cp_trans(6); i2c_pkg::i2c_coverage::cg_protocol.cp_addr(1); i2c_pkg::i2c_coverage::cg_protocol.cp_len(3); i2c_pkg::i2c_coverage::cg_protocol.cx_dir_len(7) |
| I2S_Codec-UVM-VIP | 100.0% (7/7) | - |
| IO_Link-VIP | 100.0% (9/9) | - |
| IR_Remote-UVM-VIP | 100.0% (12/12) | - |
| LPDDR-VIP | 94.0% (109/116) | memory_coverage_pkg::lpddr_coverage::lpddr_addr_cg.row(2); memory_coverage_pkg::lpddr_coverage::lpddr_bank_state_cg.state_x_cmd(1); memory_coverage_pkg::lpddr_coverage::lpddr_cmd_cg.cmd_x_ca(4) |
| LPDDR6-VIP | 100.0% (19/19) | - |
| MACsec-UVM-VIP | 100.0% (19/19) | - |
| MCTP-UVM-VIP | 90.9% (30/33) | mctp_pkg::mctp_coverage::mctp_cg.cp_type(1); mctp_pkg::mctp_coverage::mctp_cg.x_err_n(2) |
| MDIO-UVM-VIP | 100.0% (8/8) | - |
| MIL_STD_1553-VIP | 100.0% (9/9) | - |
| MPEG_TS-UVM-VIP | 100.0% (15/15) | - |
| NC-SI-UVM-VIP | 100.0% (26/26) | - |
| NVMe-VIP | 7.0% (27/384) | nvme_pkg::nvme_coverage::nvme_cmd_cg.__cross63(22); nvme_pkg::nvme_coverage::nvme_cmd_cg.__cross64(21); nvme_pkg::nvme_coverage::nvme_cmd_cg.__cross65(22); nvme_pkg::nvme_coverage::nvme_cmd_cg.fuse_cp(2); nvme_pkg::nvme_coverage::nvme_cmd_cg.nlb_cp(2); nvme_pkg::nvme_coverage::nvme_cmd_cg.nsid_cp(2); nvme_pkg::nvme_coverage::nvme_cmd_cg.opcode_cp(10); nvme_pkg::nvme_coverage::nvme_data_cg.__cross66(5); nvme_pkg::nvme_coverage::nvme_data_cg.cdw10_cp(2); nvme_pkg::nvme_coverage::nvme_data_cg.len_cp(2); nvme_pkg::nvme_coverage::nvme_fsm_cg.cmd_trans_cp(13); nvme_pkg::nvme_coverage::nvme_status_cg.status_cp(254) |
| OBI-UVM-VIP | 81.8% (27/33) | obi_pkg::obi_coverage::obi_cg.x_we_be(6) |
| OCP-VIP | 93.1% (27/29) | ocp_pkg::ocp_coverage::cg_fsm.cp_trans(2) |
| ONFI-VIP | 13.2% (68/515) | memory_coverage_pkg::ddr_coverage::ddr_cg.cmd(63); memory_coverage_pkg::emmc_coverage::emmc_cg.cmd(63); memory_coverage_pkg::hbm_coverage::hbm_cg.cmd(63); memory_coverage_pkg::lpddr_coverage::lpddr_cg.cmd(63); memory_coverage_pkg::onfi_coverage::onfi_cfg_cg.cx_cmd_len(4); memory_coverage_pkg::onfi_coverage::onfi_data_cg.cx_fail_mode(2); memory_coverage_pkg::sd_coverage::sd_cg.cmd(63); memory_coverage_pkg::ufs_coverage::ufs_cg.cmd(63); memory_coverage_pkg::unipro_coverage::unipro_cg.cmd(63) |
| OneWire-UVM-VIP | 100.0% (5/5) | - |
| PTP-VIP | 100.0% (2/2) | - |
| PWM-UVM-VIP | 100.0% (7/7) | - |
| RGMII-UVM-VIP | 100.0% (3/3) | - |
| RVFI-UVM-VIP | 81.7% (49/60) | rvfi_pkg::rvfi_coverage::rvfi_cg.cp_alu(3); rvfi_pkg::rvfi_coverage::rvfi_cg.cp_lsize(2); rvfi_pkg::rvfi_coverage::rvfi_cg.cp_ssize(3); rvfi_pkg::rvfi_coverage::rvfi_cg.x_op_trap(3) |
| RapidIO-VIP | 100.0% (7/7) | - |
| SATA-VIP | 20.8% (22/106) | sata_pkg::sata_coverage::sata_data_cg.__cross65(4); sata_pkg::sata_coverage::sata_data_cg.dw0_cp(2); sata_pkg::sata_coverage::sata_data_cg.psize_cp(2); sata_pkg::sata_coverage::sata_error_cg.__cross64(2); sata_pkg::sata_coverage::sata_error_cg.crc_error_cp(1); sata_pkg::sata_coverage::sata_fis_cg.__cross62(28); sata_pkg::sata_coverage::sata_fis_cg.__cross63(23); sata_pkg::sata_coverage::sata_fis_cg.fis_type_cp(7); sata_pkg::sata_coverage::sata_fis_cg.link_speed_cp(2); sata_pkg::sata_coverage::sata_fis_cg.payload_size_cp(4); sata_pkg::sata_coverage::sata_fsm_cg.fis_trans_cp(7); sata_pkg::sata_coverage::sata_fsm_cg.speed_cp(2) |
| SCCB_Sensor-UVM-VIP | 100.0% (9/9) | - |
| SD-VIP | 11.1% (103/932) | memory_coverage_pkg::ddr_coverage::ddr_cg.bank(8); memory_coverage_pkg::ddr_coverage::ddr_cg.bank_group(4); memory_coverage_pkg::ddr_coverage::ddr_cg.burst_len(4); memory_coverage_pkg::ddr_coverage::ddr_cg.cmd(16); memory_coverage_pkg::ddr_coverage::ddr_cg.cmd_x_bank(128); memory_coverage_pkg::emmc_coverage::emmc_cg.bw(3); memory_coverage_pkg::emmc_coverage::emmc_cg.cmd(13); memory_coverage_pkg::emmc_coverage::emmc_cg.cmd_x_bw(28); memory_coverage_pkg::emmc_coverage::emmc_data_cg.addr(4); memory_coverage_pkg::emmc_coverage::emmc_data_cg.blen(4); memory_coverage_pkg::emmc_coverage::emmc_data_cg.blen_x_addr(13); memory_coverage_pkg::emmc_coverage::emmc_data_cg.resp_err(2); memory_coverage_pkg::emmc_coverage::emmc_fsm_cg.bw_t(3); memory_coverage_pkg::emmc_coverage::emmc_fsm_cg.seq_t(6); memory_coverage_pkg::emmc_coverage::emmc_fsm_cg.seq_x_bw(18); memory_coverage_pkg::hbm_coverage::hbm_cg.bank(4); memory_coverage_pkg::hbm_coverage::hbm_cg.cid(8); memory_coverage_pkg::hbm_coverage::hbm_cg.cmd(16); memory_coverage_pkg::hbm_coverage::hbm_cg.cmd_x_cid(128); memory_coverage_pkg::lpddr_coverage::lpddr_cg.bank(8); memory_coverage_pkg::lpddr_coverage::lpddr_cg.cmd(16); memory_coverage_pkg::lpddr_coverage::lpddr_cg.cmd_x_bank(128); memory_coverage_pkg::onfi_coverage::onfi_cg.cmd(64); memory_coverage_pkg::ufs_coverage::ufs_cg.cmd_x_lun(57); memory_coverage_pkg::ufs_coverage::ufs_cg.lun(8); memory_coverage_pkg::ufs_coverage::ufs_cg.opcode(5); memory_coverage_pkg::ufs_coverage::ufs_cg.upiu(8); memory_coverage_pkg::ufs_coverage::ufs_data_cg.dlen(6); memory_coverage_pkg::ufs_coverage::ufs_data_cg.lba(3); memory_coverage_pkg::ufs_coverage::ufs_data_cg.len_x_lba(15); memory_coverage_pkg::ufs_coverage::ufs_data_cg.status(3); memory_coverage_pkg::ufs_coverage::ufs_fsm_cg.lun_t(2); memory_coverage_pkg::ufs_coverage::ufs_fsm_cg.trans(7); memory_coverage_pkg::ufs_coverage::ufs_fsm_cg.trans_x_lun(14); memory_coverage_pkg::unipro_coverage::unipro_cg.cport(8); memory_coverage_pkg::unipro_coverage::unipro_cg.msg(4); memory_coverage_pkg::unipro_coverage::unipro_cg.msg_x_cport(32); memory_coverage_pkg::unipro_coverage::unipro_credit_cg.cred(3); memory_coverage_pkg::unipro_coverage::unipro_credit_cg.cred_x_msg(12); memory_coverage_pkg::unipro_coverage::unipro_credit_cg.msg(4); memory_coverage_pkg::unipro_coverage::unipro_fsm_cg.msg_trans(3); memory_coverage_pkg::unipro_coverage::unipro_fsm_cg.msg_x_tc(6); memory_coverage_pkg::unipro_coverage::unipro_fsm_cg.tc(3) |
| SDIO-UVM-VIP | 83.3% (5/6) | sdio_pkg::sdio_coverage::sdio_cg.cp_cmd(1) |
| SDMMC_Card-UVM-VIP | 26.1% (6/23) | sdm_pkg::sdm_coverage::sdm_cg.cp_got(1); sdm_pkg::sdm_coverage::sdm_cg.cp_idx(16) |
| SD_Card-UVM-VIP | 25.0% (4/16) | sdc_pkg::sdc_coverage::sdc_cg.cp_got(1); sdc_pkg::sdc_coverage::sdc_cg.cp_idx(10); sdc_pkg::sdc_coverage::sdc_cg.cp_len(1) |
| SENT-VIP | 90.6% (29/32) | sent_pkg::sent_coverage::sent_cg.cp_d0(3) |
| SGMII-UVM-VIP | 100.0% (13/13) | - |
| SMBus-UVM-VIP | 90.6% (29/32) | smbus_pkg::smbus_coverage::smbus_cg.x_kind_pec(3) |
| SPDIF-UVM-VIP | 90.0% (9/10) | spdif_pkg::spdif_coverage::spdif_cg.cp_first(1) |
| SPDM-UVM-VIP | 87.8% (43/49) | spdm_pkg::spdm_coverage::spdm_cg.cx_req_err(6) |
| SPI_NOR-UVM-VIP | 100.0% (17/17) | - |
| SUE-UVM-VIP | 100.0% (14/14) | - |
| Smartcard_ISO7816-UVM-VIP | 10.5% (2/19) | scd_pkg::scd_coverage::scd_cg.cp_kind(13); scd_pkg::scd_coverage::scd_cg.cp_sw1(4) |
| SpaceWire-UVM-VIP | 89.7% (26/29) | spacewire_pkg::spacewire_coverage::spacewire_cg.cp_flags(1); spacewire_pkg::spacewire_coverage::spacewire_cg.x_len_fault(2) |
| T1S_PLCA-UVM-VIP | 100.0% (8/8) | - |
| TDM-UVM-VIP | 80.0% (12/15) | tdm_pkg::tdm_coverage::tdm_cg.cp_gap(1); tdm_pkg::tdm_coverage::tdm_cg.x_gap_err(2) |
| TileLink-VIP | 93.8% (30/32) | tilelink_pkg::tilelink_coverage::cg_protocol.cx_op_dop(2) |
| UEC-VIP | 100.0% (7/7) | - |
| UFS-VIP | 10.1% (127/1253) | memory_coverage_pkg::ddr_coverage::ddr_cg.bank(8); memory_coverage_pkg::ddr_coverage::ddr_cg.bank_group(4); memory_coverage_pkg::ddr_coverage::ddr_cg.burst_len(4); memory_coverage_pkg::ddr_coverage::ddr_cg.cmd(16); memory_coverage_pkg::ddr_coverage::ddr_cg.cmd_x_bank(128); memory_coverage_pkg::emmc_coverage::emmc_cg.bw(3); memory_coverage_pkg::emmc_coverage::emmc_cg.cmd(64); memory_coverage_pkg::emmc_coverage::emmc_cg.cmd_x_bw(192); memory_coverage_pkg::hbm_coverage::hbm_cg.bank(4); memory_coverage_pkg::hbm_coverage::hbm_cg.cid(8); memory_coverage_pkg::hbm_coverage::hbm_cg.cmd(16); memory_coverage_pkg::hbm_coverage::hbm_cg.cmd_x_cid(128); memory_coverage_pkg::lpddr_coverage::lpddr_cg.bank(8); memory_coverage_pkg::lpddr_coverage::lpddr_cg.cmd(16); memory_coverage_pkg::lpddr_coverage::lpddr_cg.cmd_x_bank(128); memory_coverage_pkg::onfi_coverage::onfi_cg.cmd(64); memory_coverage_pkg::sd_coverage::sd_cg.bw(3); memory_coverage_pkg::sd_coverage::sd_cg.cmd(64); memory_coverage_pkg::sd_coverage::sd_cg.cmd_x_bw(192); memory_coverage_pkg::ufs_coverage::ufs_data_cg.status(1); memory_coverage_pkg::unipro_coverage::unipro_cg.cport(8); memory_coverage_pkg::unipro_coverage::unipro_cg.msg(4); memory_coverage_pkg::unipro_coverage::unipro_cg.msg_x_cport(32); memory_coverage_pkg::unipro_coverage::unipro_credit_cg.cred(3); memory_coverage_pkg::unipro_coverage::unipro_credit_cg.cred_x_msg(12); memory_coverage_pkg::unipro_coverage::unipro_credit_cg.msg(4); memory_coverage_pkg::unipro_coverage::unipro_fsm_cg.msg_trans(3); memory_coverage_pkg::unipro_coverage::unipro_fsm_cg.msg_x_tc(6); memory_coverage_pkg::unipro_coverage::unipro_fsm_cg.tc(3) |
| USXGMII-UVM-VIP | 97.4% (38/39) | usxgmii_pkg::usxgmii_coverage::usxgmii_cg.x_speed_fault(1) |
| VbyOne_HS-UVM-VIP | 83.3% (5/6) | vbo_pkg::vbo_coverage::vbo_cg.cp_fill(1) |
| WTB-UVM-VIP | 100.0% (5/5) | - |
| Wishbone-UVM-VIP | 100.0% (50/50) | - |
| XGMII-UVM-VIP | 8.7% (6/69) | xgmii_pkg::xgmii_coverage::xgmii_cg.cp_end(63) |
| eMMC-VIP | 11.2% (126/1120) | memory_coverage_pkg::ddr_coverage::ddr_cg.bank(8); memory_coverage_pkg::ddr_coverage::ddr_cg.bank_group(4); memory_coverage_pkg::ddr_coverage::ddr_cg.burst_len(4); memory_coverage_pkg::ddr_coverage::ddr_cg.cmd(16); memory_coverage_pkg::ddr_coverage::ddr_cg.cmd_x_bank(128); memory_coverage_pkg::hbm_coverage::hbm_cg.bank(4); memory_coverage_pkg::hbm_coverage::hbm_cg.cid(8); memory_coverage_pkg::hbm_coverage::hbm_cg.cmd(16); memory_coverage_pkg::hbm_coverage::hbm_cg.cmd_x_cid(128); memory_coverage_pkg::lpddr_coverage::lpddr_cg.bank(8); memory_coverage_pkg::lpddr_coverage::lpddr_cg.cmd(16); memory_coverage_pkg::lpddr_coverage::lpddr_cg.cmd_x_bank(128); memory_coverage_pkg::onfi_coverage::onfi_cg.cmd(64); memory_coverage_pkg::sd_coverage::sd_cg.bw(3); memory_coverage_pkg::sd_coverage::sd_cg.cmd(64); memory_coverage_pkg::sd_coverage::sd_cg.cmd_x_bw(192); memory_coverage_pkg::ufs_coverage::ufs_cg.cmd_x_lun(57); memory_coverage_pkg::ufs_coverage::ufs_cg.lun(8); memory_coverage_pkg::ufs_coverage::ufs_cg.opcode(5); memory_coverage_pkg::ufs_coverage::ufs_cg.upiu(8); memory_coverage_pkg::ufs_coverage::ufs_data_cg.dlen(6); memory_coverage_pkg::ufs_coverage::ufs_data_cg.lba(3); memory_coverage_pkg::ufs_coverage::ufs_data_cg.len_x_lba(15); memory_coverage_pkg::ufs_coverage::ufs_data_cg.status(3); memory_coverage_pkg::ufs_coverage::ufs_fsm_cg.lun_t(2); memory_coverage_pkg::ufs_coverage::ufs_fsm_cg.trans(7); memory_coverage_pkg::ufs_coverage::ufs_fsm_cg.trans_x_lun(14); memory_coverage_pkg::unipro_coverage::unipro_cg.cport(8); memory_coverage_pkg::unipro_coverage::unipro_cg.msg(4); memory_coverage_pkg::unipro_coverage::unipro_cg.msg_x_cport(32); memory_coverage_pkg::unipro_coverage::unipro_credit_cg.cred(3); memory_coverage_pkg::unipro_coverage::unipro_credit_cg.cred_x_msg(12); memory_coverage_pkg::unipro_coverage::unipro_credit_cg.msg(4); memory_coverage_pkg::unipro_coverage::unipro_fsm_cg.msg_trans(3); memory_coverage_pkg::unipro_coverage::unipro_fsm_cg.msg_x_tc(6); memory_coverage_pkg::unipro_coverage::unipro_fsm_cg.tc(3) |
| eMMC_Device-UVM-VIP | 31.2% (5/16) | emd_pkg::emd_coverage::emd_cg.cp_got(1); emd_pkg::emd_coverage::emd_cg.cp_idx(9); emd_pkg::emd_coverage::emd_cg.cp_len(1) |
| eSPI-UVM-VIP | 94.6% (35/37) | espi_pkg::espi_coverage::espi_cg.x_cls_code(2) |
| hbm3-VIP | 100.0% (56/56) | - |
| xSPI-UVM-VIP | 85.7% (24/28) | xspi_pkg::xspi_coverage::xspi_cg.x_op_ext(4) |

## 5. 備註

- **CHI-UVM-VIP**：func_chi_hn_tb.sv: SKIP pinned to Icarus
- **Ethernet_AVB_TSN-VIP**：func_avb_tsn_tb.sv: FAIL fails under coverage: [FAIL] fixed store-and-forward delay: tx SOF 8 clocks after the last rx beat \| FUNC_FAIL checks=23 fails=1
- **SpaceWire-UVM-VIP**：smoke_func_tb.sv: FAIL fails under coverage: [FAIL] first bit out 42 clocks after reset \| FUNC_FAIL checks=38 fails=1

## 6. 重跑

```bash
bash tools/install_tools.sh && export PATH=/opt/verilator-5.054/bin:$PATH
bash tools/extract_vips.sh
python3 tools/coverage.py -j 2        # coverage_report.csv, build/cov/<VIP>/
python3 tools/coverage.py APB-VIP     # 單一 VIP
python3 tools/gen_coverage_doc.py     # docs/COVERAGE.md
```
