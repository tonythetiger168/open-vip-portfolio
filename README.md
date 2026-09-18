# Open VIP Portfolio

A comprehensive, open-source collection of **87 standalone protocol VIP (Verification IP) testbenches** in SystemVerilog / UVM-1.2 for SoC/ASIC verification.

[![License: Apache 2.0](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](LICENSE)
[![VIP Count](https://img.shields.io/badge/VIPs-87-brightgreen.svg)](vip_individual_portfolio.csv)

---

## Overview

This repository is a modular, per-protocol VIP library covering the major interface standards used in modern semiconductor design. Each VIP ships as a fully expanded source tree under `vips/<PROTOCOL>-VIP/` — no zip files, no code generation steps — ready to integrate into your verification flow.

All source files are licensed under the [Apache License 2.0](LICENSE).

## What's in each VIP

Every one of the 87 VIPs contains a complete UVM-1.2 testbench:

| Component | Description |
|-----------|-------------|
| Driver / Monitor / Sequencer | Active UVM agent implementing the protocol's signaling |
| Scoreboard | End-to-end checker with expected/observed analysis imp ports |
| Functional DUT model | Pure-RTL behavioral model of the protocol target |
| L1–L4 tiered SVA checkers | Layered SystemVerilog assertion compliance checkers |
| Functional coverage | ≥ 3 covergroups with crosses |
| Directed sequences | ≥ 6 directed sequence library entries |
| `README.md` | Protocol overview, architecture map, usage |
| `scripts/` | `Makefile` + `coverage.mk` + `cov_check.py` + `coverage_regression.sh` — coverage-driven regression with `COV_GOAL=100`, supporting VCS / Xcelium / Questa |

## Repository layout

```
.
├── vips/                        # 87 VIP source trees (vips/<PROTOCOL>-VIP/)
├── tools/
│   └── elab_scan.py             # pyslang 11 elaboration gate (L1a)
├── smoke/                       # Icarus Verilog DUT smoke harness (L1b)
│   ├── flatten.py               #   interface-port flattener
│   ├── smoke_run.py             #   tb generator + compile/run/classify
│   ├── run_smoke.sh             #   entry script
│   └── README.md
├── docs/
│   ├── CONTRIBUTING.md          # contribution guide
│   ├── ACCEPTANCE.md            # user acceptance guide (L1/L2/L3)
│   ├── CI_README.md             # CI integration notes
│   ├── reachability_report.csv  # covergroup reachability audit (507 groups)
│   └── fix_round2.csv           # round-2 fix log
├── .github/workflows/vip_regression.yml  # GitHub Actions: L1 gate
├── Jenkinsfile                  # Jenkins declarative pipeline (same flow)
└── vip_individual_portfolio.csv # machine-readable index of all 87 VIPs
```

## Verification status (v1.7.4)

| Gate | Tooling | Result |
|------|---------|--------|
| L1a elaboration gate | pyslang 11 + Accellera uvm-core, full parse + elaborate | **87/87 `ELAB_ERRORS=0`** |
| L1b DUT smoke test | Icarus Verilog 11 | **26 PASS / 0 FAIL / 61 SKIP** (SKIPs are Icarus tool limitations, not failures) |
| Covergroup reachability audit | static analysis | **507/507 covergroups clean** |

## Quick start

### Open-source toolchain (no commercial license needed)

Requires Icarus Verilog 11, pyslang 11, and Accellera uvm-core:

```bash
git clone https://github.com/tonythetiger168/open-vip-portfolio.git
cd open-vip-portfolio

# 1. Tool setup
sudo apt-get install -y iverilog
python3 -m pip install "pyslang>=11,<12"
git clone --depth 1 https://github.com/accellera-official/uvm-core.git
export UVM_CORE=$PWD/uvm-core/src

# 2. L1a — elaboration gate on a single VIP (expected output: ELAB_ERRORS=0)
python3 tools/elab_scan.py vips/AHB-VIP

# 3. L1b — iverilog DUT smoke test (expected: SMOKE_PASS AHB-VIP)
bash smoke/run_smoke.sh vips/AHB-VIP
bash smoke/run_smoke.sh            # all 87 VIPs
```

The full acceptance flow (environment checks, batch scripts, FAQ) is documented in [docs/ACCEPTANCE.md](docs/ACCEPTANCE.md).

### Commercial toolchain (coverage-driven regression)

Requires one of VCS / Xcelium / Questa with UVM-1.2:

```bash
cd vips/AHB-VIP/scripts
SIMULATOR=vcs bash coverage_regression.sh     # or SIMULATOR=xcelium / questa
```

Each VIP's regression builds with coverage instrumentation, runs its directed
test list, and enforces the acceptance gate `COV_GOAL=100` (line / FSM /
toggle / assertion coverage) via `cov_check.py`.

## Protocol catalog

All 87 VIPs, grouped by category (from [`vip_individual_portfolio.csv`](vip_individual_portfolio.csv)):

| Category | Protocol | Directory |
|----------|----------|-----------|
| Interconnect | CXL | [`vips/CXL-VIP/`](vips/CXL-VIP/) |
| Interconnect | PCIe | [`vips/PCIe-VIP/`](vips/PCIe-VIP/) |
| Interconnect | UCIe | [`vips/UCIe-VIP/`](vips/UCIe-VIP/) |
| Interconnect | UALink | [`vips/UALink-VIP/`](vips/UALink-VIP/) |
| Networking | Ethernet | [`vips/Ethernet-VIP/`](vips/Ethernet-VIP/) |
| Networking | FC | [`vips/FC-VIP/`](vips/FC-VIP/) |
| Networking | UEC | [`vips/UEC-VIP/`](vips/UEC-VIP/) |
| USB | USB | [`vips/USB-VIP/`](vips/USB-VIP/) |
| USB | USB-PD | [`vips/USB_PD-VIP/`](vips/USB_PD-VIP/) |
| USB | USB2 | [`vips/USB2-VIP/`](vips/USB2-VIP/) |
| USB | USB3 | [`vips/USB3-VIP/`](vips/USB3-VIP/) |
| USB | USB4 | [`vips/USB4-VIP/`](vips/USB4-VIP/) |
| USB | eUSB2 | [`vips/eUSB2-VIP/`](vips/eUSB2-VIP/) |
| AMBA | AHB | [`vips/AHB-VIP/`](vips/AHB-VIP/) |
| AMBA | APB | [`vips/APB-VIP/`](vips/APB-VIP/) |
| AMBA | AXI | [`vips/AXI-VIP/`](vips/AXI-VIP/) |
| Memory | DDR | [`vips/DDR-VIP/`](vips/DDR-VIP/) |
| Memory | DDR5 | [`vips/ddr5-VIP/`](vips/ddr5-VIP/) |
| Memory | DDR6 | [`vips/ddr6-VIP/`](vips/ddr6-VIP/) |
| Memory | HBM | [`vips/HBM-VIP/`](vips/HBM-VIP/) |
| Memory | LPDDR | [`vips/LPDDR-VIP/`](vips/LPDDR-VIP/) |
| Memory | LPDDR5 | [`vips/lpddr5-VIP/`](vips/lpddr5-VIP/) |
| Memory | LPDDR5X | [`vips/lpddr5x-VIP/`](vips/lpddr5x-VIP/) |
| Memory | LPDDR6 | [`vips/lpddr6-VIP/`](vips/lpddr6-VIP/) |
| Memory | ONFI | [`vips/ONFI-VIP/`](vips/ONFI-VIP/) |
| Memory | SD | [`vips/SD-VIP/`](vips/SD-VIP/) |
| Memory | UFS | [`vips/UFS-VIP/`](vips/UFS-VIP/) |
| Memory | UniPro-Mem | [`vips/UniPro_Mem-VIP/`](vips/UniPro_Mem-VIP/) |
| Memory | eMMC | [`vips/eMMC-VIP/`](vips/eMMC-VIP/) |
| Memory | DDR7 | [`vips/ddr7-VIP/`](vips/ddr7-VIP/) |
| Memory | GDDR5 | [`vips/gddr5-VIP/`](vips/gddr5-VIP/) |
| Memory | GDDR6 | [`vips/gddr6-VIP/`](vips/gddr6-VIP/) |
| Memory | GDDR7 | [`vips/gddr7-VIP/`](vips/gddr7-VIP/) |
| Memory | HBM2 | [`vips/hbm2-VIP/`](vips/hbm2-VIP/) |
| Memory | HBM3 | [`vips/hbm3-VIP/`](vips/hbm3-VIP/) |
| Memory | HBM3E | [`vips/hbm3e-VIP/`](vips/hbm3e-VIP/) |
| Memory | HBM4 | [`vips/hbm4-VIP/`](vips/hbm4-VIP/) |
| Memory | HBM5 | [`vips/HBM5-VIP/`](vips/HBM5-VIP/) |
| Memory | LPDDR7 | [`vips/lpddr7-VIP/`](vips/lpddr7-VIP/) |
| MIPI | C-PHY | [`vips/C_PHY-VIP/`](vips/C_PHY-VIP/) |
| MIPI | CSE | [`vips/CSE-VIP/`](vips/CSE-VIP/) |
| MIPI | CSI-2 | [`vips/CSI_2-VIP/`](vips/CSI_2-VIP/) |
| MIPI | D-PHY | [`vips/D_PHY-VIP/`](vips/D_PHY-VIP/) |
| MIPI | DSI | [`vips/DSI-VIP/`](vips/DSI-VIP/) |
| MIPI | DigRF | [`vips/DigRF-VIP/`](vips/DigRF-VIP/) |
| MIPI | HSI | [`vips/HSI-VIP/`](vips/HSI-VIP/) |
| MIPI | M-PHY | [`vips/M_PHY-VIP/`](vips/M_PHY-VIP/) |
| MIPI | UniPro | [`vips/UniPro-VIP/`](vips/UniPro-VIP/) |
| Storage/Debug | Bluetooth5 | [`vips/Bluetooth5-VIP/`](vips/Bluetooth5-VIP/) |
| Storage/Debug | DisplayPort2 | [`vips/DisplayPort2-VIP/`](vips/DisplayPort2-VIP/) |
| Storage/Debug | JTAG | [`vips/JTAG-VIP/`](vips/JTAG-VIP/) |
| Storage/Debug | NVMe | [`vips/NVMe-VIP/`](vips/NVMe-VIP/) |
| Storage/Debug | SATA | [`vips/SATA-VIP/`](vips/SATA-VIP/) |
| Automotive | CAN | [`vips/CAN-VIP/`](vips/CAN-VIP/) |
| Automotive | Ethernet-AVB-TSN | [`vips/Ethernet_AVB_TSN-VIP/`](vips/Ethernet_AVB_TSN-VIP/) |
| Automotive | FlexRay | [`vips/FlexRay-VIP/`](vips/FlexRay-VIP/) |
| Automotive | LIN | [`vips/LIN-VIP/`](vips/LIN-VIP/) |
| Serial | I2C | [`vips/I2C-VIP/`](vips/I2C-VIP/) |
| Audio | I2S Audio | [`vips/I2S-VIP/`](vips/I2S-VIP/) |
| Serial | SPI | [`vips/SPI-VIP/`](vips/SPI-VIP/) |
| Serial | UART | [`vips/UART-VIP/`](vips/UART-VIP/) |
| Debug | ARM Serial Wire Debug | [`vips/SWD-VIP/`](vips/SWD-VIP/) |
| Power | AVSBus (Adaptive Voltage Scaling) | [`vips/AVSBus-VIP/`](vips/AVSBus-VIP/) |
| Power | ARM Q-Channel Low Power Interface | [`vips/LPI-VIP/`](vips/LPI-VIP/) |
| Video | HDMI 2.1 | [`vips/HDMI-VIP/`](vips/HDMI-VIP/) |
| Security | HDCP 2.3 Content Protection | [`vips/HDCP-VIP/`](vips/HDCP-VIP/) |
| MIPI | MIPI I3C | [`vips/I3C-VIP/`](vips/I3C-VIP/) |
| MIPI | MIPI RFFE | [`vips/RFFE-VIP/`](vips/RFFE-VIP/) |
| MIPI | MIPI SLIMbus | [`vips/SLIMbus-VIP/`](vips/SLIMbus-VIP/) |
| MIPI | MIPI SoundWire | [`vips/SoundWire-VIP/`](vips/SoundWire-VIP/) |
| MIPI | MIPI SPMI | [`vips/SPMI-VIP/`](vips/SPMI-VIP/) |
| MIPI | MIPI DBI (Display Bus Interface) | [`vips/DBI-VIP/`](vips/DBI-VIP/) |
| MIPI | MIPI DPI (Display Pixel Interface) | [`vips/DPI-VIP/`](vips/DPI-VIP/) |
| Interconnect | CCIX Cache Coherent Interconnect | [`vips/CCIX-VIP/`](vips/CCIX-VIP/) |
| Interconnect | CXS CCIX Stream Interface | [`vips/CXS-VIP/`](vips/CXS-VIP/) |
| Interconnect | OCP-IP Open Core Protocol | [`vips/OCP-VIP/`](vips/OCP-VIP/) |
| Interconnect | TileLink (TL-UL/TL-C) | [`vips/TileLink-VIP/`](vips/TileLink-VIP/) |
| Interconnect | ARM Local Translation Interface | [`vips/LTI-VIP/`](vips/LTI-VIP/) |
| Memory | DFI 5.0 (MC-PHY Interface) | [`vips/DFI-VIP/`](vips/DFI-VIP/) |
| Telecom | CPRI v8.0 (eCPRI over CPR) | [`vips/CPRI-VIP/`](vips/CPRI-VIP/) |
| Telecom | eCPRI over Ethernet | [`vips/eCPRI-VIP/`](vips/eCPRI-VIP/) |
| Networking | Interlaken v1.2 | [`vips/Interlaken-VIP/`](vips/Interlaken-VIP/) |
| SerDes | JESD204C | [`vips/JESD204-VIP/`](vips/JESD204-VIP/) |
| Storage | SAS-4 (Serial Attached SCSI) | [`vips/SAS-VIP/`](vips/SAS-VIP/) |
| Storage | Toggle Mode NAND | [`vips/ToggleNAND-VIP/`](vips/ToggleNAND-VIP/) |
| Security | Crypto / Security Engine | [`vips/Security-VIP/`](vips/Security-VIP/) |
| USB | USB Type-C Port Controller | [`vips/TypeC-VIP/`](vips/TypeC-VIP/) |

## Contributing

Contributions are welcome! Please read [docs/CONTRIBUTING.md](docs/CONTRIBUTING.md) for the development workflow, coding conventions, and the regression requirements for new or updated VIPs.

## License

This project is licensed under the [Apache License 2.0](LICENSE). See [NOTICE](NOTICE) for third-party attribution (Accellera uvm-core is used as a verification dependency but is not distributed with this repository).
