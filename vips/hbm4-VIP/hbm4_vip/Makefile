# HBM4 UVM Testbench Makefile
# SPDX-License-Identifier: Apache-2.0

UVM_HOME ?= $(UVM_HOME)
VCS = vcs -sverilog -ntb_opts uvm-1.2
SIMV = ./simv

SRC = rtl/hbm4_if.sv \
      sequences/hbm4_sequence.sv \
      vip/hbm4/hbm4_protocol_checker.sv \
      vip/hbm4/hbm4_data_integrity_checker.sv \
      vip/hbm4/hbm4_timing_checker.sv \
      vip/hbm4/hbm4_error_checker.sv \
      vip/hbm4/hbm4_driver.sv \
      vip/hbm4/hbm4_monitor.sv \
      vip/hbm4/hbm4_agent.sv \
      vip/hbm4/hbm4_coverage.sv \
      vip/hbm4/hbm4_compliance_checker.sv \
      env/hbm4_env.sv \
      tests/hbm4_test.sv \
      tb/tb_top.sv

comp:
	$(VCS) +incdir+.+$(UVM_HOME)/src $(UVM_HOME)/src/uvm.sv $(SRC)
sim:
	$(SIMV) +UVM_VERBOSITY=UVM_LOW
regress:
	$(SIMV) +UVM_VERBOSITY=UVM_LOW +UVM_TESTNAME=hbm4_base_test
clean:
	rm -rf simv* csrc *.vpd ucli.key
.PHONY: comp sim regress clean
