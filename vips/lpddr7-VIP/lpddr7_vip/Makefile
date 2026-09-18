# LPDDR7 UVM Testbench Makefile
# SPDX-License-Identifier: Apache-2.0

UVM_HOME ?= $(UVM_HOME)
VCS = vcs -sverilog -ntb_opts uvm-1.2
SIMV = ./simv

SRC = rtl/lpddr7_if.sv \
      rtl/lpddr7_mem_model.sv \
      vip/lpddr7/lpddr7_protocol_checker.sv \
      vip/lpddr7/lpddr7_data_integrity_checker.sv \
      vip/lpddr7/lpddr7_timing_checker.sv \
      vip/lpddr7/lpddr7_error_checker.sv \
      vip/lpddr7/lpddr7_driver.sv \
      vip/lpddr7/lpddr7_monitor.sv \
      vip/lpddr7/lpddr7_agent.sv \
      coverage/lpddr7_coverage.sv \
      env/lpddr7_env.sv \
      sequences/lpddr7_sequence.sv \
      sva/lpddr7_compliance_checker.sv \
      tests/lpddr7_test.sv \
      tb/tb_top.sv

comp:
	$(VCS) +incdir+.+$(UVM_HOME)/src $(UVM_HOME)/src/uvm.sv $(SRC)

sim:
	$(SIMV) +UVM_VERBOSITY=UVM_LOW

regress:
	$(SIMV) +UVM_VERBOSITY=UVM_LOW +UVM_TESTNAME=lpddr7_base_test

clean:
	rm -rf simv* csrc *.vpd ucli.key

.PHONY: comp sim regress clean
