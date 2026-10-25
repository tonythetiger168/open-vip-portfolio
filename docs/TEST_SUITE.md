# VIP Portfolio 測試套件總表

> 由 `tools/gen_test_suite_docs.py` 自動產生。各 VIP 的完整測試套件文件在 [`docs/test_suites/`](test_suites/)。

## 1. 結論

- 132 個 VIP 中 132 個有可在開源工具上執行的 self-checking 功能測試，共 2445 個 check（另有 RTL IP testbench 的 57770027 次斷言評估）；132 個 VIP 的測試全部通過。
- 判定：✅ Sufficient 99、🟡 Partial 33、❌ Insufficient 0。
- Mutation testing：1783 個有效 mutant 中 1564 個被功能測試偵測（88%）。
- 功能測試找到 66 個 DUT 模型缺陷，以 XFAIL check 記錄（見第 4 節）；模型修好後該 check 會變成 XPASS 並使測試失敗，提醒移除標記。

## 2. 方法

每個 VIP 的測試套件分三層：

1. **功能測試**（`tb/func_*_tb.sv`、`tb/smoke_func_tb.sv`、RTL IP 的 `tb/*_tb.sv`）：直接驅動 VIP 內的 DUT 模型，依協定規格與模型合約逐項比對，輸出 `FUNC_PASS checks=N`。由 `tools/run_func_tests.py` 以 Icarus Verilog 或 Verilator 5.052 執行，結果寫入 `func_report.csv`。
2. **UVM 測試平台**（tests / sequences / scoreboard / SVA / coverage）：需商用模擬器執行，開源流程以 pyslang elaboration 檢查（`tools/elab_scan.py`）；有 register model 的 VIP（APB / AHB / AXI）另以 `tools/run_uvm_tests.py` 在 Verilator 上執行 UVM RAL test（見 [RAL.md](RAL.md)）。
3. **Mutation testing**（`tools/mutation_score.py`）：對 DUT 模型注入運算子與常數錯誤，檢查功能測試能否偵測，作為「測試是否足夠」的客觀指標，結果寫入 `mutation_report.csv`。

判定標準：

| 判定 | 條件 |
|---|---|
| ✅ Sufficient | 功能測試通過，≥ 10 個 check，mutation score ≥ 80% |
| 🟡 Partial | 功能測試通過，但 check < 10 或 mutation score 50–79% |
| ❌ Insufficient | 沒有功能測試、測試失敗或 mutation score < 50% |

模型缺陷（XFAIL）與模型未實作的功能另列為缺口：它們是 DUT 模型的限制，不是測試的不足。

## 3. 各 VIP 判定

Checks 欄不含 RTL IP testbench 的斷言評估次數（見各 VIP 文件）。

| VIP | 類別 | 功能測試 | Checks | 模擬器 | Mutation | 模型缺陷 | 判定 |
|---|---|---|---|---|---|---|---|
| [ACE-VIP](test_suites/ACE-VIP.md) | AMBA | `ACE_tb.sv` | 0 | verilator | 8/12 | 0 | 🟡 Partial |
| [ACE_Lite-UVM-VIP](test_suites/ACE_Lite-UVM-VIP.md) | AMBA | `smoke_func_tb.sv` | 12 | iverilog | 12/19 | 0 | 🟡 Partial |
| [ACE_Lite-VIP](test_suites/ACE_Lite-VIP.md) | AMBA | `ACE_Lite_tb.sv` | 0 | verilator | 9/12 | 0 | 🟡 Partial |
| [AHB-VIP](test_suites/AHB-VIP.md) | AMBA | `smoke_func_tb.sv`, `func_ahb_tb.sv` | 38 | iverilog | 28/28 | 0 | ✅ Sufficient |
| [APB-VIP](test_suites/APB-VIP.md) | AMBA | `smoke_func_tb.sv`, `func_apb_tb.sv` | 22 | iverilog | 15/15 | 0 | ✅ Sufficient |
| [ATB-UVM-VIP](test_suites/ATB-UVM-VIP.md) | Debug | `smoke_func_tb.sv` | 9 | iverilog | 4/6 | 0 | 🟡 Partial |
| [ATB-VIP](test_suites/ATB-VIP.md) | Debug | `ATB_tb.sv` | 0 | verilator | 9/10 | 0 | ✅ Sufficient |
| [AVSBus-VIP](test_suites/AVSBus-VIP.md) | Power | `func_avsbus_tb.sv` | 14 | verilator | 11/12 | 0 | ✅ Sufficient |
| [AXI-VIP](test_suites/AXI-VIP.md) | AMBA | `smoke_func_tb.sv`, `func_axi_tb.sv` | 48 | iverilog | 23/23 | 1 | ✅ Sufficient |
| [AXI4-VIP](test_suites/AXI4-VIP.md) | AMBA | `AXI4_tb.sv` | 0 | verilator | 10/12 | 0 | ✅ Sufficient |
| [AXI4_Lite-VIP](test_suites/AXI4_Lite-VIP.md) | AMBA | `AXI4_Lite_tb.sv` | 0 | verilator | 11/12 | 0 | ✅ Sufficient |
| [AXI_Stream-VIP](test_suites/AXI_Stream-VIP.md) | AMBA | `AXI_Stream_tb.sv` | 0 | verilator | 5/6 | 0 | ✅ Sufficient |
| [Avalon_MM-UVM-VIP](test_suites/Avalon_MM-UVM-VIP.md) | Interconnect | `smoke_func_tb.sv` | 34 | iverilog | 8/15 | 0 | 🟡 Partial |
| [Avalon_MM-VIP](test_suites/Avalon_MM-VIP.md) | Interconnect | `Avalon_MM_tb.sv`, `func_avalon_mm_tb.sv` | 33 | verilator | 9/9 | 0 | ✅ Sufficient |
| [Avalon_ST-UVM-VIP](test_suites/Avalon_ST-UVM-VIP.md) | Interconnect | `smoke_func_tb.sv`, `func_avalon_st_tb.sv` | 28 | iverilog | 7/7 | 1 | ✅ Sufficient |
| [Avalon_ST-VIP](test_suites/Avalon_ST-VIP.md) | Interconnect | `Avalon_ST_tb.sv` | 0 | verilator | 6/7 | 0 | ✅ Sufficient |
| [Bluetooth5-VIP](test_suites/Bluetooth5-VIP.md) | Storage/Debug | `func_bluetooth5_tb.sv` | 26 | verilator | 11/11 | 1 | ✅ Sufficient |
| [CAN-VIP](test_suites/CAN-VIP.md) | Automotive | `func_can_tb.sv` | 7 | verilator | 4/4 | 2 | 🟡 Partial |
| [CAN_FD-UVM-VIP](test_suites/CAN_FD-UVM-VIP.md) | Automotive | `smoke_func_tb.sv` | 14 | iverilog | 13/16 | 0 | ✅ Sufficient |
| [CCIX-VIP](test_suites/CCIX-VIP.md) | Interconnect | `func_ccix_tb.sv` | 13 | iverilog | 15/15 | 0 | ✅ Sufficient |
| [CHI-UVM-VIP](test_suites/CHI-UVM-VIP.md) | AMBA | `smoke_func_tb.sv` | 11 | iverilog | 7/10 | 0 | 🟡 Partial |
| [CHI-VIP](test_suites/CHI-VIP.md) | AMBA | `CHI_tb.sv` | 0 | verilator | 8/12 | 0 | 🟡 Partial |
| [CPRI-VIP](test_suites/CPRI-VIP.md) | Telecom | `func_cpri_tb.sv` | 17 | iverilog | 19/19 | 0 | ✅ Sufficient |
| [CSE-VIP](test_suites/CSE-VIP.md) | MIPI | `func_cse_tb.sv` | 34 | iverilog | 25/25 | 0 | ✅ Sufficient |
| [CSI_2-VIP](test_suites/CSI_2-VIP.md) | MIPI | `func_mipi_tb.sv` | 29 | verilator | 11/11 | 0 | ✅ Sufficient |
| [CXL-VIP](test_suites/CXL-VIP.md) | Interconnect | `smoke_func_tb.sv` | 11 | verilator | 4/7 | 0 | 🟡 Partial |
| [CXS-VIP](test_suites/CXS-VIP.md) | Interconnect | `func_cxs_tb.sv` | 11 | iverilog | 10/10 | 0 | ✅ Sufficient |
| [C_PHY-VIP](test_suites/C_PHY-VIP.md) | MIPI | `func_mipi_tb.sv` | 29 | verilator | 11/11 | 0 | ✅ Sufficient |
| [DBI-VIP](test_suites/DBI-VIP.md) | MIPI | `func_dbi_tb.sv` | 15 | verilator | 9/10 | 0 | ✅ Sufficient |
| [DDR-VIP](test_suites/DDR-VIP.md) | Memory | `func_mem_tb.sv` | 20 | verilator | 7/7 | 0 | ✅ Sufficient |
| [DDR4-VIP](test_suites/DDR4-VIP.md) | Memory | `DDR4_tb.sv`, `func_ddr4_tb.sv` | 39 | verilator | 7/7 | 2 | ✅ Sufficient |
| [DDR5-VIP](test_suites/DDR5-VIP.md) | Memory | `smoke_func_tb.sv`, `func_ddr5_tb.sv` | 23 | iverilog | 16/16 | 0 | ✅ Sufficient |
| [DFI-VIP](test_suites/DFI-VIP.md) | Memory | `func_dfi_tb.sv` | 29 | verilator | 12/12 | 0 | ✅ Sufficient |
| [DPI-VIP](test_suites/DPI-VIP.md) | MIPI | `func_dpi_tb.sv` | 10 | iverilog | 20/20 | 0 | ✅ Sufficient |
| [DSI-VIP](test_suites/DSI-VIP.md) | MIPI | `func_mipi_tb.sv` | 29 | verilator | 11/11 | 0 | ✅ Sufficient |
| [D_PHY-VIP](test_suites/D_PHY-VIP.md) | MIPI | `func_mipi_tb.sv` | 29 | verilator | 11/11 | 0 | ✅ Sufficient |
| [DigRF-VIP](test_suites/DigRF-VIP.md) | MIPI | `func_mipi_tb.sv` | 20 | verilator | 12/12 | 0 | ✅ Sufficient |
| [DisplayPort2-VIP](test_suites/DisplayPort2-VIP.md) | Storage/Debug | `func_displayport2_tb.sv` | 14 | iverilog | 18/18 | 2 | ✅ Sufficient |
| [ETH800G-VIP](test_suites/ETH800G-VIP.md) | Networking | `smoke_func_tb.sv`, `func_eth800g_tb.sv` | 30 | iverilog | 19/19 | 1 | ✅ Sufficient |
| [EtherCAT-VIP](test_suites/EtherCAT-VIP.md) | Industrial | `smoke_func_tb.sv` | 22 | iverilog | 2/3 | 0 | 🟡 Partial |
| [Ethernet-VIP](test_suites/Ethernet-VIP.md) | Networking | `smoke_func_tb.sv`, `func_ethernet_tb.sv` | 37 | iverilog | 25/27 | 1 | ✅ Sufficient |
| [Ethernet_AVB_TSN-VIP](test_suites/Ethernet_AVB_TSN-VIP.md) | Automotive | `func_avb_tsn_tb.sv` | 21 | iverilog | 24/30 | 3 | ✅ Sufficient |
| [FC-VIP](test_suites/FC-VIP.md) | Networking | `func_fc_tb.sv` | 28 | verilator | 11/12 | 4 | ✅ Sufficient |
| [FlexRay-VIP](test_suites/FlexRay-VIP.md) | Automotive | `func_flexray_tb.sv` | 33 | iverilog | 23/23 | 4 | ✅ Sufficient |
| [GMII-UVM-VIP](test_suites/GMII-UVM-VIP.md) | Networking | `smoke_func_tb.sv` | 22 | iverilog | 2/3 | 0 | 🟡 Partial |
| [GMII-VIP](test_suites/GMII-VIP.md) | Networking | `GMII_tb.sv` | 0 | verilator | 9/12 | 0 | 🟡 Partial |
| [GPIO-UVM-VIP](test_suites/GPIO-UVM-VIP.md) | Peripherals | `smoke_func_tb.sv` | 42 | iverilog | 1/1 | 0 | ✅ Sufficient |
| [GPIO-VIP](test_suites/GPIO-VIP.md) | Peripherals | `GPIO_tb.sv` | 0 | verilator | 5/5 | 0 | ✅ Sufficient |
| [HBM-VIP](test_suites/HBM-VIP.md) | Memory | `func_mem_tb.sv` | 20 | verilator | 6/6 | 0 | ✅ Sufficient |
| [HBM3E-VIP](test_suites/HBM3E-VIP.md) | Memory | `smoke_func_tb.sv`, `func_hbm3e_tb.sv` | 20 | iverilog | 18/18 | 0 | ✅ Sufficient |
| [HBM5-VIP](test_suites/HBM5-VIP.md) | Memory | `func_mem_tb.sv` | 16 | verilator | 5/5 | 0 | ✅ Sufficient |
| [HDCP-VIP](test_suites/HDCP-VIP.md) | Security | `func_hdcp_tb.sv` | 19 | verilator | 10/12 | 2 | ✅ Sufficient |
| [HDMI-VIP](test_suites/HDMI-VIP.md) | Video | `func_hdmi_tb.sv` | 19 | iverilog | 21/21 | 2 | ✅ Sufficient |
| [HSI-VIP](test_suites/HSI-VIP.md) | MIPI | `func_mipi_tb.sv` | 19 | verilator | 11/12 | 0 | ✅ Sufficient |
| [I2C-VIP](test_suites/I2C-VIP.md) | Serial | `smoke_func_tb.sv` | 6 | iverilog | 17/23 | 0 | 🟡 Partial |
| [I2S-VIP](test_suites/I2S-VIP.md) | Audio | `func_i2s_tb.sv` | 11 | verilator | 5/5 | 0 | ✅ Sufficient |
| [I3C-VIP](test_suites/I3C-VIP.md) | MIPI | `func_i3c_tb.sv` | 25 | verilator | 8/11 | 1 | 🟡 Partial |
| [IO_Link-VIP](test_suites/IO_Link-VIP.md) | Industrial | `smoke_func_tb.sv` | 7 | iverilog | 23/30 | 0 | 🟡 Partial |
| [Interlaken-VIP](test_suites/Interlaken-VIP.md) | Networking | `func_intlkn_tb.sv` | 23 | iverilog | 24/30 | 0 | ✅ Sufficient |
| [JESD204-VIP](test_suites/JESD204-VIP.md) | SerDes | `func_jesd204_tb.sv` | 15 | iverilog | 27/30 | 0 | ✅ Sufficient |
| [JTAG-VIP](test_suites/JTAG-VIP.md) | Storage/Debug | `func_jtag_tb.sv` | 25 | verilator | 10/12 | 0 | ✅ Sufficient |
| [LIN-VIP](test_suites/LIN-VIP.md) | Automotive | `func_lin_tb.sv` | 12 | verilator | 6/6 | 4 | ✅ Sufficient |
| [LPDDR-VIP](test_suites/LPDDR-VIP.md) | Memory | `func_mem_tb.sv` | 14 | verilator | 4/4 | 0 | ✅ Sufficient |
| [LPDDR4-VIP](test_suites/LPDDR4-VIP.md) | Memory | `LPDDR4_tb.sv`, `func_lpddr4_tb.sv` | 43 | verilator | 6/6 | 2 | ✅ Sufficient |
| [LPDDR6-VIP](test_suites/LPDDR6-VIP.md) | Memory | `smoke_func_tb.sv`, `func_lpddr6_tb.sv` | 36 | iverilog | 21/21 | 0 | ✅ Sufficient |
| [LPI-VIP](test_suites/LPI-VIP.md) | Power | `func_lpi_tb.sv` | 12 | iverilog | 14/16 | 0 | ✅ Sufficient |
| [LTI-VIP](test_suites/LTI-VIP.md) | Interconnect | `func_lti_tb.sv` | 10 | iverilog | 15/16 | 1 | ✅ Sufficient |
| [MDIO-UVM-VIP](test_suites/MDIO-UVM-VIP.md) | Networking | `smoke_func_tb.sv`, `func_mdio_tb.sv` | 19 | iverilog | 4/4 | 1 | ✅ Sufficient |
| [MDIO-VIP](test_suites/MDIO-VIP.md) | Networking | `MDIO_tb.sv` | 0 | verilator | 9/12 | 0 | 🟡 Partial |
| [MIL_STD_1553-VIP](test_suites/MIL_STD_1553-VIP.md) | Aerospace | `smoke_func_tb.sv` | 19 | iverilog | 12/15 | 0 | ✅ Sufficient |
| [M_PHY-VIP](test_suites/M_PHY-VIP.md) | MIPI | `func_mipi_tb.sv` | 29 | verilator | 11/11 | 0 | ✅ Sufficient |
| [NVMe-VIP](test_suites/NVMe-VIP.md) | Storage/Debug | `smoke_func_tb.sv`, `func_nvme_tb.sv` | 56 | verilator | 8/8 | 1 | ✅ Sufficient |
| [OCP-VIP](test_suites/OCP-VIP.md) | Interconnect | `func_ocp_tb.sv` | 12 | verilator | 6/6 | 1 | ✅ Sufficient |
| [ONFI-VIP](test_suites/ONFI-VIP.md) | Memory | `func_onfi_tb.sv` | 37 | verilator | 7/8 | 4 | ✅ Sufficient |
| [OneWire-UVM-VIP](test_suites/OneWire-UVM-VIP.md) | Peripherals | `smoke_func_tb.sv` | 25 | iverilog | 13/16 | 0 | ✅ Sufficient |
| [OneWire-VIP](test_suites/OneWire-VIP.md) | Peripherals | `_1_Wire_tb.sv`, `func_onewire_tb.sv` | 20 | verilator | 11/11 | 0 | ✅ Sufficient |
| [PCIe-VIP](test_suites/PCIe-VIP.md) | Interconnect | `smoke_func_tb.sv` | 11 | verilator | 4/7 | 0 | 🟡 Partial |
| [PTP-VIP](test_suites/PTP-VIP.md) | Networking | `smoke_func_tb.sv` | 18 | iverilog | 8/10 | 0 | ✅ Sufficient |
| [PWM-UVM-VIP](test_suites/PWM-UVM-VIP.md) | Peripherals | `smoke_func_tb.sv` | 35 | iverilog | 10/12 | 0 | ✅ Sufficient |
| [PWM-VIP](test_suites/PWM-VIP.md) | Peripherals | `PWM_tb.sv` | 0 | verilator | 10/12 | 0 | ✅ Sufficient |
| [QSPI-VIP](test_suites/QSPI-VIP.md) | Serial | `QSPI_tb.sv` | 0 | verilator | 10/12 | 0 | ✅ Sufficient |
| [RFFE-VIP](test_suites/RFFE-VIP.md) | MIPI | `func_rffe_tb.sv` | 14 | iverilog | 25/29 | 0 | ✅ Sufficient |
| [RGMII-UVM-VIP](test_suites/RGMII-UVM-VIP.md) | Networking | `smoke_func_tb.sv` | 14 | iverilog | 2/2 | 0 | ✅ Sufficient |
| [RGMII-VIP](test_suites/RGMII-VIP.md) | Networking | `RGMII_tb.sv` | 0 | verilator | 8/12 | 0 | 🟡 Partial |
| [RapidIO-VIP](test_suites/RapidIO-VIP.md) | Interconnect | `smoke_func_tb.sv` | 21 | iverilog | 2/3 | 0 | 🟡 Partial |
| [SAS-VIP](test_suites/SAS-VIP.md) | Storage | `func_sas_tb.sv` | 37 | verilator | 9/12 | 4 | 🟡 Partial |
| [SATA-VIP](test_suites/SATA-VIP.md) | Storage/Debug | `func_sata_tb.sv` | 26 | verilator | 10/11 | 2 | ✅ Sufficient |
| [SD-VIP](test_suites/SD-VIP.md) | Memory | `func_sd_tb.sv` | 33 | verilator | 9/12 | 3 | 🟡 Partial |
| [SDIO-UVM-VIP](test_suites/SDIO-UVM-VIP.md) | Storage | `smoke_func_tb.sv` | 15 | iverilog | 10/18 | 0 | 🟡 Partial |
| [SDIO-VIP](test_suites/SDIO-VIP.md) | Storage | `SDIO_tb.sv` | 0 | verilator | 8/12 | 0 | 🟡 Partial |
| [SENT-VIP](test_suites/SENT-VIP.md) | Automotive | `smoke_func_tb.sv` | 12 | iverilog | 12/16 | 0 | 🟡 Partial |
| [SLIMbus-VIP](test_suites/SLIMbus-VIP.md) | MIPI | `func_slimbus_tb.sv` | 14 | iverilog | 23/23 | 0 | ✅ Sufficient |
| [SPI-VIP](test_suites/SPI-VIP.md) | Serial | `smoke_func_tb.sv` | 8 | iverilog | 22/28 | 0 | 🟡 Partial |
| [SPMI-VIP](test_suites/SPMI-VIP.md) | MIPI | `func_spmi_tb.sv` | 15 | iverilog | 24/29 | 0 | ✅ Sufficient |
| [SWD-VIP](test_suites/SWD-VIP.md) | Debug | `func_swd_tb.sv` | 23 | verilator | 11/12 | 0 | ✅ Sufficient |
| [Security-VIP](test_suites/Security-VIP.md) | Security | `func_security_tb.sv` | 17 | iverilog | 25/25 | 0 | ✅ Sufficient |
| [SoundWire-VIP](test_suites/SoundWire-VIP.md) | MIPI | `func_soundwire_tb.sv` | 18 | verilator | 6/7 | 0 | ✅ Sufficient |
| [TileLink-VIP](test_suites/TileLink-VIP.md) | Interconnect | `func_tilelink_tb.sv` | 10 | verilator | 7/7 | 1 | ✅ Sufficient |
| [ToggleNAND-VIP](test_suites/ToggleNAND-VIP.md) | Storage | `func_tnand_tb.sv` | 32 | verilator | 10/12 | 5 | ✅ Sufficient |
| [TypeC-VIP](test_suites/TypeC-VIP.md) | USB | `func_typec_tb.sv` | 9 | iverilog | 1/1 | 0 | 🟡 Partial |
| [UALink-VIP](test_suites/UALink-VIP.md) | Interconnect | `smoke_func_tb.sv` | 11 | iverilog | 10/16 | 0 | 🟡 Partial |
| [UART-VIP](test_suites/UART-VIP.md) | Serial | `smoke_func_tb.sv` | 11 | iverilog | 13/19 | 0 | 🟡 Partial |
| [UCIe-VIP](test_suites/UCIe-VIP.md) | Interconnect | `smoke_func_tb.sv` | 19 | iverilog | 12/12 | 0 | ✅ Sufficient |
| [UEC-VIP](test_suites/UEC-VIP.md) | Networking | `smoke_func_tb.sv` | 12 | iverilog | 8/12 | 0 | 🟡 Partial |
| [UFS-VIP](test_suites/UFS-VIP.md) | Memory | `func_ufs_tb.sv` | 28 | verilator | 11/12 | 0 | ✅ Sufficient |
| [USB-VIP](test_suites/USB-VIP.md) | USB | `func_usb_tb.sv` | 29 | iverilog | 26/30 | 0 | ✅ Sufficient |
| [USB2-VIP](test_suites/USB2-VIP.md) | USB | `smoke_func_tb.sv` | 15 | iverilog | 21/30 | 0 | 🟡 Partial |
| [USB3-VIP](test_suites/USB3-VIP.md) | USB | `func_usb3_tb.sv` | 28 | iverilog | 26/30 | 0 | ✅ Sufficient |
| [USB4-VIP](test_suites/USB4-VIP.md) | USB | `func_usb4_tb.sv` | 26 | verilator | 11/12 | 0 | ✅ Sufficient |
| [USB_PD-VIP](test_suites/USB_PD-VIP.md) | USB | `func_usb_pd_tb.sv` | 29 | iverilog | 26/30 | 2 | ✅ Sufficient |
| [UniPro-VIP](test_suites/UniPro-VIP.md) | MIPI | `func_mipi_tb.sv` | 29 | verilator | 11/11 | 0 | ✅ Sufficient |
| [UniPro_Mem-VIP](test_suites/UniPro_Mem-VIP.md) | Memory | `func_unipro_mem_tb.sv` | 22 | iverilog | 22/22 | 0 | ✅ Sufficient |
| [WTB-UVM-VIP](test_suites/WTB-UVM-VIP.md) | Debug | `smoke_func_tb.sv` | 9 | iverilog | 4/6 | 0 | 🟡 Partial |
| [WTB-VIP](test_suites/WTB-VIP.md) | Debug | `WTB_tb.sv` | 0 | verilator | 10/12 | 0 | ✅ Sufficient |
| [Wishbone-UVM-VIP](test_suites/Wishbone-UVM-VIP.md) | Interconnect | `smoke_func_tb.sv`, `func_wishbone_tb.sv` | 34 | iverilog | 11/11 | 0 | ✅ Sufficient |
| [Wishbone-VIP](test_suites/Wishbone-VIP.md) | Interconnect | `Wishbone_tb.sv` | 0 | verilator | 8/12 | 0 | 🟡 Partial |
| [XGMII-UVM-VIP](test_suites/XGMII-UVM-VIP.md) | Networking | `smoke_func_tb.sv` | 14 | iverilog | 1/1 | 0 | ✅ Sufficient |
| [XGMII-VIP](test_suites/XGMII-VIP.md) | Networking | `XGMII_tb.sv` | 0 | verilator | 10/12 | 0 | ✅ Sufficient |
| [ddr6-VIP](test_suites/ddr6-VIP.md) | Memory | `func_mem_tb.sv` | 16 | verilator | 5/5 | 0 | ✅ Sufficient |
| [ddr7-VIP](test_suites/ddr7-VIP.md) | Memory | `func_mem_tb.sv` | 16 | verilator | 5/5 | 0 | ✅ Sufficient |
| [eCPRI-VIP](test_suites/eCPRI-VIP.md) | Telecom | `func_ecpri_tb.sv` | 20 | iverilog | 27/30 | 4 | ✅ Sufficient |
| [eMMC-VIP](test_suites/eMMC-VIP.md) | Memory | `func_emmc_tb.sv` | 41 | verilator | 8/12 | 3 | 🟡 Partial |
| [eUSB2-VIP](test_suites/eUSB2-VIP.md) | USB | `func_eusb2_tb.sv` | 25 | iverilog | 26/30 | 1 | ✅ Sufficient |
| [gddr5-VIP](test_suites/gddr5-VIP.md) | Memory | `func_mem_tb.sv` | 15 | verilator | 7/7 | 0 | ✅ Sufficient |
| [gddr6-VIP](test_suites/gddr6-VIP.md) | Memory | `func_mem_tb.sv` | 15 | verilator | 7/7 | 0 | ✅ Sufficient |
| [gddr7-VIP](test_suites/gddr7-VIP.md) | Memory | `func_mem_tb.sv` | 15 | verilator | 7/7 | 0 | ✅ Sufficient |
| [hbm2-VIP](test_suites/hbm2-VIP.md) | Memory | `func_mem_tb.sv` | 15 | verilator | 7/7 | 0 | ✅ Sufficient |
| [hbm3-VIP](test_suites/hbm3-VIP.md) | Memory | `func_mem_tb.sv` | 15 | verilator | 7/7 | 0 | ✅ Sufficient |
| [hbm4-VIP](test_suites/hbm4-VIP.md) | Memory | `func_mem_tb.sv` | 15 | verilator | 7/7 | 0 | ✅ Sufficient |
| [lpddr5-VIP](test_suites/lpddr5-VIP.md) | Memory | `func_mem_tb.sv` | 15 | verilator | 7/7 | 0 | ✅ Sufficient |
| [lpddr5x-VIP](test_suites/lpddr5x-VIP.md) | Memory | `func_mem_tb.sv` | 26 | iverilog | 24/24 | 0 | ✅ Sufficient |
| [lpddr7-VIP](test_suites/lpddr7-VIP.md) | Memory | `func_mem_tb.sv` | 26 | iverilog | 24/24 | 0 | ✅ Sufficient |

## 4. 功能測試找到的 DUT 模型缺陷

**AXI-VIP**

- AW accepted during a write burst does not redirect that burst's beats

**Avalon_ST-UVM-VIP**

- beats held while aso_ready is low (no data lost)

**Bluetooth5-VIP**

- echo starts with the first received byte

**CAN-VIP**

- compliant standard frame received without error
- stuff bit counted as the first bit of the next run

**DDR4-VIP**

- PRE is a single-cycle command (pins return to NOP)
- host held off for tRP after PRE

**DisplayPort2-VIP**

- K28.5 on all four lanes completes training
- K character during active video after training is flagged

**ETH800G-VIP**

- EOP without SOP is not counted as a packet

**Ethernet-VIP**

- 56-byte frame (under the 64-byte minimum) gives len_error

**Ethernet_AVB_TSN-VIP**

- ts_nsec stays below 1e9 and advances 8 ns per clock across the second
- back-to-back frames (SOF directly after the last beat) both forwarded
- frame interrupted by gate closure is not forwarded truncated

**FC-VIP**

- second identical frame with a correct CRC accepted
- frame longer than 2148 bytes raises len_error
- EOP without SOP raises framing_error
- credit consumed in the R_RDY clock is counted (3 left)

**FlexRay-VIP**

- frame echoed on txd_a as 000 1 + captured bits
- odd payload length: whole frame captured
- corrupted frame CRC flagged
- FlexRay 2.1 header with spec CRC accepted

**HDCP-VIP**

- receiver answers at the HDCP DDC read address 0x75
- revoked receiver presents the revoked Bksv

**HDMI-VIP**

- blue >= 0x80 is pixel data, not the CRC word
- spec video preamble (ch1 CTRL1, ch2 CTRL0) decoded as video

**I3C-VIP**

- ENTDAA with a repeated START before 0x7E/R

**LIN-VIP**

- sync byte 0x55 received without bit error
- checksum output carries the received checksum byte
- re-transmitted frame ends with the checksum
- wrong checksum byte flagged

**LPDDR4-VIP**

- PRE is a single-cycle command (pins return to NOP)
- host held off for tRP after PRE

**LTI-VIP**

- la_ready is low while a translation is outstanding

**MDIO-UVM-VIP**

- read of PHY 5: TA 0 then phy_status, MSB first

**NVMe-VIP**

- CQ entry carries this command's status

**OCP-VIP**

- SCmdAccept low while a request is outstanding

**ONFI-VIP**

- parameter page integrity CRC (bytes 254-255) valid
- partial program: unwritten bytes of the page stay FFh
- GET FEATURES returns P2..P4
- 00h after 70h resumes page data output

**SAS-VIP**

- VIP driver OOB (48 zero clocks, 32 toggles) brings the PHY ready
- frame sent right after the response's stop bit is received
- remainder of an oversize DATA frame is not parsed as new frames
- first frame after 32 SN toggles is received correctly

**SATA-VIP**

- dword 0 carries FIS type 0x27 and the C bit
- reset drops link_up and restarts OOB

**SD-VIP**

- command with the specified CRC7 is accepted
- R2 starts with 0, 0, 111111
- R6 reports CURRENT_STATE (ident) in bits 12:9

**TileLink-VIP**

- a_ready low while a request is outstanding

**ToggleNAND-VIP**

- status READY flag in bit 6 (40h)
- read at column 5 returns bytes 5..8 of the page
- erase clears data programmed at a non-zero column
- byte captured on the DQS falling edge (DDR)
- NAND does not drive DQ while the host drives a command

**USB_PD-VIP**

- Source_Capabilities during a contract are answered with a Request
- rejected request leaves VBUS at the previous level

**eCPRI-VIP**

- rx_valid asserted without waiting for rx_ready
- FCS beat held while rx_ready is low
- request received while a response is pending is answered too
- zero-length request is terminated by its FCS word and answered

**eMMC-VIP**

- command with the specified CRC7 is accepted
- R2 starts with 0, 0, 111111
- CMD7 R1 reports CURRENT_STATE (stby) in bits 12:9

**eUSB2-VIP**

- HS selected after host K-J-K-J-K-J

## 5. 重新產生

```bash
bash tools/extract_vips.sh                # 解開 vips/*.zip 到 build/vips
python3 smoke/flatten.py && python3 tools/run_func_tests.py   # func_report.csv
python3 tools/mutation_score.py -j 4       # mutation_report.csv（數小時）
python3 tools/gen_test_suite_docs.py       # 本文件與 docs/test_suites/
```
