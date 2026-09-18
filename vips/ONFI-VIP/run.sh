#!/bin/bash
# Copyright 2026 VIP Portfolio Contributors
# SPDX-License-Identifier: Apache-2.0
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
TESTNAME=${TESTNAME:-memory_coverage_regression_test}
SEED=${SEED:-$RANDOM}
SIMULATOR=${SIMULATOR:-xrun}

echo ========================================
echo   Memory UVM VIP Framework
echo   Test: $TESTNAME
echo   Seed: $SEED
echo   Simulator: $SIMULATOR
echo ========================================

SV_FILES=(
    interfaces/memory_interfaces.sv
    ddr/ddr_pkg.sv lpddr/lpddr_pkg.sv hbm/hbm_pkg.sv
    ufs/ufs_pkg.sv unipro/unipro_pkg.sv emmc/emmc_pkg.sv
    onfi/onfi_pkg.sv sd/sd_pkg.sv
    coverage/memory_coverage_pkg.sv
    env/memory_env_pkg.sv
    env/sva/onfi_compliance_checker.sv
    env/vip/onfi/onfi_protocol_checker.sv
    env/vip/onfi/onfi_timing_checker.sv
    env/vip/onfi/onfi_error_checker.sv
    env/vip/onfi/onfi_data_integrity_checker.sv
    test/memory_test_pkg.sv
    tb_top.sv
)

FLIST=$(IFS=' '; echo ${SV_FILES[*]})

case $SIMULATOR in
    xrun)  xrun -uvm -sv $FLIST +UVM_TESTNAME=$TESTNAME +ntb_random_seed=$SEED -timescale 1ns/1ps -access +rw -l sim.log ;;
    vcs)   vcs -sverilog -ntb_opts uvm $FLIST +UVM_TESTNAME=$TESTNAME +ntb_random_seed=$SEED -timescale=1ns/1ps -l comp.log; ./simv +UVM_TESTNAME=$TESTNAME +ntb_random_seed=$SEED -l sim.log ;;
    vsim)  vlib work; vlog -sv $FLIST; vsim -c tb_top -sv_seed $SEED -do "run -all; quit -f" +UVM_TESTNAME=$TESTNAME -l sim.log ;;
    *)     echo "Unknown simulator: $SIMULATOR"; exit 1 ;;
esac

echo ========================================
echo   Simulation Complete
echo   Test: $TESTNAME
echo ========================================
