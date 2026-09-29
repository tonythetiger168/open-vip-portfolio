# Open VIP Portfolio

> A comprehensive, open-source collection of **131 individual protocol VIP (Verification IP) testbenches** for SystemVerilog/UVM-based SoC/ASIC verification, plus synthesizable RTL IP reference designs.

[![License](https://img.shields.io/badge/License-Apache%%202.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)
[![VIP Count](https://img.shields.io/badge/VIPs-131-brightgreen.svg)]()
[![Protocols](https://img.shields.io/badge/Protocols-116-orange.svg)]()

---

## Overview

This repository provides a **modular, per-protocol verification IP library** covering major interface standards used in modern semiconductor design. Each entry is packaged as a standalone zip file.

- **109 UVM VIPs** -- complete UVM testbench environments (agent, sequences, scoreboard, coverage, SVA checks)
- **22 RTL IPs** -- synthesizable reference RTL with directed testbenches
- **116 distinct protocols** across 20 families

All source files are licensed under **Apache License 2.0**.

---

## Protocol Coverage

### AMBA (11)

| Protocol | Type | File | Size |
|----------|------|------|------|
| ACE | RTL IP | `ACE-VIP.zip` |  |
| ACE-Lite | RTL IP | `ACE_Lite-VIP.zip` |  |
| ACE-Lite | UVM VIP | `ACE_Lite-UVM-VIP.zip` |  |
| AHB | UVM VIP | `AHB-VIP.zip` |  |
| APB | UVM VIP | `APB-VIP.zip` |  |
| AXI | UVM VIP | `AXI-VIP.zip` |  |
| AXI-Stream | RTL IP | `AXI_Stream-VIP.zip` |  |
| AXI4 | RTL IP | `AXI4-VIP.zip` |  |
| AXI4-Lite | RTL IP | `AXI4_Lite-VIP.zip` |  |
| CHI | RTL IP | `CHI-VIP.zip` |  |
| CHI | UVM VIP | `CHI-UVM-VIP.zip` |  |

### Aerospace (1)

| Protocol | Type | File | Size |
|----------|------|------|------|
| MIL-STD-1553 | UVM VIP | `MIL_STD_1553-VIP.zip` |  |

### Audio (1)

| Protocol | Type | File | Size |
|----------|------|------|------|
| I2S Audio | UVM VIP | `I2S-VIP.zip` |  |

### Automotive (6)

| Protocol | Type | File | Size |
|----------|------|------|------|
| CAN | UVM VIP | `CAN-VIP.zip` |  |
| CAN-FD | UVM VIP | `CAN_FD-UVM-VIP.zip` |  |
| Ethernet-AVB-TSN | UVM VIP | `Ethernet_AVB_TSN-VIP.zip` |  |
| FlexRay | UVM VIP | `FlexRay-VIP.zip` |  |
| LIN | UVM VIP | `LIN-VIP.zip` |  |
| SENT | UVM VIP | `SENT-VIP.zip` |  |

### Debug (5)

| Protocol | Type | File | Size |
|----------|------|------|------|
| ARM Serial Wire Debug | UVM VIP | `SWD-VIP.zip` |  |
| ATB | RTL IP | `ATB-VIP.zip` |  |
| ATB | UVM VIP | `ATB-UVM-VIP.zip` |  |
| WTB | RTL IP | `WTB-VIP.zip` |  |
| WTB | UVM VIP | `WTB-UVM-VIP.zip` |  |

### Industrial (2)

| Protocol | Type | File | Size |
|----------|------|------|------|
| EtherCAT | UVM VIP | `EtherCAT-VIP.zip` |  |
| IO-Link | UVM VIP | `IO_Link-VIP.zip` |  |

### Interconnect (16)

| Protocol | Type | File | Size |
|----------|------|------|------|
| ARM Local Translation Interface | UVM VIP | `LTI-VIP.zip` |  |
| Avalon-MM | RTL IP | `Avalon_MM-VIP.zip` |  |
| Avalon-MM | UVM VIP | `Avalon_MM-UVM-VIP.zip` |  |
| Avalon-ST | RTL IP | `Avalon_ST-VIP.zip` |  |
| Avalon-ST | UVM VIP | `Avalon_ST-UVM-VIP.zip` |  |
| CCIX Cache Coherent Interconnect | UVM VIP | `CCIX-VIP.zip` |  |
| CXL | UVM VIP | `CXL-VIP.zip` |  |
| CXS CCIX Stream Interface | UVM VIP | `CXS-VIP.zip` |  |
| OCP-IP Open Core Protocol | UVM VIP | `OCP-VIP.zip` |  |
| PCIe | UVM VIP | `PCIe-VIP.zip` |  |
| RapidIO | UVM VIP | `RapidIO-VIP.zip` |  |
| TileLink (TL-UL/TL-C) | UVM VIP | `TileLink-VIP.zip` |  |
| UALink | UVM VIP | `UALink-VIP.zip` |  |
| UCIe | UVM VIP | `UCIe-VIP.zip` |  |
| Wishbone | RTL IP | `Wishbone-VIP.zip` |  |
| Wishbone | UVM VIP | `Wishbone-UVM-VIP.zip` |  |

### MIPI (16)

| Protocol | Type | File | Size |
|----------|------|------|------|
| C-PHY | UVM VIP | `C_PHY-VIP.zip` |  |
| CSE | UVM VIP | `CSE-VIP.zip` |  |
| CSI-2 | UVM VIP | `CSI_2-VIP.zip` |  |
| D-PHY | UVM VIP | `D_PHY-VIP.zip` |  |
| DSI | UVM VIP | `DSI-VIP.zip` |  |
| DigRF | UVM VIP | `DigRF-VIP.zip` |  |
| HSI | UVM VIP | `HSI-VIP.zip` |  |
| M-PHY | UVM VIP | `M_PHY-VIP.zip` |  |
| MIPI DBI (Display Bus Interface) | UVM VIP | `DBI-VIP.zip` |  |
| MIPI DPI (Display Pixel Interface) | UVM VIP | `DPI-VIP.zip` |  |
| MIPI I3C | UVM VIP | `I3C-VIP.zip` |  |
| MIPI RFFE | UVM VIP | `RFFE-VIP.zip` |  |
| MIPI SLIMbus | UVM VIP | `SLIMbus-VIP.zip` |  |
| MIPI SPMI | UVM VIP | `SPMI-VIP.zip` |  |
| MIPI SoundWire | UVM VIP | `SoundWire-VIP.zip` |  |
| UniPro | UVM VIP | `UniPro-VIP.zip` |  |

### Memory (26)

| Protocol | Type | File | Size |
|----------|------|------|------|
| DDR | UVM VIP | `DDR-VIP.zip` |  |
| DDR4 | RTL IP | `DDR4-VIP.zip` |  |
| DDR5 | UVM VIP | `ddr5-VIP.zip` |  |
| DDR6 | UVM VIP | `ddr6-VIP.zip` |  |
| DDR7 | UVM VIP | `ddr7-VIP.zip` |  |
| DFI 5.0 (MC-PHY Interface) | UVM VIP | `DFI-VIP.zip` |  |
| GDDR5 | UVM VIP | `gddr5-VIP.zip` |  |
| GDDR6 | UVM VIP | `gddr6-VIP.zip` |  |
| GDDR7 | UVM VIP | `gddr7-VIP.zip` |  |
| HBM | UVM VIP | `HBM-VIP.zip` |  |
| HBM2 | UVM VIP | `hbm2-VIP.zip` |  |
| HBM3 | UVM VIP | `hbm3-VIP.zip` |  |
| HBM3E | UVM VIP | `hbm3e-VIP.zip` |  |
| HBM4 | UVM VIP | `hbm4-VIP.zip` |  |
| HBM5 | UVM VIP | `HBM5-VIP.zip` |  |
| LPDDR | UVM VIP | `LPDDR-VIP.zip` |  |
| LPDDR4 | RTL IP | `LPDDR4-VIP.zip` |  |
| LPDDR5 | UVM VIP | `lpddr5-VIP.zip` |  |
| LPDDR5X | UVM VIP | `lpddr5x-VIP.zip` |  |
| LPDDR6 | UVM VIP | `lpddr6-VIP.zip` |  |
| LPDDR7 | UVM VIP | `lpddr7-VIP.zip` |  |
| ONFI | UVM VIP | `ONFI-VIP.zip` |  |
| SD | UVM VIP | `SD-VIP.zip` |  |
| UFS | UVM VIP | `UFS-VIP.zip` |  |
| UniPro-Mem | UVM VIP | `UniPro_Mem-VIP.zip` |  |
| eMMC | UVM VIP | `eMMC-VIP.zip` |  |

### Networking (13)

| Protocol | Type | File | Size |
|----------|------|------|------|
| Ethernet | UVM VIP | `Ethernet-VIP.zip` |  |
| FC | UVM VIP | `FC-VIP.zip` |  |
| GMII | RTL IP | `GMII-VIP.zip` |  |
| GMII | UVM VIP | `GMII-UVM-VIP.zip` |  |
| IEEE 1588 PTP | UVM VIP | `PTP-VIP.zip` |  |
| Interlaken v1.2 | UVM VIP | `Interlaken-VIP.zip` |  |
| MDIO | RTL IP | `MDIO-VIP.zip` |  |
| MDIO | UVM VIP | `MDIO-UVM-VIP.zip` |  |
| RGMII | RTL IP | `RGMII-VIP.zip` |  |
| RGMII | UVM VIP | `RGMII-UVM-VIP.zip` |  |
| UEC | UVM VIP | `UEC-VIP.zip` |  |
| XGMII | RTL IP | `XGMII-VIP.zip` |  |
| XGMII | UVM VIP | `XGMII-UVM-VIP.zip` |  |

### Peripherals (6)

| Protocol | Type | File | Size |
|----------|------|------|------|
| 1-Wire | RTL IP | `OneWire-VIP.zip` |  |
| 1-Wire | UVM VIP | `OneWire-UVM-VIP.zip` |  |
| GPIO | RTL IP | `GPIO-VIP.zip` |  |
| GPIO | UVM VIP | `GPIO-UVM-VIP.zip` |  |
| PWM | RTL IP | `PWM-VIP.zip` |  |
| PWM | UVM VIP | `PWM-UVM-VIP.zip` |  |

### Power (2)

| Protocol | Type | File | Size |
|----------|------|------|------|
| ARM Q-Channel Low Power Interface | UVM VIP | `LPI-VIP.zip` |  |
| AVSBus (Adaptive Voltage Scaling) | UVM VIP | `AVSBus-VIP.zip` |  |

### Security (2)

| Protocol | Type | File | Size |
|----------|------|------|------|
| Crypto / Security Engine | UVM VIP | `Security-VIP.zip` |  |
| HDCP 2.3 Content Protection | UVM VIP | `HDCP-VIP.zip` |  |

### SerDes (1)

| Protocol | Type | File | Size |
|----------|------|------|------|
| JESD204C | UVM VIP | `JESD204-VIP.zip` |  |

### Serial (4)

| Protocol | Type | File | Size |
|----------|------|------|------|
| I2C | UVM VIP | `I2C-VIP.zip` |  |
| QSPI | RTL IP | `QSPI-VIP.zip` |  |
| SPI | UVM VIP | `SPI-VIP.zip` |  |
| UART | UVM VIP | `UART-VIP.zip` |  |

### Storage (4)

| Protocol | Type | File | Size |
|----------|------|------|------|
| SAS-4 (Serial Attached SCSI) | UVM VIP | `SAS-VIP.zip` |  |
| SDIO | RTL IP | `SDIO-VIP.zip` |  |
| SDIO | UVM VIP | `SDIO-UVM-VIP.zip` |  |
| Toggle Mode NAND | UVM VIP | `ToggleNAND-VIP.zip` |  |

### Storage/Debug (5)

| Protocol | Type | File | Size |
|----------|------|------|------|
| Bluetooth5 | UVM VIP | `Bluetooth5-VIP.zip` |  |
| DisplayPort2 | UVM VIP | `DisplayPort2-VIP.zip` |  |
| JTAG | UVM VIP | `JTAG-VIP.zip` |  |
| NVMe | UVM VIP | `NVMe-VIP.zip` |  |
| SATA | UVM VIP | `SATA-VIP.zip` |  |

### Telecom (2)

| Protocol | Type | File | Size |
|----------|------|------|------|
| CPRI v8.0 (eCPRI over CPR) | UVM VIP | `CPRI-VIP.zip` |  |
| eCPRI over Ethernet | UVM VIP | `eCPRI-VIP.zip` |  |

### USB (7)

| Protocol | Type | File | Size |
|----------|------|------|------|
| USB | UVM VIP | `USB-VIP.zip` |  |
| USB Type-C Port Controller | UVM VIP | `TypeC-VIP.zip` |  |
| USB-PD | UVM VIP | `USB_PD-VIP.zip` |  |
| USB2 | UVM VIP | `USB2-VIP.zip` |  |
| USB3 | UVM VIP | `USB3-VIP.zip` |  |
| USB4 | UVM VIP | `USB4-VIP.zip` |  |
| eUSB2 | UVM VIP | `eUSB2-VIP.zip` |  |

### Video (1)

| Protocol | Type | File | Size |
|----------|------|------|------|
| HDMI 2.1 | UVM VIP | `HDMI-VIP.zip` |  |

---

## Repository Structure

```
open-vip-portfolio/
|-- LICENSE
|-- README.md
|-- vip_individual_portfolio.csv   # machine-readable index (131 entries)
|-- smoke_report.csv               # full open-toolchain L1b smoke results
|-- vips/                          # 131 individual VIP/IP zip files
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

*Release v1.7.5 -- generated from vip_individual_portfolio.csv*
