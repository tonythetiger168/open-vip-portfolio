# CAN — CAN 2.0 / CAN FD / CAN TT UVM VIP

Open-source UVM verification IP for **CAN** (Controller Area Network, automotive serial bus).

## Protocol Overview

- **Frame structure:** SOF → arbitration (11/29-bit ID, RTR, IDE) → control (FDF/BRS/ESI, DLC) → data (0-8 bytes) → CRC-15 → ACK → EOF + IFS
- **Bit timing:** 8 clock cycles per bit (abstract model), bit stuffing after 5 consecutive equal bits
- **Arbitration concept:** dominant (0) wins; ID 0x000 = highest priority (covered by `can_arbitration_sequence`)
- **Error handling:** stuff/CRC/form/ack error injection, active error flag (6 dominant bits), bus-off tracking signals

## Contents

| Path | Description |
|------|-------------|
| `common/common_pkg.sv` | shared base classes (`protocol_checker_base`, `coverage_collector_base`) |
| `can/can_if.sv` | protocol interface + clocking blocks |
| `can/can_pkg.sv` + `*.svh` | UVM agent (driver / monitor / sequencer / coverage / checker) |
| `can/can_crc.svh` | CRC-15 (0x4599) helper function |
| `can/sva/can_compliance_checker.sv` | SVA compliance checker module (L1=4, L2=6, L3=4, L4=5) |
| `can/vip/can/` | protocol / timing / error / data-integrity checkers |
| `env/can_env.sv` | environment + end-to-end scoreboard |
| `tests/can_tests.sv` | base / random / can_2_0 / error_inject / regression tests |
| `tb/top_tb.sv` | testbench top |
| `tb/can_node_model.sv` | functional CAN node DUT (pure RTL) |
| `scripts/` | Makefile + coverage-driven regression (100% goal) |

## Architecture

```
can_tests -> can_env -> can_agent (sequencer -> driver -> monitor) -> scoreboard
                |                                        ^
                v                                        |
        can_if (can_rx) -> CAN node DUT (CRC check/echo) -+ (can_tx)
```

The VIP driver serializes frames onto `can_rx`; the DUT node decodes, verifies
CRC-15, and echoes the frame on `can_tx` (or emits an active error flag); the
monitor decodes `can_tx` bit-by-bit and the scoreboard compares expected vs
observed frames (n_matches / n_mismatches, UVM_ERROR on mismatch).

## Sequence Library
| Sequence | Purpose |
|----------|---------|
| `can_random_sequence` | constrained-random (normal) |
| `can_2_0_sequence` / `can_fd_sequence` / `can_tt_sequence` | per-variant traffic |
| `can_back_to_back_sequence` | minimal inter-frame space |
| `can_remote_sequence` | RTR remote frames |
| `can_arbitration_sequence` | ID extremes (corner case) |
| `can_error_inject_sequence` | CRC error injection |
| `can_stress_sequence` | dense traffic with 10% errors |
| `can_reset_sequence` | frame right after reset |
| `can_regression_sequence` | weighted mix |

## SVA (L1-L4)
- **L1 (4):** SOF dominant, std/ext ID ranges, DLC range
- **L2 (6):** CRC ok, ACK field, FDF/BRS/ESI legality, bit time, bus-off
- **L3 (4):** TT trigger, error frame counters, bus-off recovery, overload
- **L4 (5):** dominant drive only when enabled, SOF after IFS, bit-stuffing (6 dominant = error flag only), error-flag recovery, CRC delimiter recessive

## Functional Coverage
- `can_type_cg`: CAN type x frame type / DLC, IDE x error (cross)
- `can_error_cg`: error injection kinds (cross)
- `can_fsm_cg`: frame-type + CAN-type transition sequences (cross)
- `can_data_cg`: payload corners (0x00/0xFF/0xAA/0x55) x DLC (cross)

## Quick start
```bash
cd scripts
make all TEST=base_test          # single run (VCS default)
./coverage_regression.sh         # full regression + 100% coverage gate
SIMULATOR=questa ./coverage_regression.sh
```

License: Apache-2.0
