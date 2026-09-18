// Copyright 2026 VIP Portfolio Contributors
// SPDX-License-Identifier: Apache-2.0
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//     http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.
//
# Multi-Protocol Verification IP (VIP)  ## Overview  Coverage-Driven UVM-based Verification IP supporting:  - **PCIe Gen 5** (32 GT/s, x16) - **PCIe Gen 6** (64 GT/s, x16) - **CXL 2.0** (32 GT/s, x16) - **CXL 3.0** (32 GT/s, x16, PASID) - **UCIe** (16-32 GT/s, x64) - **UALink** (64-224 GT/s, x16)  ## Directory Structure  ``` multi_protocol_vip/ |-- rtl/              # SystemVerilog Interface + Assertions |   |-- mp_vip_if.sv |-- vip/base/       # UVM Base Components |   |-- mp_vip_pkg.sv      # Package: txn, coverage, scoreboard |   |-- mp_sequencer.sv    # UVM Sequencer |   |-- mp_driver.sv       # Protocol-aware Driver |   |-- mp_monitor.sv      # Monitor + Coverage Sampling |   |-- mp_agent.sv        # UVM Agent |-- env/              # Verification Environment |   |-- mp_env.sv          # Multi-protocol env |-- sequences/        # UVM Sequences |   |-- mp_base_sequence.sv |   |-- mp_random_sequence.sv |   |-- mp_regression_sequence.sv |-- tests/            # UVM Tests |   |-- mp_base_test.sv |   |-- mp_random_regression_test.sv |   |-- mp_pcie_gen5_test.sv |   |-- mp_pcie_gen6_test.sv |   |-- mp_cxl_test.sv |-- tb/               # Top-Level Testbench |   |-- top_tb.sv          # DUT stub + interface binding |-- scripts/          # Build & Regression |   |-- Makefile |   |-- regression.sh ```  ## Quick Start  ```bash cd scripts  # Compile + Elaborate + Run make all  # Or step by step make compile make elaborate make run TEST=mp_random_regression_test SEED=12345  # Full regression (25 runs: 5 tests x 5 seeds) make regression  # Parallel regression with coverage merge chmod +x regression.sh ./regression.sh ```  ## Coverage Model  | Covergroup | Description | |------------|-------------| | `cg_txn_type` | Protocol x Transaction Type cross | | `cg_address_map` | Memory range + alignment | | `cg_data_patterns` | Zeros, ones, walking, random | | `cg_latency` | Latency distribution per protocol | | `cg_error_injection` | ECRC/LCRC/Framing/Protocol errors | | `cg_interface_activity` | Handshake + link state cross |  ## EDA Tool Support  | Tool | Vendor | Command | |------|--------|---------| | VCS | Synopsys | `make SIMULATOR=vcs` | | Xcelium | Cadence | `make SIMULATOR=xcelium` | | Questa | Siemens | `make SIMULATOR=questa` |  ## License  Proprietary - For internal use only.
## Deepened Features (v2.0.0)

- **Regenerated compilable sources**: the shipped bodies were minified onto a
  single comment line (effectively dead code); all files were rewritten as
  clean, parse-verified SystemVerilog with identical names and APIs.
- **TLP-level driver**: LTSSM/link-up wait, header + data-beat driving with
  ready backpressure hold, SOP/EOP/BE framing, tag/TC/attr/length_dw fields,
  `drv_ap` expected-transaction broadcast for the scoreboard.
- **Protocol-decoding monitor**: reconstructs PCIe/CXL/UCIe/UALink transactions
  from SOP..EOP waveforms, per-cycle LTSSM FSM coverage sampling.
- **End-to-end scoreboard** (`mp_e2e_scoreboard`): expected (driver) vs
  observed (monitor) comparison with `n_matches`/`n_mismatches`, UVM_ERROR on
  mismatch (analysis imps `_exp`/`_obs`).
- **Functional DUT models in tb/top_tb.sv**: `mp_dut` walks LTSSM
  (RESET->DETECT->POLLING->CONFIG->L0) and models ready/valid flow control;
  `mp_endpoint_mem_model` is an associative-memory endpoint snooping write
  TLP payloads (closed loop driver->DUT->monitor).
- **Directed sequence library (9)**: base, random, regression mix, power
  management (L0s/L1 idle windows), error injection (EP/inject/TD),
  back-to-back, stress (max payload all TCs), corner case (min/max payload,
  boundary address, poison), reset.
- **Functional coverage (7 covergroups)**: cg_txn_type (protocol x type
  cross), cg_address_map (range x align cross), cg_data_patterns,
  cg_latency (latency x protocol cross), cg_error_injection (type x recovery
  cross), cg_link_fsm (LTSSM state + transition sequences),
  cg_interface_activity (handshake x link-state cross, in mp_vip_if).
- **SVA compliance checker** (module form, `rtl/sva/pcie_compliance_checker.sv`):
  L1 basic (4), L2 full protocol (8), L3 advanced (8) preserved;
  **L4 PCIe-specific (5)**: EOP-requires-VALID, SOP only at TLP boundary,
  continuation beat requires in-flight TLP, SOP->EOP within 64 beats,
  no traffic during reset. Tiered coverage report in `final` block.
- **Protocol checker** (`vip/pcie/pcie_protocol_checker.sv`): online rule
  checks (link-down traffic, SOP mid-TLP, EP without VALID, tag recycling).

All 21 .sv/.svh files pass a pyslang syntax parse with 0 errors.

## Quick start

```bash
cd scripts
make all                       # single run (VCS default)
./coverage_regression.sh       # full regression + coverage gate
SIMULATOR=questa ./coverage_regression.sh
```
