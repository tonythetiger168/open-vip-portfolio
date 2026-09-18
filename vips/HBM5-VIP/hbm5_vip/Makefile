# HBM5 UVM Testbench Makefile
# SPDX-License-Identifier: Apache-2.0

UVM_HOME ?= $(UVM_HOME)
VCS = vcs -sverilog -ntb_opts uvm-1.2
SIMV = ./simv

SRC = rtl/hbm5_if.sv \
      sequences/hbm5_sequence.sv \
      vip/hbm5/hbm5_driver.sv \
      vip/hbm5/hbm5_monitor.sv \
      vip/hbm5/hbm5_agent.sv \
      vip/hbm5/hbm5_scoreboard.sv \
      vip/hbm5/hbm5_coverage.sv \
      env/hbm5_env.sv \
      vip/hbm5/hbm5_protocol_checker.sv \
      vip/hbm5/hbm5_data_integrity_checker.sv \
      vip/hbm5/hbm5_timing_checker.sv \
      vip/hbm5/hbm5_error_checker.sv \
      sva/hbm5_compliance_checker.sv \
      tests/hbm5_test.sv \
      tb/tb_top.sv

comp:
	$(VCS) +incdir+.+$(UVM_HOME)/src $(UVM_HOME)/src/uvm.sv $(SRC)

sim:
	$(SIMV) +UVM_VERBOSITY=UVM_LOW

regress:
	$(SIMV) +UVM_VERBOSITY=UVM_LOW +UVM_TESTNAME=hbm5_directed_test

clean:
	rm -rf simv* csrc *.vpd ucli.key

.PHONY: comp sim regress clean
