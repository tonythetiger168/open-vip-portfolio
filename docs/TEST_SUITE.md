# VIP Portfolio 測試套件總表

> 由 `tools/gen_test_suite_docs.py` 自動產生。各 VIP 的完整測試套件文件在 [`docs/test_suites/`](test_suites/)。

## 1. 結論

- 130 個 VIP 中 130 個有可在開源工具上執行的 self-checking 功能測試，共 3563 個 check；130 個 VIP 的測試全部通過（RTL IP 已移到 open-ip-portfolio，其 testbench 不在此計）。
- 判定：✅ Sufficient 113、🟡 Partial 17、❌ Insufficient 0。
- Mutation testing：2431 個有效 mutant 中 2286 個被功能測試偵測（94%）。
- 沒有未修正的 DUT 模型缺陷：功能測試中沒有 XFAIL check（先前記錄的缺陷都已在模型中修正）。

## 2. 方法

每個 VIP 的測試套件分三層：

1. **功能測試**（`tb/func_*_tb.sv`、`tb/smoke_func_tb.sv`）：直接驅動 VIP 內的 DUT 模型，依協定規格與模型合約逐項比對，輸出 `FUNC_PASS checks=N`。由 `tools/run_func_tests.py` 以 Icarus Verilog 或 Verilator 5.052 執行，結果寫入 `func_report.csv`。
2. **UVM 測試平台**（tests / sequences / scoreboard / SVA / coverage）：需商用模擬器執行，開源流程以 pyslang elaboration 檢查（`tools/elab_scan.py`）；有 register model 的 VIP（APB / AHB / AXI / OCP / TileLink）另以 `tools/run_uvm_tests.py` 在 Verilator 上執行 UVM RAL test（見 [RAL.md](RAL.md)）；由 `tools/gen_uvm_agents.py` 產生 agent 的 49 個 VIP 另在 Verilator 上執行 `<prefix>_func_test`（scoreboard 以 DUT 參考模型比對）。
3. **Mutation testing**（`tools/mutation_score.py`）：對 DUT 模型注入運算子與常數錯誤，檢查功能測試能否偵測，作為「測試是否足夠」的客觀指標，結果寫入 `mutation_report.csv`。

判定標準：

| 判定 | 條件 |
|---|---|
| ✅ Sufficient | 功能測試通過，≥ 10 個 check，mutation score ≥ 80% |
| 🟡 Partial | 功能測試通過，但 check < 10 或 mutation score 50–79% |
| ❌ Insufficient | 沒有功能測試、測試失敗或 mutation score < 50% |

模型缺陷（XFAIL）與模型未實作的功能另列為缺口：它們是 DUT 模型的限制，不是測試的不足。

## 3. 各 VIP 判定

| VIP | 類別 | 功能測試 | Checks | 模擬器 | Mutation | 模型缺陷 | 判定 |
|---|---|---|---|---|---|---|---|
| [ACE-UVM-VIP](test_suites/ACE-UVM-VIP.md) | AMBA | `smoke_func_tb.sv` | 19 | verilator | 43/43 | 0 | ✅ Sufficient |
| [ACE_Lite-UVM-VIP](test_suites/ACE_Lite-UVM-VIP.md) | AMBA | `smoke_func_tb.sv` | 12 | iverilog | 12/19 | 0 | 🟡 Partial |
| [AHB-VIP](test_suites/AHB-VIP.md) | AMBA | `smoke_func_tb.sv`, `func_ahb_tb.sv` | 38 | iverilog | 28/28 | 0 | ✅ Sufficient |
| [APB-VIP](test_suites/APB-VIP.md) | AMBA | `smoke_func_tb.sv`, `func_apb_tb.sv` | 22 | iverilog | 15/15 | 0 | ✅ Sufficient |
| [ATB-UVM-VIP](test_suites/ATB-UVM-VIP.md) | Debug | `smoke_func_tb.sv` | 9 | iverilog | 4/6 | 0 | 🟡 Partial |
| [AVSBus-VIP](test_suites/AVSBus-VIP.md) | Power | `func_avsbus_tb.sv` | 14 | verilator | 11/12 | 0 | ✅ Sufficient |
| [AXI-VIP](test_suites/AXI-VIP.md) | AMBA | `smoke_func_tb.sv`, `func_axi_tb.sv` | 51 | iverilog | 23/23 | 0 | ✅ Sufficient |
| [AXI4_Lite-UVM-VIP](test_suites/AXI4_Lite-UVM-VIP.md) | AMBA | `smoke_func_tb.sv` | 172 | iverilog | 32/32 | 0 | ✅ Sufficient |
| [AXI_Stream-UVM-VIP](test_suites/AXI_Stream-UVM-VIP.md) | AMBA | `smoke_func_tb.sv` | 17 | iverilog | 22/22 | 0 | ✅ Sufficient |
| [Avalon_MM-UVM-VIP](test_suites/Avalon_MM-UVM-VIP.md) | Interconnect | `smoke_func_tb.sv` | 34 | iverilog | 8/15 | 0 | 🟡 Partial |
| [Avalon_ST-UVM-VIP](test_suites/Avalon_ST-UVM-VIP.md) | Interconnect | `smoke_func_tb.sv`, `func_avalon_st_tb.sv` | 31 | iverilog | 17/17 | 0 | ✅ Sufficient |
| [Bluetooth5-VIP](test_suites/Bluetooth5-VIP.md) | Storage/Debug | `func_bluetooth5_tb.sv` | 28 | verilator | 11/11 | 0 | ✅ Sufficient |
| [CAN-VIP](test_suites/CAN-VIP.md) | Automotive | `func_can_tb.sv` | 19 | verilator | 10/10 | 0 | ✅ Sufficient |
| [CAN_FD-UVM-VIP](test_suites/CAN_FD-UVM-VIP.md) | Automotive | `smoke_func_tb.sv` | 14 | iverilog | 13/16 | 0 | ✅ Sufficient |
| [CAN_XL-UVM-VIP](test_suites/CAN_XL-UVM-VIP.md) | Automotive | `smoke_func_tb.sv` | 38 | verilator | 28/28 | 0 | ✅ Sufficient |
| [CCIX-VIP](test_suites/CCIX-VIP.md) | Interconnect | `func_ccix_tb.sv` | 13 | iverilog | 15/15 | 0 | ✅ Sufficient |
| [CHI-UVM-VIP](test_suites/CHI-UVM-VIP.md) | AMBA | `smoke_func_tb.sv` | 11 | iverilog | 7/10 | 0 | 🟡 Partial |
| [CPRI-VIP](test_suites/CPRI-VIP.md) | Telecom | `func_cpri_tb.sv` | 17 | iverilog | 19/19 | 0 | ✅ Sufficient |
| [CSE-VIP](test_suites/CSE-VIP.md) | MIPI | `func_cse_tb.sv` | 34 | iverilog | 25/25 | 0 | ✅ Sufficient |
| [CSI_2-VIP](test_suites/CSI_2-VIP.md) | MIPI | `func_mipi_tb.sv` | 29 | verilator | 11/11 | 0 | ✅ Sufficient |
| [CXL-VIP](test_suites/CXL-VIP.md) | Interconnect | `smoke_func_tb.sv`, `func_cxl_mem_tb.sv` | 41 | verilator | 37/37 | 0 | ✅ Sufficient |
| [CXS-VIP](test_suites/CXS-VIP.md) | Interconnect | `func_cxs_tb.sv` | 11 | iverilog | 10/10 | 0 | ✅ Sufficient |
| [C_PHY-VIP](test_suites/C_PHY-VIP.md) | MIPI | `func_mipi_tb.sv` | 29 | verilator | 11/11 | 0 | ✅ Sufficient |
| [DBI-VIP](test_suites/DBI-VIP.md) | MIPI | `func_dbi_tb.sv` | 15 | verilator | 9/10 | 0 | ✅ Sufficient |
| [DDR-VIP](test_suites/DDR-VIP.md) | Memory | `func_mem_tb.sv` | 20 | verilator | 7/7 | 0 | ✅ Sufficient |
| [DDR5-VIP](test_suites/DDR5-VIP.md) | Memory | `smoke_func_tb.sv`, `func_ddr5_tb.sv`, `func_ddr5_dev_tb.sv` | 103 | iverilog/verilator | 33/33 | 0 | ✅ Sufficient |
| [DFI-VIP](test_suites/DFI-VIP.md) | Memory | `func_dfi_tb.sv` | 29 | verilator | 12/12 | 0 | ✅ Sufficient |
| [DPI-VIP](test_suites/DPI-VIP.md) | MIPI | `func_dpi_tb.sv` | 10 | iverilog | 20/20 | 0 | ✅ Sufficient |
| [DSI-VIP](test_suites/DSI-VIP.md) | MIPI | `func_mipi_tb.sv` | 29 | verilator | 11/11 | 0 | ✅ Sufficient |
| [D_PHY-VIP](test_suites/D_PHY-VIP.md) | MIPI | `func_mipi_tb.sv` | 29 | verilator | 11/11 | 0 | ✅ Sufficient |
| [DigRF-VIP](test_suites/DigRF-VIP.md) | MIPI | `func_mipi_tb.sv` | 20 | verilator | 10/12 | 0 | ✅ Sufficient |
| [DisplayPort2-VIP](test_suites/DisplayPort2-VIP.md) | Storage/Debug | `func_displayport2_tb.sv` | 16 | iverilog | 23/23 | 0 | ✅ Sufficient |
| [ETH800G-VIP](test_suites/ETH800G-VIP.md) | Networking | `smoke_func_tb.sv`, `func_eth800g_tb.sv` | 30 | iverilog | 21/21 | 0 | ✅ Sufficient |
| [EtherCAT-VIP](test_suites/EtherCAT-VIP.md) | Industrial | `smoke_func_tb.sv` | 22 | iverilog | 2/3 | 0 | 🟡 Partial |
| [Ethernet-VIP](test_suites/Ethernet-VIP.md) | Networking | `smoke_func_tb.sv`, `func_ethernet_tb.sv` | 37 | iverilog | 24/26 | 0 | ✅ Sufficient |
| [Ethernet_AVB_TSN-VIP](test_suites/Ethernet_AVB_TSN-VIP.md) | Automotive | `func_avb_tsn_tb.sv` | 23 | iverilog | 24/24 | 0 | ✅ Sufficient |
| [FC-VIP](test_suites/FC-VIP.md) | Networking | `func_fc_tb.sv` | 30 | verilator | 12/12 | 0 | ✅ Sufficient |
| [FlexRay-VIP](test_suites/FlexRay-VIP.md) | Automotive | `func_flexray_tb.sv` | 38 | iverilog | 20/20 | 0 | ✅ Sufficient |
| [GMII-UVM-VIP](test_suites/GMII-UVM-VIP.md) | Networking | `smoke_func_tb.sv` | 22 | iverilog | 2/3 | 0 | 🟡 Partial |
| [GPIO-UVM-VIP](test_suites/GPIO-UVM-VIP.md) | Peripherals | `smoke_func_tb.sv` | 42 | iverilog | 1/1 | 0 | ✅ Sufficient |
| [HBM-VIP](test_suites/HBM-VIP.md) | Memory | `func_mem_tb.sv` | 20 | verilator | 6/6 | 0 | ✅ Sufficient |
| [HBM3E-VIP](test_suites/HBM3E-VIP.md) | Memory | `smoke_func_tb.sv`, `func_hbm3e_tb.sv`, `func_hbm_dev_tb.sv` | 116 | iverilog/verilator | 40/40 | 0 | ✅ Sufficient |
| [HBM5-VIP](test_suites/HBM5-VIP.md) | Memory | `func_mem_tb.sv` | 16 | verilator | 5/5 | 0 | ✅ Sufficient |
| [HDCP-VIP](test_suites/HDCP-VIP.md) | Security | `func_hdcp_tb.sv` | 20 | verilator | 10/12 | 0 | ✅ Sufficient |
| [HDMI-VIP](test_suites/HDMI-VIP.md) | Video | `func_hdmi_tb.sv` | 20 | iverilog | 25/25 | 0 | ✅ Sufficient |
| [HSI-VIP](test_suites/HSI-VIP.md) | MIPI | `func_mipi_tb.sv` | 19 | verilator | 11/12 | 0 | ✅ Sufficient |
| [HyperBus-UVM-VIP](test_suites/HyperBus-UVM-VIP.md) | Memory | `smoke_func_tb.sv` | 40 | iverilog | 30/30 | 0 | ✅ Sufficient |
| [I2C-VIP](test_suites/I2C-VIP.md) | Serial | `smoke_func_tb.sv` | 6 | iverilog | 17/23 | 0 | 🟡 Partial |
| [I2S-VIP](test_suites/I2S-VIP.md) | Audio | `func_i2s_tb.sv` | 11 | verilator | 5/5 | 0 | ✅ Sufficient |
| [I3C-VIP](test_suites/I3C-VIP.md) | MIPI | `func_i3c_tb.sv` | 25 | verilator | 9/11 | 0 | ✅ Sufficient |
| [IO_Link-VIP](test_suites/IO_Link-VIP.md) | Industrial | `smoke_func_tb.sv` | 7 | iverilog | 23/30 | 0 | 🟡 Partial |
| [Interlaken-VIP](test_suites/Interlaken-VIP.md) | Networking | `func_intlkn_tb.sv` | 23 | iverilog | 24/30 | 0 | ✅ Sufficient |
| [JESD204-VIP](test_suites/JESD204-VIP.md) | SerDes | `func_jesd204_tb.sv` | 15 | iverilog | 27/30 | 0 | ✅ Sufficient |
| [JTAG-VIP](test_suites/JTAG-VIP.md) | Storage/Debug | `func_jtag_tb.sv` | 25 | verilator | 10/12 | 0 | ✅ Sufficient |
| [LIN-VIP](test_suites/LIN-VIP.md) | Automotive | `func_lin_tb.sv` | 25 | verilator | 8/8 | 0 | ✅ Sufficient |
| [LPDDR-VIP](test_suites/LPDDR-VIP.md) | Memory | `func_mem_tb.sv` | 14 | verilator | 4/4 | 0 | ✅ Sufficient |
| [LPDDR6-VIP](test_suites/LPDDR6-VIP.md) | Memory | `smoke_func_tb.sv`, `func_lpddr6_tb.sv` | 36 | iverilog | 21/21 | 0 | ✅ Sufficient |
| [LPI-VIP](test_suites/LPI-VIP.md) | Power | `func_lpi_tb.sv` | 12 | iverilog | 14/16 | 0 | ✅ Sufficient |
| [LTI-VIP](test_suites/LTI-VIP.md) | Interconnect | `func_lti_tb.sv` | 10 | iverilog | 18/19 | 0 | ✅ Sufficient |
| [MACsec-UVM-VIP](test_suites/MACsec-UVM-VIP.md) | Security | `smoke_func_tb.sv` | 50 | iverilog | 39/39 | 0 | ✅ Sufficient |
| [MCTP-UVM-VIP](test_suites/MCTP-UVM-VIP.md) | Power | `smoke_func_tb.sv` | 23 | iverilog | 44/44 | 0 | ✅ Sufficient |
| [MDIO-UVM-VIP](test_suites/MDIO-UVM-VIP.md) | Networking | `smoke_func_tb.sv`, `func_mdio_tb.sv` | 23 | iverilog | 20/20 | 0 | ✅ Sufficient |
| [MIL_STD_1553-VIP](test_suites/MIL_STD_1553-VIP.md) | Aerospace | `smoke_func_tb.sv` | 19 | iverilog | 12/15 | 0 | ✅ Sufficient |
| [M_PHY-VIP](test_suites/M_PHY-VIP.md) | MIPI | `func_mipi_tb.sv` | 29 | verilator | 11/11 | 0 | ✅ Sufficient |
| [NC-SI-UVM-VIP](test_suites/NC-SI-UVM-VIP.md) | Networking | `smoke_func_tb.sv` | 41 | iverilog | 41/41 | 0 | ✅ Sufficient |
| [NVMe-VIP](test_suites/NVMe-VIP.md) | Storage/Debug | `smoke_func_tb.sv`, `func_nvme_tb.sv` | 57 | verilator | 8/8 | 0 | ✅ Sufficient |
| [OBI-UVM-VIP](test_suites/OBI-UVM-VIP.md) | Interconnect | `smoke_func_tb.sv` | 39 | iverilog | 13/13 | 0 | ✅ Sufficient |
| [OCP-VIP](test_suites/OCP-VIP.md) | Interconnect | `func_ocp_tb.sv` | 12 | verilator | 7/7 | 0 | ✅ Sufficient |
| [ONFI-VIP](test_suites/ONFI-VIP.md) | Memory | `func_onfi_tb.sv` | 39 | verilator | 8/8 | 0 | ✅ Sufficient |
| [OneWire-UVM-VIP](test_suites/OneWire-UVM-VIP.md) | Peripherals | `smoke_func_tb.sv` | 25 | iverilog | 13/16 | 0 | ✅ Sufficient |
| [PCIe-VIP](test_suites/PCIe-VIP.md) | Interconnect | `smoke_func_tb.sv`, `func_pcie_dl_tb.sv` | 100 | verilator | 45/45 | 0 | ✅ Sufficient |
| [PCIe_IDE-UVM-VIP](test_suites/PCIe_IDE-UVM-VIP.md) | Security | `smoke_func_tb.sv` | 44 | iverilog | 37/37 | 0 | ✅ Sufficient |
| [PTP-VIP](test_suites/PTP-VIP.md) | Networking | `smoke_func_tb.sv` | 18 | iverilog | 8/10 | 0 | ✅ Sufficient |
| [PWM-UVM-VIP](test_suites/PWM-UVM-VIP.md) | Peripherals | `smoke_func_tb.sv` | 35 | iverilog | 10/12 | 0 | ✅ Sufficient |
| [RFFE-VIP](test_suites/RFFE-VIP.md) | MIPI | `func_rffe_tb.sv` | 14 | iverilog | 25/29 | 0 | ✅ Sufficient |
| [RGMII-UVM-VIP](test_suites/RGMII-UVM-VIP.md) | Networking | `smoke_func_tb.sv` | 14 | iverilog | 2/2 | 0 | ✅ Sufficient |
| [RVFI-UVM-VIP](test_suites/RVFI-UVM-VIP.md) | Debug | `smoke_func_tb.sv` | 59 | iverilog | 44/44 | 0 | ✅ Sufficient |
| [RapidIO-VIP](test_suites/RapidIO-VIP.md) | Interconnect | `smoke_func_tb.sv` | 21 | iverilog | 2/3 | 0 | 🟡 Partial |
| [SAS-VIP](test_suites/SAS-VIP.md) | Storage | `func_sas_tb.sv` | 42 | verilator | 10/10 | 0 | ✅ Sufficient |
| [SATA-VIP](test_suites/SATA-VIP.md) | Storage/Debug | `func_sata_tb.sv` | 28 | verilator | 10/11 | 0 | ✅ Sufficient |
| [SD-VIP](test_suites/SD-VIP.md) | Memory | `func_sd_tb.sv` | 35 | verilator | 10/10 | 0 | ✅ Sufficient |
| [SDIO-UVM-VIP](test_suites/SDIO-UVM-VIP.md) | Storage | `smoke_func_tb.sv` | 15 | iverilog | 10/18 | 0 | 🟡 Partial |
| [SENT-VIP](test_suites/SENT-VIP.md) | Automotive | `smoke_func_tb.sv` | 12 | iverilog | 12/16 | 0 | 🟡 Partial |
| [SGMII-UVM-VIP](test_suites/SGMII-UVM-VIP.md) | Networking | `smoke_func_tb.sv` | 23 | verilator | 28/28 | 0 | ✅ Sufficient |
| [SLIMbus-VIP](test_suites/SLIMbus-VIP.md) | MIPI | `func_slimbus_tb.sv` | 14 | iverilog | 23/23 | 0 | ✅ Sufficient |
| [SMBus-UVM-VIP](test_suites/SMBus-UVM-VIP.md) | Power | `smoke_func_tb.sv` | 40 | iverilog | 28/28 | 0 | ✅ Sufficient |
| [SPI-VIP](test_suites/SPI-VIP.md) | Serial | `smoke_func_tb.sv` | 8 | iverilog | 22/28 | 0 | 🟡 Partial |
| [SPMI-VIP](test_suites/SPMI-VIP.md) | MIPI | `func_spmi_tb.sv` | 15 | iverilog | 24/29 | 0 | ✅ Sufficient |
| [SUE-UVM-VIP](test_suites/SUE-UVM-VIP.md) | Networking | `smoke_func_tb.sv` | 30 | iverilog | 43/43 | 0 | ✅ Sufficient |
| [SWD-VIP](test_suites/SWD-VIP.md) | Debug | `func_swd_tb.sv` | 23 | verilator | 11/12 | 0 | ✅ Sufficient |
| [Security-VIP](test_suites/Security-VIP.md) | Security | `func_security_tb.sv` | 17 | iverilog | 25/25 | 0 | ✅ Sufficient |
| [SoundWire-VIP](test_suites/SoundWire-VIP.md) | MIPI | `func_soundwire_tb.sv` | 18 | verilator | 6/7 | 0 | ✅ Sufficient |
| [SpaceWire-UVM-VIP](test_suites/SpaceWire-UVM-VIP.md) | Aerospace | `smoke_func_tb.sv` | 38 | iverilog | 40/40 | 0 | ✅ Sufficient |
| [T1S_PLCA-UVM-VIP](test_suites/T1S_PLCA-UVM-VIP.md) | Automotive | `smoke_func_tb.sv` | 19 | verilator | 41/41 | 0 | ✅ Sufficient |
| [TDM-UVM-VIP](test_suites/TDM-UVM-VIP.md) | Audio | `smoke_func_tb.sv` | 13 | iverilog | 17/17 | 0 | ✅ Sufficient |
| [TileLink-VIP](test_suites/TileLink-VIP.md) | Interconnect | `func_tilelink_tb.sv` | 10 | verilator | 9/9 | 0 | ✅ Sufficient |
| [ToggleNAND-VIP](test_suites/ToggleNAND-VIP.md) | Storage | `func_tnand_tb.sv` | 33 | verilator | 10/12 | 0 | ✅ Sufficient |
| [TypeC-VIP](test_suites/TypeC-VIP.md) | USB | `func_typec_tb.sv` | 9 | iverilog | 1/1 | 0 | 🟡 Partial |
| [UALink-VIP](test_suites/UALink-VIP.md) | Interconnect | `smoke_func_tb.sv`, `func_ualink_tl_tb.sv` | 34 | iverilog/verilator | 38/38 | 0 | ✅ Sufficient |
| [UART-VIP](test_suites/UART-VIP.md) | Serial | `smoke_func_tb.sv` | 11 | iverilog | 13/19 | 0 | 🟡 Partial |
| [UCIe-VIP](test_suites/UCIe-VIP.md) | Interconnect | `smoke_func_tb.sv`, `func_ucie_d2d_tb.sv` | 83 | iverilog/verilator | 43/43 | 0 | ✅ Sufficient |
| [UEC-VIP](test_suites/UEC-VIP.md) | Networking | `smoke_func_tb.sv` | 12 | iverilog | 8/12 | 0 | 🟡 Partial |
| [UFS-VIP](test_suites/UFS-VIP.md) | Memory | `func_ufs_tb.sv` | 28 | verilator | 11/12 | 0 | ✅ Sufficient |
| [USB-VIP](test_suites/USB-VIP.md) | USB | `func_usb_tb.sv` | 29 | iverilog | 26/30 | 0 | ✅ Sufficient |
| [USB2-VIP](test_suites/USB2-VIP.md) | USB | `smoke_func_tb.sv` | 15 | iverilog | 21/30 | 0 | 🟡 Partial |
| [USB3-VIP](test_suites/USB3-VIP.md) | USB | `func_usb3_tb.sv` | 28 | iverilog | 26/30 | 0 | ✅ Sufficient |
| [USB4-VIP](test_suites/USB4-VIP.md) | USB | `func_usb4_tb.sv` | 26 | verilator | 11/12 | 0 | ✅ Sufficient |
| [USB_PD-VIP](test_suites/USB_PD-VIP.md) | USB | `func_usb_pd_tb.sv` | 29 | iverilog | 27/30 | 0 | ✅ Sufficient |
| [USXGMII-UVM-VIP](test_suites/USXGMII-UVM-VIP.md) | Networking | `smoke_func_tb.sv` | 29 | iverilog | 46/46 | 0 | ✅ Sufficient |
| [UniPro-VIP](test_suites/UniPro-VIP.md) | MIPI | `func_mipi_tb.sv` | 29 | verilator | 11/11 | 0 | ✅ Sufficient |
| [UniPro_Mem-VIP](test_suites/UniPro_Mem-VIP.md) | Memory | `func_unipro_mem_tb.sv` | 22 | iverilog | 22/22 | 0 | ✅ Sufficient |
| [WTB-UVM-VIP](test_suites/WTB-UVM-VIP.md) | Debug | `smoke_func_tb.sv` | 9 | iverilog | 4/6 | 0 | 🟡 Partial |
| [Wishbone-UVM-VIP](test_suites/Wishbone-UVM-VIP.md) | Interconnect | `smoke_func_tb.sv`, `func_wishbone_tb.sv` | 34 | iverilog | 11/11 | 0 | ✅ Sufficient |
| [XGMII-UVM-VIP](test_suites/XGMII-UVM-VIP.md) | Networking | `smoke_func_tb.sv` | 14 | iverilog | 1/1 | 0 | ✅ Sufficient |
| [ddr6-VIP](test_suites/ddr6-VIP.md) | Memory | `func_mem_tb.sv` | 16 | verilator | 5/5 | 0 | ✅ Sufficient |
| [ddr7-VIP](test_suites/ddr7-VIP.md) | Memory | `func_mem_tb.sv` | 16 | verilator | 5/5 | 0 | ✅ Sufficient |
| [eCPRI-VIP](test_suites/eCPRI-VIP.md) | Telecom | `func_ecpri_tb.sv` | 20 | iverilog | 28/30 | 0 | ✅ Sufficient |
| [eMMC-VIP](test_suites/eMMC-VIP.md) | Memory | `func_emmc_tb.sv` | 43 | verilator | 10/10 | 0 | ✅ Sufficient |
| [eSPI-UVM-VIP](test_suites/eSPI-UVM-VIP.md) | Peripherals | `smoke_func_tb.sv` | 54 | iverilog | 42/42 | 0 | ✅ Sufficient |
| [eUSB2-VIP](test_suites/eUSB2-VIP.md) | USB | `func_eusb2_tb.sv` | 25 | iverilog | 26/30 | 0 | ✅ Sufficient |
| [gddr5-VIP](test_suites/gddr5-VIP.md) | Memory | `func_mem_tb.sv` | 15 | verilator | 7/7 | 0 | ✅ Sufficient |
| [gddr6-VIP](test_suites/gddr6-VIP.md) | Memory | `func_mem_tb.sv` | 15 | verilator | 7/7 | 0 | ✅ Sufficient |
| [gddr7-VIP](test_suites/gddr7-VIP.md) | Memory | `func_mem_tb.sv` | 15 | verilator | 7/7 | 0 | ✅ Sufficient |
| [hbm2-VIP](test_suites/hbm2-VIP.md) | Memory | `func_mem_tb.sv` | 15 | verilator | 7/7 | 0 | ✅ Sufficient |
| [hbm3-VIP](test_suites/hbm3-VIP.md) | Memory | `func_mem_tb.sv` | 15 | verilator | 7/7 | 0 | ✅ Sufficient |
| [hbm4-VIP](test_suites/hbm4-VIP.md) | Memory | `func_mem_tb.sv` | 15 | verilator | 7/7 | 0 | ✅ Sufficient |
| [lpddr5-VIP](test_suites/lpddr5-VIP.md) | Memory | `func_mem_tb.sv` | 15 | verilator | 7/7 | 0 | ✅ Sufficient |
| [lpddr5x-VIP](test_suites/lpddr5x-VIP.md) | Memory | `func_mem_tb.sv` | 26 | iverilog | 24/24 | 0 | ✅ Sufficient |
| [lpddr7-VIP](test_suites/lpddr7-VIP.md) | Memory | `func_mem_tb.sv` | 26 | iverilog | 24/24 | 0 | ✅ Sufficient |
| [xSPI-UVM-VIP](test_suites/xSPI-UVM-VIP.md) | Serial | `smoke_func_tb.sv` | 18 | iverilog | 24/24 | 0 | ✅ Sufficient |

## 4. 功能測試找到的 DUT 模型缺陷

## 5. 重新產生

```bash
bash tools/extract_vips.sh                # 解開 vips/*.zip 到 build/vips
python3 smoke/flatten.py && python3 tools/run_func_tests.py   # func_report.csv
python3 tools/mutation_score.py -j 4       # mutation_report.csv（數小時）
python3 tools/gen_test_suite_docs.py       # 本文件與 docs/test_suites/
```
