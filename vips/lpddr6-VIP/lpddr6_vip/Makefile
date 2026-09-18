# LPDDR6 UVM Testbench Makefile
# SPDX-License-Identifier: Apache-2.0

UVM_HOME ?= $(UVM_HOME)
VCS = vcs -sverilog -ntb_opts uvm-1.2
SIMV = ./simv

SRC = rtl/lpddr6_if.sv \
      rtl/lpddr6_mem_model.sv \
      vip/lpddr6/lpddr6_protocol_checker.sv \
      vip/lpddr6/lpddr6_data_integrity_checker.sv \
      vip/lpddr6/lpddr6_timing_checker.sv \
      vip/lpddr6/lpddr6_error_checker.sv \
      vip/lpddr6/lpddr6_driver.sv \
      vip/lpddr6/lpddr6_monitor.sv \
      vip/lpddr6/lpddr6_agent.sv \
      coverage/lpddr6_coverage.sv \
      env/lpddr6_env.sv \
      sequences/lpddr6_sequence.sv \
      sva/lpddr6_compliance_checker.sv \
      tests/lpddr6_test.sv \
      tb/tb_top.sv

comp:
	$(VCS) +incdir+.+$(UVM_HOME)/src $(UVM_HOME)/src/uvm.sv $(SRC)

sim:
	$(SIMV) +UVM_VERBOSITY=UVM_LOW

regress:
	$(SIMV) +UVM_VERBOSITY=UVM_LOW +UVM_TESTNAME=lpddr6_base_test

clean:
	rm -rf simv* csrc *.vpd ucli.key

.PHONY: comp sim regress clean
