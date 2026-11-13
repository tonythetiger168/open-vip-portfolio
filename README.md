# Open VIP Portfolio

> TV／STB／IPCAM：請先核對 [平台驗證矩陣](docs/design/platform_bus_host_matrix.md) 的 DUT／agent 角色。測試套件的 Sufficient 僅針對模型範圍，不等於 host、DMA 或產品合規完成。

> 新增 [shared UVM／六類 coverage 計畫](docs/design/platform_shared_uvm_plan.md) 及有界 RTL seed/replay gate；procedural fixture campaign 通過不等於 UVM 或完整 SoC coverage 100%。

> A comprehensive, open-source collection of **164 individual protocol VIP (Verification IP) testbenches** for SystemVerilog/UVM-based SoC/ASIC verification.

[![License](https://img.shields.io/badge/License-Apache%%202.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)
[![VIP Count](https://img.shields.io/badge/VIPs-164-brightgreen.svg)]()
[![Protocols](https://img.shields.io/badge/Protocols-150-orange.svg)]()

---

## Overview

This repository provides a **modular, per-protocol verification IP library** covering major interface standards used in modern semiconductor design. Each entry is packaged as a standalone zip file.

- **164 UVM VIPs** -- complete UVM testbench environments (agent, sequences, scoreboard, coverage, SVA checks)
- **RTL IPs** -- the synthesizable reference RTL lives in [open-ip-portfolio](https://github.com/tonythetiger168/open-ip-portfolio); the column `open-ip 對應` of the CSV maps each VIP to its IP there: each `/`-separated name is the stem of one `rtl/<name>_top.sv`, and `無對應` means open-ip-portfolio has no RTL for it yet
- **150 distinct protocols** across 20 families

All source files are licensed under **Apache License 2.0**.

---

## Protocol Coverage

### AMBA (9)

| Protocol | Type | File | Size |
|----------|------|------|------|
| ACE | UVM VIP | `ACE-UVM-VIP.zip` | 31KB |
| ACE-Lite | UVM VIP | `ACE_Lite-UVM-VIP.zip` | 24KB |
| AHB | UVM VIP | `AHB-VIP.zip` | 35KB |
| APB | UVM VIP | `APB-VIP.zip` | 33KB |
| AXI | UVM VIP | `AXI-VIP.zip` | 35KB |
| AXI-Stream | UVM VIP | `AXI_Stream-UVM-VIP.zip` | 23KB |
| AXI4-Lite | UVM VIP | `AXI4_Lite-UVM-VIP.zip` | 24KB |
| CHI | UVM VIP | `CHI-UVM-VIP.zip` | 34KB |
| CHI Issue H link level (SN-F, flits, L-credits) | UVM VIP | `CHI_H-UVM-VIP.zip` | 31KB |

### Aerospace (2)

| Protocol | Type | File | Size |
|----------|------|------|------|
| MIL-STD-1553 | UVM VIP | `MIL_STD_1553-VIP.zip` | 24KB |
| SpaceWire (ECSS-E-ST-50-12C) | UVM VIP | `SpaceWire-UVM-VIP.zip` | 27KB |

### Audio (4)

| Protocol | Type | File | Size |
|----------|------|------|------|
| I2S Audio | UVM VIP | `I2S-VIP.zip` | 35KB |
| I2S audio codec (clock master) | UVM VIP | `I2S_Codec-UVM-VIP.zip` | 21KB |
| S/PDIF (IEC 60958) | UVM VIP | `SPDIF-UVM-VIP.zip` | 23KB |
| TDM audio (DSP mode) | UVM VIP | `TDM-UVM-VIP.zip` | 20KB |

### Automotive (8)

| Protocol | Type | File | Size |
|----------|------|------|------|
| 10BASE-T1S PLCA (IEEE 802.3cg) | UVM VIP | `T1S_PLCA-UVM-VIP.zip` | 23KB |
| CAN | UVM VIP | `CAN-VIP.zip` | 42KB |
| CAN XL | UVM VIP | `CAN_XL-UVM-VIP.zip` | 27KB |
| CAN-FD | UVM VIP | `CAN_FD-UVM-VIP.zip` | 23KB |
| Ethernet-AVB-TSN | UVM VIP | `Ethernet_AVB_TSN-VIP.zip` | 66KB |
| FlexRay | UVM VIP | `FlexRay-VIP.zip` | 38KB |
| LIN | UVM VIP | `LIN-VIP.zip` | 37KB |
| SENT | UVM VIP | `SENT-VIP.zip` | 23KB |

### Debug (4)

| Protocol | Type | File | Size |
|----------|------|------|------|
| ARM Serial Wire Debug | UVM VIP | `SWD-VIP.zip` | 31KB |
| ATB | UVM VIP | `ATB-UVM-VIP.zip` | 23KB |
| RVFI (RISC-V Formal Interface, RV32I) | UVM VIP | `RVFI-UVM-VIP.zip` | 29KB |
| WTB | UVM VIP | `WTB-UVM-VIP.zip` | 23KB |

### Industrial (2)

| Protocol | Type | File | Size |
|----------|------|------|------|
| EtherCAT | UVM VIP | `EtherCAT-VIP.zip` | 24KB |
| IO-Link | UVM VIP | `IO_Link-VIP.zip` | 24KB |

### Interconnect (15)

| Protocol | Type | File | Size |
|----------|------|------|------|
| ARM Local Translation Interface | UVM VIP | `LTI-VIP.zip` | 28KB |
| Avalon-MM | UVM VIP | `Avalon_MM-UVM-VIP.zip` | 24KB |
| Avalon-ST | UVM VIP | `Avalon_ST-UVM-VIP.zip` | 24KB |
| BoW die-to-die PHY v2.0 (OCP ODSA Bunch of Wires) | UVM VIP | `BoW-UVM-VIP.zip` | 28KB |
| CCIX Cache Coherent Interconnect | UVM VIP | `CCIX-VIP.zip` | 28KB |
| CXL | UVM VIP | `CXL-VIP.zip` | 54KB |
| CXS CCIX Stream Interface | UVM VIP | `CXS-VIP.zip` | 28KB |
| OBI | UVM VIP | `OBI-UVM-VIP.zip` | 21KB |
| OCP-IP Open Core Protocol | UVM VIP | `OCP-VIP.zip` | 28KB |
| PCIe | UVM VIP | `PCIe-VIP.zip` | 65KB |
| RapidIO | UVM VIP | `RapidIO-VIP.zip` | 23KB |
| TileLink (TL-UL/TL-C) | UVM VIP | `TileLink-VIP.zip` | 29KB |
| UALink | UVM VIP | `UALink-VIP.zip` | 41KB |
| UCIe | UVM VIP | `UCIe-VIP.zip` | 43KB |
| Wishbone | UVM VIP | `Wishbone-UVM-VIP.zip` | 24KB |

### MIPI (18)

| Protocol | Type | File | Size |
|----------|------|------|------|
| C-PHY | UVM VIP | `C_PHY-VIP.zip` | 36KB |
| CSE | UVM VIP | `CSE-VIP.zip` | 36KB |
| CSI-2 | UVM VIP | `CSI_2-VIP.zip` | 44KB |
| CSI-2 camera sensor transmitter | UVM VIP | `CSI2_Sensor-UVM-VIP.zip` | 25KB |
| D-PHY | UVM VIP | `D_PHY-VIP.zip` | 36KB |
| DigRF | UVM VIP | `DigRF-VIP.zip` | 33KB |
| DSI | UVM VIP | `DSI-VIP.zip` | 36KB |
| HSI | UVM VIP | `HSI-VIP.zip` | 34KB |
| M-PHY | UVM VIP | `M_PHY-VIP.zip` | 36KB |
| MIPI DBI (Display Bus Interface) | UVM VIP | `DBI-VIP.zip` | 28KB |
| MIPI DPI (Display Pixel Interface) | UVM VIP | `DPI-VIP.zip` | 27KB |
| MIPI I3C | UVM VIP | `I3C-VIP.zip` | 35KB |
| MIPI RFFE | UVM VIP | `RFFE-VIP.zip` | 30KB |
| MIPI SLIMbus | UVM VIP | `SLIMbus-VIP.zip` | 31KB |
| MIPI SoundWire | UVM VIP | `SoundWire-VIP.zip` | 32KB |
| MIPI SPMI | UVM VIP | `SPMI-VIP.zip` | 30KB |
| SCCB / I2C camera sensor control | UVM VIP | `SCCB_Sensor-UVM-VIP.zip` | 22KB |
| UniPro | UVM VIP | `UniPro-VIP.zip` | 36KB |

### Memory (26)

| Protocol | Type | File | Size |
|----------|------|------|------|
| DDR | UVM VIP | `DDR-VIP.zip` | 40KB |
| DDR5 | UVM VIP | `DDR5-VIP.zip` | 37KB |
| DDR6 | UVM VIP | `ddr6-VIP.zip` | 27KB |
| DDR7 | UVM VIP | `ddr7-VIP.zip` | 27KB |
| DFI 5.0 (MC-PHY Interface) | UVM VIP | `DFI-VIP.zip` | 32KB |
| eMMC | UVM VIP | `eMMC-VIP.zip` | 53KB |
| GDDR5 | UVM VIP | `gddr5-VIP.zip` | 29KB |
| GDDR6 | UVM VIP | `gddr6-VIP.zip` | 30KB |
| GDDR7 | UVM VIP | `gddr7-VIP.zip` | 30KB |
| HBM | UVM VIP | `HBM-VIP.zip` | 29KB |
| HBM2 | UVM VIP | `hbm2-VIP.zip` | 29KB |
| HBM3 | UVM VIP | `hbm3-VIP.zip` | 29KB |
| HBM3E | UVM VIP | `HBM3E-VIP.zip` | 37KB |
| HBM4 | UVM VIP | `hbm4-VIP.zip` | 30KB |
| HBM5 | UVM VIP | `HBM5-VIP.zip` | 27KB |
| HyperBus / HyperRAM | UVM VIP | `HyperBus-UVM-VIP.zip` | 26KB |
| LPDDR | UVM VIP | `LPDDR-VIP.zip` | 29KB |
| LPDDR5 | UVM VIP | `lpddr5-VIP.zip` | 30KB |
| LPDDR5X | UVM VIP | `lpddr5x-VIP.zip` | 43KB |
| LPDDR6 | UVM VIP | `LPDDR6-VIP.zip` | 22KB |
| LPDDR7 | UVM VIP | `lpddr7-VIP.zip` | 32KB |
| ONFI | UVM VIP | `ONFI-VIP.zip` | 53KB |
| Quad-SPI NOR flash (XIP) | UVM VIP | `SPI_NOR-UVM-VIP.zip` | 23KB |
| SD | UVM VIP | `SD-VIP.zip` | 55KB |
| UFS | UVM VIP | `UFS-VIP.zip` | 35KB |
| UniPro-Mem | UVM VIP | `UniPro_Mem-VIP.zip` | 39KB |

### Networking (15)

| Protocol | Type | File | Size |
|----------|------|------|------|
| 800G Ethernet | UVM VIP | `ETH800G-VIP.zip` | 23KB |
| Ethernet | UVM VIP | `Ethernet-VIP.zip` | 57KB |
| FC | UVM VIP | `FC-VIP.zip` | 48KB |
| GMII | UVM VIP | `GMII-UVM-VIP.zip` | 23KB |
| GMII / RGMII Ethernet PHY link partner | UVM VIP | `GMII_PHY-UVM-VIP.zip` | 25KB |
| IEEE 1588 PTP | UVM VIP | `PTP-VIP.zip` | 23KB |
| Interlaken v1.2 | UVM VIP | `Interlaken-VIP.zip` | 30KB |
| MDIO | UVM VIP | `MDIO-UVM-VIP.zip` | 23KB |
| NC-SI (DMTF DSP0222, RBT) | UVM VIP | `NC-SI-UVM-VIP.zip` | 26KB |
| RGMII | UVM VIP | `RGMII-UVM-VIP.zip` | 23KB |
| SGMII | UVM VIP | `SGMII-UVM-VIP.zip` | 27KB |
| SUE / ESUN scale-up Ethernet transport | UVM VIP | `SUE-UVM-VIP.zip` | 23KB |
| UEC | UVM VIP | `UEC-VIP.zip` | 22KB |
| USXGMII (multi-rate 64b/66b) | UVM VIP | `USXGMII-UVM-VIP.zip` | 25KB |
| XGMII | UVM VIP | `XGMII-UVM-VIP.zip` | 23KB |

### Peripherals (5)

| Protocol | Type | File | Size |
|----------|------|------|------|
| 1-Wire | UVM VIP | `OneWire-UVM-VIP.zip` | 23KB |
| GPIO | UVM VIP | `GPIO-UVM-VIP.zip` | 29KB |
| IR remote control (NEC / RC5) | UVM VIP | `IR_Remote-UVM-VIP.zip` | 24KB |
| PWM | UVM VIP | `PWM-UVM-VIP.zip` | 29KB |
| eSPI (Enhanced SPI) | UVM VIP | `eSPI-UVM-VIP.zip` | 26KB |

### Power (4)

| Protocol | Type | File | Size |
|----------|------|------|------|
| ARM Q-Channel Low Power Interface | UVM VIP | `LPI-VIP.zip` | 29KB |
| AVSBus (Adaptive Voltage Scaling) | UVM VIP | `AVSBus-VIP.zip` | 31KB |
| MCTP over SMBus (DMTF DSP0237) | UVM VIP | `MCTP-UVM-VIP.zip` | 25KB |
| SMBus/PMBus | UVM VIP | `SMBus-UVM-VIP.zip` | 26KB |

### Security (7)

| Protocol | Type | File | Size |
|----------|------|------|------|
| Crypto / Security Engine | UVM VIP | `Security-VIP.zip` | 36KB |
| DVB CI / CI+ CAM (EN 50221, PC Card) | UVM VIP | `CI_CAM-UVM-VIP.zip` | 28KB |
| HDCP 2.3 Content Protection | UVM VIP | `HDCP-VIP.zip` | 32KB |
| ISO 7816-3 smartcard (T = 0, PPS) | UVM VIP | `Smartcard_ISO7816-UVM-VIP.zip` | 27KB |
| MACsec (IEEE 802.1AE, GCM-AES-128) | UVM VIP | `MACsec-UVM-VIP.zip` | 29KB |
| PCIe IDE (AES-256-GCM) | UVM VIP | `PCIe_IDE-UVM-VIP.zip` | 28KB |
| SPDM 1.4 Responder (DMTF DSP0274, device attestation) | UVM VIP | `SPDM-UVM-VIP.zip` | 27KB |

### SerDes (1)

| Protocol | Type | File | Size |
|----------|------|------|------|
| JESD204C | UVM VIP | `JESD204-VIP.zip` | 31KB |

### Serial (4)

| Protocol | Type | File | Size |
|----------|------|------|------|
| I2C | UVM VIP | `I2C-VIP.zip` | 33KB |
| SPI | UVM VIP | `SPI-VIP.zip` | 35KB |
| UART | UVM VIP | `UART-VIP.zip` | 36KB |
| xSPI (JESD251) | UVM VIP | `xSPI-UVM-VIP.zip` | 23KB |

### Storage (7)

| Protocol | Type | File | Size |
|----------|------|------|------|
| eMMC device (1-bit, RST_n) | UVM VIP | `eMMC_Device-UVM-VIP.zip` | 27KB |
| SAS-4 (Serial Attached SCSI) | UVM VIP | `SAS-VIP.zip` | 34KB |
| SD / eMMC card (1/4/8-bit, 512-byte blocks) | UVM VIP | `SDMMC_Card-UVM-VIP.zip` | 31KB |
| SD memory card (4-bit) | UVM VIP | `SD_Card-UVM-VIP.zip` | 27KB |
| SDIO | UVM VIP | `SDIO-UVM-VIP.zip` | 23KB |
| SCM dual-mode SSD (NVMe 2.1 multi-queue + FDP, CXL.mem byte port) | UVM VIP | `SCM_SSD-VIP.zip` | 18KB |
| Toggle Mode NAND | UVM VIP | `ToggleNAND-VIP.zip` | 33KB |

### Storage/Debug (5)

| Protocol | Type | File | Size |
|----------|------|------|------|
| Bluetooth5 | UVM VIP | `Bluetooth5-VIP.zip` | 36KB |
| DisplayPort2 | UVM VIP | `DisplayPort2-VIP.zip` | 42KB |
| JTAG | UVM VIP | `JTAG-VIP.zip` | 41KB |
| NVMe | UVM VIP | `NVMe-VIP.zip` | 35KB |
| SATA | UVM VIP | `SATA-VIP.zip` | 33KB |

### Telecom (2)

| Protocol | Type | File | Size |
|----------|------|------|------|
| CPRI v8.0 (eCPRI over CPR) | UVM VIP | `CPRI-VIP.zip` | 29KB |
| eCPRI over Ethernet | UVM VIP | `eCPRI-VIP.zip` | 30KB |

### USB (7)

| Protocol | Type | File | Size |
|----------|------|------|------|
| USB | UVM VIP | `USB-VIP.zip` | 74KB |
| USB Type-C Port Controller | UVM VIP | `TypeC-VIP.zip` | 31KB |
| USB-PD | UVM VIP | `USB_PD-VIP.zip` | 61KB |
| USB2 | UVM VIP | `USB2-VIP.zip` | 64KB |
| USB3 | UVM VIP | `USB3-VIP.zip` | 61KB |
| USB4 | UVM VIP | `USB4-VIP.zip` | 61KB |
| eUSB2 | UVM VIP | `eUSB2-VIP.zip` | 61KB |

### Video (5)

| Protocol | Type | File | Size |
|----------|------|------|------|
| HDMI 2.1 | UVM VIP | `HDMI-VIP.zip` | 38KB |
| HDMI CEC | UVM VIP | `HDMI_CEC-UVM-VIP.zip` | 24KB |
| HDMI source (TMDS, InfoFrames) | UVM VIP | `HDMI_Source-UVM-VIP.zip` | 28KB |
| MPEG-2 TS / TSI (ISO/IEC 13818-1) | UVM VIP | `MPEG_TS-UVM-VIP.zip` | 23KB |
| V-by-One HS panel sink | UVM VIP | `VbyOne_HS-UVM-VIP.zip` | 22KB |

### SoC Subsystem (14)

Phone SoC subsystem VIPs for the AXI4-manager IPs of open-ip-portfolio. Each zip is
standalone: APB4 agent + generated RAL, AXI4 subordinate / monitor / coverage (the
manager-port kit), reference-model scoreboards, an RTL snapshot, `tb/top_tb.sv`,
`sim/<ip>.f` and `sim/testlist.txt` for Verilator + uvm-core. See
[docs/SOC_SUBSYS.md](docs/SOC_SUBSYS.md).

| Protocol | Type | File | Size |
|----------|------|------|------|
| AXI4 manager port kit (shared by every subsystem VIP) | UVM VIP | `AXI4_Manager_Port-UVM-VIP.zip` | 32KB |
| CPU cluster memory traffic (AXI4 manager) | UVM VIP | `CPU_Cluster-UVM-VIP.zip` | 39KB |
| GPU 2D / blit engine (AXI4 manager) | UVM VIP | `GPU-UVM-VIP.zip` | 39KB |
| NPU convolution engine (AXI4 manager) | UVM VIP | `NPU-UVM-VIP.zip` | 39KB |
| Camera ISP: sensor input, black level, gain (AXI4 manager) | UVM VIP | `ISP-UVM-VIP.zip` | 40KB |
| Video codec DPCM encode / decode (AXI4 manager) | UVM VIP | `Video_Codec-UVM-VIP.zip` | 40KB |
| Display controller scan-out, CRC, underruns (AXI4 manager) | UVM VIP | `Display_Controller-UVM-VIP.zip` | 41KB |
| Audio DSP gain / mix / clip (AXI4 manager) | UVM VIP | `Audio_DSP-UVM-VIP.zip` | 40KB |
| Modem baseband scrambler + CRC-32 (AXI4 manager) | UVM VIP | `Modem-UVM-VIP.zip` | 39KB |
| Always-on sensor hub decimator (AXI4 manager) | UVM VIP | `Sensor_Hub-UVM-VIP.zip` | 41KB |
| SMMU / IOMMU translation, TLB, faults (AXI4 subordinate + manager) | UVM VIP | `SMMU-UVM-VIP.zip` | 41KB |
| System DMA, 4 channels (AXI4 manager) | UVM VIP | `DMA-UVM-VIP.zip` | 42KB |
| Interrupt controller, priority claim, event log (AXI4 manager) | UVM VIP | `Interrupt_Controller-UVM-VIP.zip` | 44KB |
| Timer / watchdog with timestamp ring (AXI4 manager) | UVM VIP | `Timer_WDT-UVM-VIP.zip` | 43KB |

---

## SoC Bench Libraries

Models a SoC testbench uses next to the protocol VIPs, kept as source under
`soc/` (not zipped, not part of the per-VIP gates):

| Library | Content |
|---|---|
| [`soc/dram_timing`](soc/dram_timing/README.md) | DRAM channel timing for memory slaves, chosen by preset name (`ddr4-2400`, `ddr4-3200`, `lpddr4-3200`, `lpddr4x-4266`, `lpddr5-6400`, `lpddr5x-8533`), the name socgen's `memories[].timing` carries |
| [`soc/device_models`](soc/device_models/README.md) | Device-side models a SoC bench hangs on IP pins without a UVM agent: `csi2_tx_model` (camera sensor into CSI_2_top), `gmii_phy_model` (link partner with echo for Ethernet_top), `i2s_codec_model` (I2S clock master for I2S_top), each self-tested against the open-ip-portfolio RTL |

## Repository Structure

```
open-vip-portfolio/
|-- LICENSE
|-- README.md
|-- vip_individual_portfolio.csv   # machine-readable index (164 entries)
|-- smoke_report.csv               # full open-toolchain L1b smoke results
|-- vips/                          # 164 individual VIP zip files
|-- .github/workflows/             # CI validation
|-- docs/                          # CONTRIBUTING and guides
```

---

## Quick Start

### 1. Download a VIP

```bash
git clone https://github.com/tonythetiger168/open-vip-portfolio.git
cd open-vip-portfolio
unzip vips/UART-VIP.zip -d ./my_project/
```

### 2. Run the open-toolchain smoke gate

```bash
bash smoke/run_smoke.sh UART-VIP   # or: python3 smoke/smoke_run.py --smoke-all
```

---

## Quality Gates

- **L1a elaboration**: `python3 tools/elab_scan.py vips/<VIP>` (pyslang + UVM 1.2)
- **L1b smoke**: `bash smoke/run_smoke.sh <VIP>` (iverilog/verilator; full report in `smoke_report.csv`)
- **IP cross-check**: `python3 tools/run_ip_crosscheck.py --ip-dir ../open-ip-portfolio` checks the open-ip-portfolio CSI-2, Ethernet, HDMI, Crypto, UART, SPI, I2C, GPIO, PWM, I2S, SD, eMMC, USB, DDR4_Lite and LPDDR5X_Lite RTL against public vectors, spec-derived references and independent protocol models (see `ipcheck/README.md`)

---

## License

All VIP source files in this repository are licensed under the **Apache License 2.0**. See [LICENSE](LICENSE).

---

## Contributing

Contributions are welcome! Please see [docs/CONTRIBUTING.md](docs/CONTRIBUTING.md).

---

*Release v1.10.0 -- generated from vip_individual_portfolio.csv*

