#!/usr/bin/env bash
# SPDX-License-Identifier: Apache-2.0
# Build and run the dram_timing_pkg self-test with Verilator 5.
set -euo pipefail
cd "$(dirname "$0")"
rm -rf obj_dir
verilator --binary -Wno-fatal -Wno-lint --top-module dram_timing_tb \
  src/dram_timing_pkg.sv tests/dram_timing_tb.sv -o tb > build.log 2>&1 || { tail -20 build.log; exit 1; }
./obj_dir/tb | tee sim.log
grep -q '^FUNC_PASS' sim.log
