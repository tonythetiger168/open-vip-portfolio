# Open VIP Portfolio

> A comprehensive, open-source collection of **132 individual protocol VIP (Verification IP) testbenches** for SystemVerilog/UVM-based SoC/ASIC verification, plus synthesizable RTL IP reference designs.

[![License](https://img.shields.io/badge/License-Apache%%202.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)
[![VIP Count](https://img.shields.io/badge/VIPs-132-brightgreen.svg)]()
[![Protocols](https://img.shields.io/badge/Protocols-117-orange.svg)]()

---

## Overview

This repository provides a **modular, per-protocol verification IP library** covering major interface standards used in modern semiconductor design. Each entry is packaged as a standalone zip file.

- **110 UVM VIPs** -- complete UVM testbench environments (agent, sequences, scoreboard, coverage, SVA checks)
- **22 RTL IPs** -- synthesizable reference RTL with directed testbenches
- **117 distinct protocols** across 20 families

All source files are licensed under **Apache License 2.0**.

---

## Protocol Coverage

### AMBA (11)

| Protocol | Type | File | Size |
|----------|------|------|------|
| ACE | RTL IP | `ACE-VIP.zip` | 13KB |
| ACE-Lite | RTL IP | `ACE_Lite-VIP.zip` | 11KB |
| ACE-Lite | UVM VIP | `ACE_Lite-UVM-VIP.zip` | 24KB |
| AHB | UVM VIP | `AHB-VIP.zip` | 35KB |
| APB | UVM VIP | `APB-VIP.zip` | 33KB |
| AXI | UVM VIP | `AXI-VIP.zip` | 35KB |
| AXI-Stream | RTL IP | `AXI_Stream-VIP.zip` | 7KB |
| AXI4 | RTL IP | `AXI4-VIP.zip` | 13KB |
| AXI4-Lite | RTL IP | `AXI4_Lite-VIP.zip` | 10KB |
| CHI | RTL IP | `CHI-VIP.zip` | 8KB |
| CHI | UVM VIP | `CHI-UVM-VIP.zip` | 24KB |

### Aerospace (1)

| Protocol | Type | File | Size |
|----------|------|------|------|
| MIL-STD-1553 | UVM VIP | `MIL_STD_1553-VIP.zip` | 24KB |

### Audio (1)

| Protocol | Type | File | Size |
|----------|------|------|------|
| I2S Audio | UVM VIP | `I2S-VIP.zip` | 29KB |

### Automotive (6)

| Protocol | Type | File | Size |
|----------|------|------|------|
| CAN | UVM VIP | `CAN-VIP.zip` | 42KB |
| CAN-FD | UVM VIP | `CAN_FD-UVM-VIP.zip` | 23KB |
| Ethernet-AVB-TSN | UVM VIP | `Ethernet_AVB_TSN-VIP.zip` | 66KB |
| FlexRay | UVM VIP | `FlexRay-VIP.zip` | 38KB |
| LIN | UVM VIP | `LIN-VIP.zip` | 37KB |
| SENT | UVM VIP | `SENT-VIP.zip` | 23KB |

### Debug (5)

| Protocol | Type | File | Size |
|----------|------|------|------|
| ARM Serial Wire Debug | UVM VIP | `SWD-VIP.zip` | 31KB |
| ATB | RTL IP | `ATB-VIP.zip` | 7KB |
| ATB | UVM VIP | `ATB-UVM-VIP.zip` | 23KB |
| WTB | RTL IP | `WTB-VIP.zip` | 14KB |
| WTB | UVM VIP | `WTB-UVM-VIP.zip` | 23KB |

### Industrial (2)

| Protocol | Type | File | Size |
|----------|------|------|------|
| EtherCAT | UVM VIP | `EtherCAT-VIP.zip` | 24KB |
| IO-Link | UVM VIP | `IO_Link-VIP.zip` | 24KB |

### Interconnect (16)

| Protocol | Type | File | Size |
|----------|------|------|------|
| ARM Local Translation Interface | UVM VIP | `LTI-VIP.zip` | 28KB |
| Avalon-MM | RTL IP | `Avalon_MM-VIP.zip` | 10KB |
| Avalon-MM | UVM VIP | `Avalon_MM-UVM-VIP.zip` | 24KB |
| Avalon-ST | RTL IP | `Avalon_ST-VIP.zip` | 7KB |
| Avalon-ST | UVM VIP | `Avalon_ST-UVM-VIP.zip` | 24KB |
| CCIX Cache Coherent Interconnect | UVM VIP | `CCIX-VIP.zip` | 28KB |
| CXL | UVM VIP | `CXL-VIP.zip` | 40KB |
| CXS CCIX Stream Interface | UVM VIP | `CXS-VIP.zip` | 28KB |
| OCP-IP Open Core Protocol | UVM VIP | `OCP-VIP.zip` | 28KB |
| PCIe | UVM VIP | `PCIe-VIP.zip` | 41KB |
| RapidIO | UVM VIP | `RapidIO-VIP.zip` | 23KB |
| TileLink (TL-UL/TL-C) | UVM VIP | `TileLink-VIP.zip` | 29KB |
| UALink | UVM VIP | `UALink-VIP.zip` | 22KB |
| UCIe | UVM VIP | `UCIe-VIP.zip` | 22KB |
| Wishbone | RTL IP | `Wishbone-VIP.zip` | 10KB |
| Wishbone | UVM VIP | `Wishbone-UVM-VIP.zip` | 24KB |

### MIPI (16)

| Protocol | Type | File | Size |
|----------|------|------|------|
| C-PHY | UVM VIP | `C_PHY-VIP.zip` | 36KB |
| CSE | UVM VIP | `CSE-VIP.zip` | 36KB |
| CSI-2 | UVM VIP | `CSI_2-VIP.zip` | 36KB |
| D-PHY | UVM VIP | `D_PHY-VIP.zip` | 36KB |
| DSI | UVM VIP | `DSI-VIP.zip` | 36KB |
| DigRF | UVM VIP | `DigRF-VIP.zip` | 33KB |
| HSI | UVM VIP | `HSI-VIP.zip` | 34KB |
| M-PHY | UVM VIP | `M_PHY-VIP.zip` | 36KB |
| MIPI DBI (Display Bus Interface) | UVM VIP | `DBI-VIP.zip` | 28KB |
| MIPI DPI (Display Pixel Interface) | UVM VIP | `DPI-VIP.zip` | 27KB |
| MIPI I3C | UVM VIP | `I3C-VIP.zip` | 35KB |
| MIPI RFFE | UVM VIP | `RFFE-VIP.zip` | 30KB |
| MIPI SLIMbus | UVM VIP | `SLIMbus-VIP.zip` | 31KB |
| MIPI SPMI | UVM VIP | `SPMI-VIP.zip` | 30KB |
| MIPI SoundWire | UVM VIP | `SoundWire-VIP.zip` | 32KB |
| UniPro | UVM VIP | `UniPro-VIP.zip` | 36KB |

### Memory (26)

| Protocol | Type | File | Size |
|----------|------|------|------|
| DDR | UVM VIP | `DDR-VIP.zip` | 29KB |
| DDR4 | RTL IP | `DDR4-VIP.zip` | 11KB |
| DDR5 | UVM VIP | `DDR5-VIP.zip` | 22KB |
| DDR6 | UVM VIP | `ddr6-VIP.zip` | 27KB |
| DDR7 | UVM VIP | `ddr7-VIP.zip` | 27KB |
| DFI 5.0 (MC-PHY Interface) | UVM VIP | `DFI-VIP.zip` | 32KB |
| GDDR5 | UVM VIP | `gddr5-VIP.zip` | 29KB |
| GDDR6 | UVM VIP | `gddr6-VIP.zip` | 30KB |
| GDDR7 | UVM VIP | `gddr7-VIP.zip` | 30KB |
| HBM | UVM VIP | `HBM-VIP.zip` | 29KB |
| HBM2 | UVM VIP | `hbm2-VIP.zip` | 29KB |
| HBM3 | UVM VIP | `hbm3-VIP.zip` | 29KB |
| HBM3E | UVM VIP | `HBM3E-VIP.zip` | 22KB |
| HBM4 | UVM VIP | `hbm4-VIP.zip` | 30KB |
| HBM5 | UVM VIP | `HBM5-VIP.zip` | 27KB |
| LPDDR | UVM VIP | `LPDDR-VIP.zip` | 29KB |
| LPDDR4 | RTL IP | `LPDDR4-VIP.zip` | 11KB |
| LPDDR5 | UVM VIP | `lpddr5-VIP.zip` | 30KB |
| LPDDR5X | UVM VIP | `lpddr5x-VIP.zip` | 32KB |
| LPDDR6 | UVM VIP | `LPDDR6-VIP.zip` | 22KB |
| LPDDR7 | UVM VIP | `lpddr7-VIP.zip` | 32KB |
| ONFI | UVM VIP | `ONFI-VIP.zip` | 53KB |
| SD | UVM VIP | `SD-VIP.zip` | 44KB |
| UFS | UVM VIP | `UFS-VIP.zip` | 35KB |
| UniPro-Mem | UVM VIP | `UniPro_Mem-VIP.zip` | 39KB |
| eMMC | UVM VIP | `eMMC-VIP.zip` | 41KB |

### Networking (14)

| Protocol | Type | File | Size |
|----------|------|------|------|
| 800G Ethernet | UVM VIP | `ETH800G-VIP.zip` | 23KB |
| Ethernet | UVM VIP | `Ethernet-VIP.zip` | 51KB |
| FC | UVM VIP | `FC-VIP.zip` | 48KB |
| GMII | RTL IP | `GMII-VIP.zip` | 7KB |
| GMII | UVM VIP | `GMII-UVM-VIP.zip` | 23KB |
| IEEE 1588 PTP | UVM VIP | `PTP-VIP.zip` | 23KB |
| Interlaken v1.2 | UVM VIP | `Interlaken-VIP.zip` | 30KB |
| MDIO | RTL IP | `MDIO-VIP.zip` | 8KB |
| MDIO | UVM VIP | `MDIO-UVM-VIP.zip` | 23KB |
| RGMII | RTL IP | `RGMII-VIP.zip` | 8KB |
| RGMII | UVM VIP | `RGMII-UVM-VIP.zip` | 23KB |
| UEC | UVM VIP | `UEC-VIP.zip` | 22KB |
| XGMII | RTL IP | `XGMII-VIP.zip` | 8KB |
| XGMII | UVM VIP | `XGMII-UVM-VIP.zip` | 23KB |

### Peripherals (6)

| Protocol | Type | File | Size |
|----------|------|------|------|
| 1-Wire | RTL IP | `OneWire-VIP.zip` | 8KB |
| 1-Wire | UVM VIP | `OneWire-UVM-VIP.zip` | 23KB |
| GPIO | RTL IP | `GPIO-VIP.zip` | 6KB |
| GPIO | UVM VIP | `GPIO-UVM-VIP.zip` | 23KB |
| PWM | RTL IP | `PWM-VIP.zip` | 6KB |
| PWM | UVM VIP | `PWM-UVM-VIP.zip` | 23KB |

### Power (2)

| Protocol | Type | File | Size |
|----------|------|------|------|
| ARM Q-Channel Low Power Interface | UVM VIP | `LPI-VIP.zip` | 29KB |
| AVSBus (Adaptive Voltage Scaling) | UVM VIP | `AVSBus-VIP.zip` | 31KB |

### Security (2)

| Protocol | Type | File | Size |
|----------|------|------|------|
| Crypto / Security Engine | UVM VIP | `Security-VIP.zip` | 30KB |
| HDCP 2.3 Content Protection | UVM VIP | `HDCP-VIP.zip` | 32KB |

### SerDes (1)

| Protocol | Type | File | Size |
|----------|------|------|------|
| JESD204C | UVM VIP | `JESD204-VIP.zip` | 31KB |

### Serial (4)

| Protocol | Type | File | Size |
|----------|------|------|------|
| I2C | UVM VIP | `I2C-VIP.zip` | 29KB |
| QSPI | RTL IP | `QSPI-VIP.zip` | 8KB |
| SPI | UVM VIP | `SPI-VIP.zip` | 31KB |
| UART | UVM VIP | `UART-VIP.zip` | 31KB |

### Storage (4)

| Protocol | Type | File | Size |
|----------|------|------|------|
| SAS-4 (Serial Attached SCSI) | UVM VIP | `SAS-VIP.zip` | 34KB |
| SDIO | RTL IP | `SDIO-VIP.zip` | 15KB |
| SDIO | UVM VIP | `SDIO-UVM-VIP.zip` | 23KB |
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
| USB | UVM VIP | `USB-VIP.zip` | 63KB |
| USB Type-C Port Controller | UVM VIP | `TypeC-VIP.zip` | 31KB |
| USB-PD | UVM VIP | `USB_PD-VIP.zip` | 61KB |
| USB2 | UVM VIP | `USB2-VIP.zip` | 64KB |
| USB3 | UVM VIP | `USB3-VIP.zip` | 61KB |
| USB4 | UVM VIP | `USB4-VIP.zip` | 61KB |
| eUSB2 | UVM VIP | `eUSB2-VIP.zip` | 61KB |

### Video (1)

| Protocol | Type | File | Size |
|----------|------|------|------|
| HDMI 2.1 | UVM VIP | `HDMI-VIP.zip` | 31KB |

---

## Repository Structure

```
open-vip-portfolio/
|-- LICENSE
|-- README.md
|-- vip_individual_portfolio.csv   # machine-readable index (132 entries)
|-- smoke_report.csv               # full open-toolchain L1b smoke results
|-- vips/                          # 132 individual VIP/IP zip files
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

---

## License

All VIP source files in this repository are licensed under the **Apache License 2.0**. See [LICENSE](LICENSE).

---

## Contributing

Contributions are welcome! Please see [docs/CONTRIBUTING.md](docs/CONTRIBUTING.md).

---

*Release v1.8.0 -- generated from vip_individual_portfolio.csv*
