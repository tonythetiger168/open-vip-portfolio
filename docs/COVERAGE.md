# VIP Portfolio Coverage 報告

> 由 `tools/gen_coverage_doc.py` 依 `coverage_report.csv`（`tools/coverage.py`，Verilator 5.052 `--coverage`）自動產生，請勿手動修改。

## 1. 結論

- 132 個 VIP 中 131 個量到 code coverage（149 個功能測試中 148 個在 Verilator 上帶 coverage 執行）。
- Line / branch coverage（全部 DUT model 合計）：94.6%（3467/3664）。
- Toggle coverage（全部 DUT model 合計）：55.0%（46247/84132）。
- Expression coverage（全部 DUT model 合計）：92.8%（2502/2695）。
- Line coverage 100% 的 VIP 63 個，≥ 90% 的 117 個，低於 90% 的 14 個（見第 4 節）。
- Functional coverage（covergroup bins，在 Verilator 上量得的 ACE_Lite-UVM-VIP / AHB-VIP / APB-VIP / ATB-UVM-VIP / AXI-VIP / Avalon_MM-UVM-VIP / Avalon_ST-UVM-VIP / CAN_FD-UVM-VIP / CHI-UVM-VIP / DDR5-VIP / ETH800G-VIP / EtherCAT-VIP / GMII-UVM-VIP / GPIO-UVM-VIP / HBM3E-VIP / IO_Link-VIP / LPDDR6-VIP / MDIO-UVM-VIP / MIL_STD_1553-VIP / OCP-VIP / OneWire-UVM-VIP）：49.0%（364/743），其餘 UVM 環境的 covergroup 需商用模擬器（見第 2 節）。

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
| [ACE-VIP](test_suites/ACE-VIP.md) | 1/1 | 93.5% (58/62) | 88.9% (1003/1128) | 99.1% (112/113) | - | - |
| [ACE_Lite-UVM-VIP](test_suites/ACE_Lite-UVM-VIP.md) | 1/1 | 100.0% (11/11) | 8.0% (183/2282) | 94.4% (17/18) | 100.0% (2/2) | 100.0% (22/22) |
| [ACE_Lite-VIP](test_suites/ACE_Lite-VIP.md) | 1/1 | 95.0% (38/40) | 98.8% (583/590) | 99.0% (97/98) | - | - |
| [AHB-VIP](test_suites/AHB-VIP.md) | 2/2 | 100.0% (13/13) | 56.3% (364/646) | 100.0% (15/15) | 56.2% (9/16) | 38.8% (47/121) |
| [APB-VIP](test_suites/APB-VIP.md) | 2/2 | 100.0% (19/19) | 37.8% (196/518) | 100.0% (19/19) | 100.0% (14/14) | 47.7% (53/111) |
| [ATB-UVM-VIP](test_suites/ATB-UVM-VIP.md) | 1/1 | 100.0% (3/3) | 20.0% (16/80) | 100.0% (8/8) | 100.0% (2/2) | 100.0% (5/5) |
| [ATB-VIP](test_suites/ATB-VIP.md) | 1/1 | 100.0% (8/8) | 95.9% (1191/1242) | 100.0% (12/12) | - | - |
| [AVSBus-VIP](test_suites/AVSBus-VIP.md) | 1/1 | 95.7% (22/23) | 64.3% (18/28) | 87.5% (14/16) | - | - |
| [AXI-VIP](test_suites/AXI-VIP.md) | 2/2 | 92.1% (35/38) | 61.6% (548/890) | 100.0% (35/35) | 46.7% (7/15) | 22.9% (72/315) |
| [AXI4-VIP](test_suites/AXI4-VIP.md) | 1/1 | 96.7% (58/60) | 99.7% (688/690) | 100.0% (75/75) | - | - |
| [AXI4_Lite-VIP](test_suites/AXI4_Lite-VIP.md) | 1/1 | 95.0% (38/40) | 98.1% (504/514) | 100.0% (36/36) | - | - |
| [AXI_Stream-VIP](test_suites/AXI_Stream-VIP.md) | 1/1 | 100.0% (5/5) | 87.4% (1045/1196) | 100.0% (8/8) | - | - |
| [Avalon_MM-UVM-VIP](test_suites/Avalon_MM-UVM-VIP.md) | 1/1 | 100.0% (10/10) | 91.0% (162/178) | 100.0% (21/21) | 100.0% (2/2) | 100.0% (11/11) |
| [Avalon_MM-VIP](test_suites/Avalon_MM-VIP.md) | 2/2 | 98.0% (49/50) | 95.5% (336/352) | 100.0% (51/51) | - | - |
| [Avalon_ST-UVM-VIP](test_suites/Avalon_ST-UVM-VIP.md) | 2/2 | 100.0% (9/9) | 100.0% (218/218) | 100.0% (13/13) | 100.0% (2/2) | 100.0% (3/3) |
| [Avalon_ST-VIP](test_suites/Avalon_ST-VIP.md) | 1/1 | 100.0% (4/4) | 99.8% (1192/1194) | 100.0% (9/9) | - | - |
| [Bluetooth5-VIP](test_suites/Bluetooth5-VIP.md) | 1/1 | 95.8% (23/24) | 34.7% (131/378) | 90.9% (10/11) | - | - |
| [CAN-VIP](test_suites/CAN-VIP.md) | 1/1 | 89.6% (86/96) | 74.5% (891/1196) | 95.5% (42/44) | - | - |
| [CAN_FD-UVM-VIP](test_suites/CAN_FD-UVM-VIP.md) | 1/1 | 100.0% (11/11) | 75.0% (24/32) | 100.0% (9/9) | 100.0% (2/2) | 87.5% (7/8) |
| [CCIX-VIP](test_suites/CCIX-VIP.md) | 1/1 | 91.7% (11/12) | 73.4% (207/282) | 85.7% (6/7) | - | - |
| [CHI-UVM-VIP](test_suites/CHI-UVM-VIP.md) | 1/1 | 91.7% (11/12) | 30.2% (70/232) | 100.0% (2/2) | 100.0% (2/2) | 100.0% (6/6) |
| [CHI-VIP](test_suites/CHI-VIP.md) | 2/2 | 94.7% (18/19) | 94.9% (281/296) | 100.0% (14/14) | - | - |
| [CPRI-VIP](test_suites/CPRI-VIP.md) | 1/1 | 94.4% (17/18) | 92.1% (140/152) | 100.0% (9/9) | - | - |
| [CSE-VIP](test_suites/CSE-VIP.md) | 1/1 | 97.7% (43/44) | 20.7% (130/628) | 100.0% (7/7) | - | - |
| [CSI_2-VIP](test_suites/CSI_2-VIP.md) | 1/1 | 100.0% (13/13) | 51.7% (187/362) | 100.0% (10/10) | - | - |
| [CXL-VIP](test_suites/CXL-VIP.md) | 1/1 | 100.0% (15/15) | 88.1% (1026/1164) | 100.0% (4/4) | - | - |
| [CXS-VIP](test_suites/CXS-VIP.md) | 1/1 | 100.0% (13/13) | 94.3% (164/174) | 100.0% (18/18) | - | - |
| [C_PHY-VIP](test_suites/C_PHY-VIP.md) | 1/1 | 100.0% (13/13) | 51.7% (187/362) | 100.0% (10/10) | - | - |
| [DBI-VIP](test_suites/DBI-VIP.md) | 1/1 | 100.0% (28/28) | 91.2% (62/68) | 100.0% (10/10) | - | - |
| [DDR-VIP](test_suites/DDR-VIP.md) | 1/1 | 100.0% (23/23) | 17.0% (216/1274) | 91.7% (22/24) | - | - |
| [DDR4-VIP](test_suites/DDR4-VIP.md) | 2/2 | 94.7% (36/38) | 94.3% (1090/1156) | 94.4% (17/18) | - | - |
| [DDR5-VIP](test_suites/DDR5-VIP.md) | 2/2 | 100.0% (12/12) | 100.0% (1586/1586) | 100.0% (10/10) | 100.0% (2/2) | 100.0% (17/17) |
| [DFI-VIP](test_suites/DFI-VIP.md) | 1/1 | 96.3% (26/27) | 46.5% (318/684) | 81.8% (9/11) | - | - |
| [DPI-VIP](test_suites/DPI-VIP.md) | 1/1 | 100.0% (20/20) | 66.7% (44/66) | 100.0% (15/15) | - | - |
| [DSI-VIP](test_suites/DSI-VIP.md) | 1/1 | 100.0% (13/13) | 51.7% (187/362) | 100.0% (10/10) | - | - |
| [D_PHY-VIP](test_suites/D_PHY-VIP.md) | 1/1 | 100.0% (13/13) | 51.7% (187/362) | 100.0% (10/10) | - | - |
| [DigRF-VIP](test_suites/DigRF-VIP.md) | 1/1 | 100.0% (30/30) | 78.3% (155/198) | 100.0% (17/17) | - | - |
| [DisplayPort2-VIP](test_suites/DisplayPort2-VIP.md) | 1/1 | 100.0% (26/26) | 43.2% (210/486) | 100.0% (20/20) | - | - |
| [ETH800G-VIP](test_suites/ETH800G-VIP.md) | 2/2 | 100.0% (15/15) | 92.0% (613/666) | 86.4% (19/22) | 100.0% (2/2) | 100.0% (9/9) |
| [EtherCAT-VIP](test_suites/EtherCAT-VIP.md) | 1/1 | 100.0% (5/5) | 32.6% (30/92) | 100.0% (4/4) | 100.0% (2/2) | 87.5% (7/8) |
| [Ethernet-VIP](test_suites/Ethernet-VIP.md) | 2/2 | 95.9% (47/49) | 99.0% (1071/1082) | 87.5% (21/24) | - | - |
| [Ethernet_AVB_TSN-VIP](test_suites/Ethernet_AVB_TSN-VIP.md) | 1/1 | 94.1% (32/34) | 35.5% (236/664) | 90.5% (19/21) | - | - |
| [FC-VIP](test_suites/FC-VIP.md) | 1/1 | 96.4% (54/56) | 97.7% (1081/1106) | 94.6% (35/37) | - | - |
| [FlexRay-VIP](test_suites/FlexRay-VIP.md) | 1/1 | 96.4% (53/55) | 46.8% (550/1174) | 100.0% (16/16) | - | - |
| [GMII-UVM-VIP](test_suites/GMII-UVM-VIP.md) | 1/1 | 100.0% (3/3) | 97.7% (43/44) | 100.0% (2/2) | 100.0% (2/2) | 100.0% (5/5) |
| [GMII-VIP](test_suites/GMII-VIP.md) | 1/1 | 100.0% (15/15) | 99.4% (525/528) | 100.0% (20/20) | - | - |
| [GPIO-UVM-VIP](test_suites/GPIO-UVM-VIP.md) | 1/1 | 100.0% (3/3) | 98.5% (67/68) | 100.0% (2/2) | 100.0% (2/2) | 100.0% (6/6) |
| [GPIO-VIP](test_suites/GPIO-VIP.md) | 1/1 | 100.0% (11/11) | 99.2% (121/122) | 100.0% (25/25) | - | - |
| [HBM-VIP](test_suites/HBM-VIP.md) | 1/1 | 100.0% (23/23) | 23.8% (342/1434) | 95.7% (22/23) | - | - |
| [HBM3E-VIP](test_suites/HBM3E-VIP.md) | 2/2 | 100.0% (13/13) | 100.0% (2610/2610) | 100.0% (10/10) | 100.0% (2/2) | 100.0% (17/17) |
| [HBM5-VIP](test_suites/HBM5-VIP.md) | 1/1 | 100.0% (23/23) | 16.3% (207/1272) | 95.2% (20/21) | - | - |
| [HDCP-VIP](test_suites/HDCP-VIP.md) | 1/1 | 91.7% (44/48) | 71.4% (190/266) | 80.0% (32/40) | - | - |
| [HDMI-VIP](test_suites/HDMI-VIP.md) | 1/1 | 100.0% (25/25) | 100.0% (98/98) | 88.2% (15/17) | - | - |
| [HSI-VIP](test_suites/HSI-VIP.md) | 1/1 | 100.0% (25/25) | 78.1% (153/196) | 100.0% (15/15) | - | - |
| [I2C-VIP](test_suites/I2C-VIP.md) | 1/1 | 95.5% (21/22) | 1.2% (24/2080) | 90.0% (9/10) | - | - |
| [I2S-VIP](test_suites/I2S-VIP.md) | 1/1 | 88.5% (23/26) | 98.2% (110/112) | 92.3% (12/13) | - | - |
| [I3C-VIP](test_suites/I3C-VIP.md) | 1/1 | 85.0% (85/100) | 2.0% (43/2120) | 82.3% (79/96) | - | - |
| [IO_Link-VIP](test_suites/IO_Link-VIP.md) | 1/1 | 96.2% (25/26) | 74.1% (86/116) | 100.0% (8/8) | 100.0% (2/2) | 100.0% (9/9) |
| [Interlaken-VIP](test_suites/Interlaken-VIP.md) | 1/1 | 92.0% (23/25) | 50.5% (278/550) | 100.0% (20/20) | - | - |
| [JESD204-VIP](test_suites/JESD204-VIP.md) | 1/1 | 86.1% (31/36) | 61.6% (90/146) | 100.0% (8/8) | - | - |
| [JTAG-VIP](test_suites/JTAG-VIP.md) | 1/1 | 98.6% (68/69) | 82.4% (216/262) | 100.0% (41/41) | - | - |
| [LIN-VIP](test_suites/LIN-VIP.md) | 1/1 | 90.2% (74/82) | 74.7% (583/780) | 42.2% (19/45) | - | - |
| [LPDDR-VIP](test_suites/LPDDR-VIP.md) | 1/1 | 95.7% (22/23) | 8.0% (94/1170) | 100.0% (3/3) | - | - |
| [LPDDR4-VIP](test_suites/LPDDR4-VIP.md) | 2/2 | 94.7% (36/38) | 96.1% (1289/1342) | 95.5% (21/22) | - | - |
| [LPDDR6-VIP](test_suites/LPDDR6-VIP.md) | 2/2 | 100.0% (14/14) | 100.0% (1080/1080) | 100.0% (12/12) | 100.0% (2/2) | 100.0% (19/19) |
| [LPI-VIP](test_suites/LPI-VIP.md) | 1/1 | 100.0% (10/10) | 100.0% (12/12) | 100.0% (12/12) | - | - |
| [LTI-VIP](test_suites/LTI-VIP.md) | 1/1 | 100.0% (12/12) | 80.9% (304/376) | 100.0% (5/5) | - | - |
| [MDIO-UVM-VIP](test_suites/MDIO-UVM-VIP.md) | 2/2 | 92.6% (25/27) | 95.6% (195/204) | 84.6% (11/13) | 100.0% (2/2) | 100.0% (8/8) |
| [MDIO-VIP](test_suites/MDIO-VIP.md) | 1/1 | 100.0% (23/23) | 56.0% (655/1170) | 96.8% (30/31) | - | - |
| [MIL_STD_1553-VIP](test_suites/MIL_STD_1553-VIP.md) | 1/1 | 100.0% (9/9) | 32.3% (31/96) | 100.0% (6/6) | 100.0% (2/2) | 100.0% (9/9) |
| [M_PHY-VIP](test_suites/M_PHY-VIP.md) | 1/1 | 100.0% (13/13) | 51.7% (187/362) | 100.0% (10/10) | - | - |
| [NVMe-VIP](test_suites/NVMe-VIP.md) | 2/2 | 100.0% (19/19) | 10.4% (282/2720) | 100.0% (14/14) | - | - |
| [OCP-VIP](test_suites/OCP-VIP.md) | 1/1 | 100.0% (16/16) | 85.8% (295/344) | 100.0% (5/5) | - | 93.1% (27/29) |
| [ONFI-VIP](test_suites/ONFI-VIP.md) | 1/1 | 90.5% (86/95) | 83.1% (118/142) | 100.0% (35/35) | - | - |
| [OneWire-UVM-VIP](test_suites/OneWire-UVM-VIP.md) | 1/1 | 90.9% (10/11) | 87.5% (21/24) | 85.7% (6/7) | 100.0% (2/2) | 100.0% (5/5) |
| [OneWire-VIP](test_suites/OneWire-VIP.md) | 2/2 | 97.6% (41/42) | 92.6% (150/162) | 90.9% (20/22) | - | - |
| [PCIe-VIP](test_suites/PCIe-VIP.md) | 1/1 | 100.0% (15/15) | 88.1% (1025/1164) | 100.0% (4/4) | - | - |
| [PTP-VIP](test_suites/PTP-VIP.md) | 1/1 | 100.0% (7/7) | 6.3% (25/398) | 100.0% (5/5) | - | - |
| [PWM-UVM-VIP](test_suites/PWM-UVM-VIP.md) | 1/1 | 100.0% (6/6) | 19.8% (21/106) | 100.0% (9/9) | - | - |
| [PWM-VIP](test_suites/PWM-VIP.md) | 1/1 | 100.0% (11/11) | 92.4% (255/276) | 100.0% (18/18) | - | - |
| [QSPI-VIP](test_suites/QSPI-VIP.md) | 1/1 | 98.0% (49/50) | 97.9% (137/140) | 97.6% (41/42) | - | - |
| [RFFE-VIP](test_suites/RFFE-VIP.md) | 1/1 | 94.3% (33/35) | 4.6% (24/524) | 100.0% (18/18) | - | - |
| [RGMII-UVM-VIP](test_suites/RGMII-UVM-VIP.md) | 1/1 | 100.0% (3/3) | 95.8% (23/24) | 100.0% (2/2) | - | - |
| [RGMII-VIP](test_suites/RGMII-VIP.md) | 1/1 | 100.0% (21/21) | 99.8% (551/552) | 100.0% (22/22) | - | - |
| [RapidIO-VIP](test_suites/RapidIO-VIP.md) | 1/1 | 100.0% (5/5) | 73.0% (111/152) | 100.0% (2/2) | - | - |
| [SAS-VIP](test_suites/SAS-VIP.md) | 1/1 | 91.3% (105/115) | 13.0% (222/1702) | 85.7% (36/42) | - | - |
| [SATA-VIP](test_suites/SATA-VIP.md) | 1/1 | 91.3% (21/23) | 21.6% (66/306) | 72.2% (13/18) | - | - |
| [SD-VIP](test_suites/SD-VIP.md) | 1/1 | 92.2% (95/103) | 40.6% (916/2256) | 83.7% (72/86) | - | - |
| [SDIO-UVM-VIP](test_suites/SDIO-UVM-VIP.md) | 1/1 | 94.1% (16/17) | 95.3% (225/236) | 88.9% (8/9) | - | - |
| [SDIO-VIP](test_suites/SDIO-VIP.md) | 1/1 | 95.0% (76/80) | 68.4% (2291/3348) | 95.3% (61/64) | - | - |
| [SENT-VIP](test_suites/SENT-VIP.md) | 1/1 | 100.0% (9/9) | 82.0% (41/50) | 100.0% (10/10) | - | - |
| [SLIMbus-VIP](test_suites/SLIMbus-VIP.md) | 1/1 | 80.9% (38/47) | 80.8% (181/224) | 90.9% (10/11) | - | - |
| [SPI-VIP](test_suites/SPI-VIP.md) | 0/1 | - | - | - | - | - |
| [SPMI-VIP](test_suites/SPMI-VIP.md) | 1/1 | 92.0% (23/25) | 91.7% (11/12) | 91.7% (11/12) | - | - |
| [SWD-VIP](test_suites/SWD-VIP.md) | 1/1 | 93.6% (44/47) | 9.0% (24/268) | 75.0% (18/24) | - | - |
| [Security-VIP](test_suites/Security-VIP.md) | 1/1 | 96.2% (25/26) | 79.6% (532/668) | 100.0% (8/8) | - | - |
| [SoundWire-VIP](test_suites/SoundWire-VIP.md) | 1/1 | 95.3% (41/43) | 100.0% (110/110) | 86.7% (13/15) | - | - |
| [TileLink-VIP](test_suites/TileLink-VIP.md) | 1/1 | 100.0% (13/13) | 82.0% (287/350) | 100.0% (5/5) | - | - |
| [ToggleNAND-VIP](test_suites/ToggleNAND-VIP.md) | 1/1 | 93.9% (46/49) | 42.1% (106/252) | 92.7% (38/41) | - | - |
| [TypeC-VIP](test_suites/TypeC-VIP.md) | 1/1 | 88.9% (8/9) | 100.0% (18/18) | 100.0% (2/2) | - | - |
| [UALink-VIP](test_suites/UALink-VIP.md) | 1/1 | 100.0% (11/11) | 24.0% (83/346) | 100.0% (8/8) | - | - |
| [UART-VIP](test_suites/UART-VIP.md) | 1/1 | 90.0% (18/20) | 90.0% (9/10) | 100.0% (4/4) | - | - |
| [UCIe-VIP](test_suites/UCIe-VIP.md) | 1/1 | 100.0% (10/10) | 10.3% (137/1336) | 100.0% (14/14) | - | - |
| [UEC-VIP](test_suites/UEC-VIP.md) | 1/1 | 100.0% (4/4) | 13.5% (566/4204) | 100.0% (12/12) | - | - |
| [UFS-VIP](test_suites/UFS-VIP.md) | 1/1 | 86.5% (45/52) | 56.9% (247/434) | 96.3% (26/27) | - | - |
| [USB-VIP](test_suites/USB-VIP.md) | 1/1 | 93.9% (31/33) | 54.3% (125/230) | 96.3% (26/27) | - | - |
| [USB2-VIP](test_suites/USB2-VIP.md) | 1/1 | 93.9% (31/33) | 61.7% (111/180) | 92.6% (25/27) | - | - |
| [USB3-VIP](test_suites/USB3-VIP.md) | 1/1 | 94.9% (37/39) | 59.1% (78/132) | 95.2% (20/21) | - | - |
| [USB4-VIP](test_suites/USB4-VIP.md) | 1/1 | 91.4% (32/35) | 78.7% (118/150) | 100.0% (11/11) | - | - |
| [USB_PD-VIP](test_suites/USB_PD-VIP.md) | 1/1 | 96.4% (27/28) | 70.3% (121/172) | 100.0% (30/30) | - | - |
| [UniPro-VIP](test_suites/UniPro-VIP.md) | 1/1 | 100.0% (13/13) | 51.7% (187/362) | 100.0% (10/10) | - | - |
| [UniPro_Mem-VIP](test_suites/UniPro_Mem-VIP.md) | 1/1 | 100.0% (18/18) | 65.8% (96/146) | 100.0% (14/14) | - | - |
| [WTB-UVM-VIP](test_suites/WTB-UVM-VIP.md) | 1/1 | 100.0% (3/3) | 20.0% (16/80) | 100.0% (8/8) | - | - |
| [WTB-VIP](test_suites/WTB-VIP.md) | 1/1 | 95.7% (111/116) | 96.3% (1277/1326) | 91.8% (56/61) | - | - |
| [Wishbone-UVM-VIP](test_suites/Wishbone-UVM-VIP.md) | 2/2 | 100.0% (9/9) | 95.6% (1174/1228) | 100.0% (18/18) | - | - |
| [Wishbone-VIP](test_suites/Wishbone-VIP.md) | 1/1 | 96.3% (26/27) | 99.5% (438/440) | 100.0% (44/44) | - | - |
| [XGMII-UVM-VIP](test_suites/XGMII-UVM-VIP.md) | 1/1 | 100.0% (3/3) | 99.3% (147/148) | 100.0% (2/2) | - | - |
| [XGMII-VIP](test_suites/XGMII-VIP.md) | 1/1 | 100.0% (15/15) | 97.9% (617/630) | 100.0% (20/20) | - | - |
| [ddr6-VIP](test_suites/ddr6-VIP.md) | 1/1 | 100.0% (23/23) | 16.3% (207/1272) | 95.2% (20/21) | - | - |
| [ddr7-VIP](test_suites/ddr7-VIP.md) | 1/1 | 100.0% (23/23) | 16.3% (207/1272) | 95.2% (20/21) | - | - |
| [eCPRI-VIP](test_suites/eCPRI-VIP.md) | 1/1 | 91.9% (34/37) | 70.8% (358/506) | 100.0% (17/17) | - | - |
| [eMMC-VIP](test_suites/eMMC-VIP.md) | 1/1 | 92.7% (89/96) | 56.6% (738/1304) | 84.1% (58/69) | - | - |
| [eUSB2-VIP](test_suites/eUSB2-VIP.md) | 1/1 | 97.0% (32/33) | 81.8% (72/88) | 92.3% (24/26) | - | - |
| [gddr5-VIP](test_suites/gddr5-VIP.md) | 1/1 | 85.7% (12/14) | 67.9% (186/274) | 58.3% (7/12) | - | - |
| [gddr6-VIP](test_suites/gddr6-VIP.md) | 1/1 | 85.7% (12/14) | 67.9% (186/274) | 58.3% (7/12) | - | - |
| [gddr7-VIP](test_suites/gddr7-VIP.md) | 1/1 | 85.7% (12/14) | 67.9% (186/274) | 58.3% (7/12) | - | - |
| [hbm2-VIP](test_suites/hbm2-VIP.md) | 1/1 | 85.7% (12/14) | 67.9% (186/274) | 58.3% (7/12) | - | - |
| [hbm3-VIP](test_suites/hbm3-VIP.md) | 1/1 | 85.7% (12/14) | 67.9% (186/274) | 58.3% (7/12) | - | - |
| [hbm4-VIP](test_suites/hbm4-VIP.md) | 1/1 | 85.7% (12/14) | 67.9% (186/274) | 58.3% (7/12) | - | - |
| [lpddr5-VIP](test_suites/lpddr5-VIP.md) | 1/1 | 85.7% (12/14) | 67.9% (186/274) | 58.3% (7/12) | - | - |
| [lpddr5x-VIP](test_suites/lpddr5x-VIP.md) | 1/1 | 100.0% (35/35) | 26.1% (397/1522) | 96.4% (27/28) | - | - |
| [lpddr7-VIP](test_suites/lpddr7-VIP.md) | 1/1 | 100.0% (35/35) | 26.1% (397/1522) | 96.4% (27/28) | - | - |

## 4. Line coverage 低於 90% 的 VIP

未執行到的行號可對照 `build/cov/<VIP>/annotated/`（`%000000` 開頭的行）。大多是 model 的錯誤處理，或未被測試觸發的協定模式。

| VIP | Line | 未執行到的行 |
|---|---|---|
| SLIMbus-VIP | 80.9% | dut_slimbus_codec_slave.sv:37-43,65,88 |
| I3C-VIP | 85.0% | dut_i3c_target_model.sv:37-38,76,125-126,136,150,153,155,163,186,193,208,239,255 |
| gddr5-VIP | 85.7% | dut_gddr5_mem_model.sv:64 |
| gddr6-VIP | 85.7% | dut_gddr6_mem_model.sv:64 |
| gddr7-VIP | 85.7% | dut_gddr7_mem_model.sv:64 |
| hbm2-VIP | 85.7% | dut_hbm2_mem_model.sv:64 |
| hbm3-VIP | 85.7% | dut_hbm3_mem_model.sv:64 |
| hbm4-VIP | 85.7% | dut_hbm4_mem_model.sv:64 |
| lpddr5-VIP | 85.7% | dut_lpddr5_mem_model.sv:64 |
| JESD204-VIP | 86.1% | dut_jesd204_adc_dut.sv:30,32-34,131 |
| UFS-VIP | 86.5% | dut_ufs_device_dut.sv:45-49,79,144 |
| I2S-VIP | 88.5% | dut_i2s_receiver_loopback.sv:28,31,69 |
| TypeC-VIP | 88.9% | dut_typec_partner_model.sv:46 |
| CAN-VIP | 89.6% | dut_can_node_model.sv:83,87,91,93,121,133,165,174,259,334 |

### Functional coverage 未命中的 bins

| VIP | Functional | 未命中 bins（covergroup.coverpoint(數量)） |
|---|---|---|
| ACE_Lite-UVM-VIP | 100.0% (22/22) | - |
| AHB-VIP | 38.8% (47/121) | cg_ahb.cp_hburst(7); cg_ahb.cp_hsize(5); cg_ahb.cp_htrans(2); cg_ahb.cross_trans_write(4); cg_amba.cp_arvalid(1); cg_amba.cp_awvalid(1); cg_amba.cp_bvalid(1); cg_amba.cp_htrans(2); cg_amba.cp_penable(1); cg_amba.cp_psel(1); cg_amba.cp_rvalid(1); cg_amba.cp_wvalid(1); cg_amba.cross_aw_ar(3); cg_amba.cross_psel_en(3); cg_data.cp_data(1); cg_data.cx_wr_data(2); cg_fsm.cp_state(3); cg_fsm.cp_trans(5); cg_protocol.cp_burst(2); cg_protocol.cp_len(4); cg_protocol.cp_size(3); cg_protocol.cx_burst_size(11); cg_protocol.cx_wr_burst(4); cg_protocol.cx_wr_len(6) |
| APB-VIP | 47.7% (53/111) | cg_amba.cp_arvalid(1); cg_amba.cp_awvalid(1); cg_amba.cp_bvalid(1); cg_amba.cp_htrans(3); cg_amba.cp_rvalid(1); cg_amba.cp_wvalid(1); cg_amba.cross_aw_ar(3); cg_amba.cross_psel_en(1); cg_apb.cp_pprot(2); cg_apb.cp_pstrb(4); cg_apb.cross_sel_en(1); cg_apb.cross_wr_strb(10); cg_data.cp_data(2); cg_data.cx_wr_data(4); cg_fsm.cp_state(2); cg_fsm.cp_trans(5); cg_protocol.cp_len(3); cg_protocol.cp_prot(3); cg_protocol.cx_wr_len(6); cg_protocol.cx_wr_prot(4) |
| ATB-UVM-VIP | 100.0% (5/5) | - |
| AXI-VIP | 22.9% (72/315) | cg_amba.cp_htrans(3); cg_amba.cp_penable(1); cg_amba.cp_psel(1); cg_amba.cross_aw_ar(1); cg_amba.cross_psel_en(3); cg_axi.cp_arburst(1); cg_axi.cp_arsize(4); cg_axi.cp_awburst(1); cg_axi.cp_awcache(3); cg_axi.cp_awlen(3); cg_axi.cp_awsize(4); cg_axi.cp_bresp(2); cg_axi.cp_burst(2); cg_axi.cp_len(3); cg_axi.cp_prot(4); cg_axi.cp_resp(2); cg_axi.cp_rresp(2); cg_axi.cp_size(5); cg_axi.cross_ar(16); cg_axi.cross_aw(70); cg_axi.cross_burst_len(11); cg_axi.cross_prot_size(29); cg_data.cp_data(1); cg_data.cx_wr_data(2); cg_fsm.cp_trans(2); cg_protocol.cp_burst(2); cg_protocol.cp_len(5); cg_protocol.cp_resp(1); cg_protocol.cp_size(3); cg_protocol.cx_burst_len(14); cg_protocol.cx_wr_burst(4); cg_protocol.cx_wr_size_len(38) |
| Avalon_MM-UVM-VIP | 100.0% (11/11) | - |
| Avalon_ST-UVM-VIP | 100.0% (3/3) | - |
| CAN_FD-UVM-VIP | 87.5% (7/8) | can_fd_cg.cp_serr(1) |
| CHI-UVM-VIP | 100.0% (6/6) | - |
| DDR5-VIP | 100.0% (17/17) | - |
| ETH800G-VIP | 100.0% (9/9) | - |
| EtherCAT-VIP | 87.5% (7/8) | ethercat_cg.cp_pd(1) |
| GMII-UVM-VIP | 100.0% (5/5) | - |
| GPIO-UVM-VIP | 100.0% (6/6) | - |
| HBM3E-VIP | 100.0% (17/17) | - |
| IO_Link-VIP | 100.0% (9/9) | - |
| LPDDR6-VIP | 100.0% (19/19) | - |
| MDIO-UVM-VIP | 100.0% (8/8) | - |
| MIL_STD_1553-VIP | 100.0% (9/9) | - |
| OCP-VIP | 93.1% (27/29) | cg_fsm.cp_trans(2) |
| OneWire-UVM-VIP | 100.0% (5/5) | - |

## 5. 備註

- **PTP-VIP**：UVM build: %Error: 'make -C build/cov/uvm/PTP-VIP/obj -f Vtop_tb.mk -j 2' exited with 2
- **PWM-UVM-VIP**：UVM build: %Error: 'make -C build/cov/uvm/PWM-UVM-VIP/obj -f Vtop_tb.mk -j 2' exited with 2
- **RGMII-UVM-VIP**：UVM build: %Error: 'make -C build/cov/uvm/RGMII-UVM-VIP/obj -f Vtop_tb.mk -j 2' exited with 2
- **RapidIO-VIP**：UVM build: %Error: 'make -C build/cov/uvm/RapidIO-VIP/obj -f Vtop_tb.mk -j 2' exited with 2
- **SDIO-UVM-VIP**：UVM build: %Error: 'make -C build/cov/uvm/SDIO-UVM-VIP/obj -f Vtop_tb.mk -j 2' exited with 2
- **SENT-VIP**：UVM build: %Error: 'make -C build/cov/uvm/SENT-VIP/obj -f Vtop_tb.mk -j 2' exited with 2
- **SPI-VIP**：測試要比對 MISO 是否為 `1'bz`，Verilator 不支援 top-level tri-state，只能在 Icarus 上跑，因此量不到 coverage。<br>smoke_func_tb.sv: ERROR plain compile: %Error-UNSUPPORTED: /home/claude/open-vip-portfolio/build/vips/SPI-VIP/tb/smoke_func_tb.sv:31:27: Unsupported: tristate in top-level IO: 'vif_mosi'; pkgs compile: %Error-UNSUPPORTED: /home/claude/open-vip-portfolio/build/vips/SPI-VIP/tb/smoke_func_tb.sv:31:27: Unsupported: tristate in
- **TileLink-VIP**：UVM build: %Error: 'make -C build/cov/uvm/TileLink-VIP/obj -f Vtop_tb.mk -j 2' exited with 2
- **UALink-VIP**：UVM build: %Error: 'make -C build/cov/uvm/UALink-VIP/obj -f Vtop_tb.mk -j 2' exited with 2
- **UCIe-VIP**：UVM build: %Error: 'make -C build/cov/uvm/UCIe-VIP/obj -f Vtop_tb.mk -j 2' exited with 2
- **UEC-VIP**：UVM build: %Error: 'make -C build/cov/uvm/UEC-VIP/obj -f Vtop_tb.mk -j 2' exited with 2
- **WTB-UVM-VIP**：UVM build: %Error: 'make -C build/cov/uvm/WTB-UVM-VIP/obj -f Vtop_tb.mk -j 2' exited with 2
- **Wishbone-UVM-VIP**：UVM build: %Error: 'make -C build/cov/uvm/Wishbone-UVM-VIP/obj -f Vtop_tb.mk -j 2' exited with 2
- **XGMII-UVM-VIP**：UVM build: %Error: 'make -C build/cov/uvm/XGMII-UVM-VIP/obj -f Vtop_tb.mk -j 2' exited with 2

## 6. 重跑

```bash
bash tools/install_tools.sh && export PATH=/opt/verilator-5.052/bin:$PATH
bash tools/extract_vips.sh
python3 tools/coverage.py -j 2        # coverage_report.csv, build/cov/<VIP>/
python3 tools/coverage.py APB-VIP     # 單一 VIP
python3 tools/gen_coverage_doc.py     # docs/COVERAGE.md
```
