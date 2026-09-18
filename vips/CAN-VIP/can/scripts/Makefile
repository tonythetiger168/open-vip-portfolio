#=============================================================================#
# CAN-VIP Makefile (generated)
# Supports: Synopsys VCS, Cadence Xcelium, Siemens Questa
# Coverage-driven regression: make cov   (line/fsm/toggle/assert, goal 100%)
#=============================================================================#

SIMULATOR ?= vcs
TOP       ?= top_tb
TEST      ?= base_test
SEED      ?= $(shell date +%s)

ALL_SV    = $(shell cd .. && find . -name '*.sv' ! -path './scripts/*' | sort)
PKG_SV    = $(filter %_pkg.sv,$(ALL_SV))
TB_SV     = $(filter %/tb_top.sv %/top_tb.sv,$(ALL_SV))
SRC_FILES = $(addprefix ../,$(PKG_SV) $(filter-out $(PKG_SV) $(TB_SV),$(ALL_SV)) $(TB_SV))
INC_FLAGS = $(addprefix +incdir+../,$(sort $(dir $(ALL_SV))))

ifeq ($(SIMULATOR),vcs)
    COMPILE = vlogan -sverilog -ntb_opts uvm-1.2 $(INC_FLAGS)
    ELAB    = vcs -sverilog -ntb_opts uvm-1.2 -timescale=1ns/1ps $(TOP) -o simv
    RUN     = ./simv +UVM_TESTNAME=$(TEST) +ntb_random_seed=$(SEED) -l run.log
else ifeq ($(SIMULATOR),xcelium)
    COMPILE = xmvlog -sv $(INC_FLAGS)
    ELAB    = xmelab -access +rwc -timescale 1ns/1ps $(TOP)
    RUN     = xmsim $(TOP) +UVM_TESTNAME=$(TEST) +ntb_random_seed=$(SEED) -l run.log
else ifeq ($(SIMULATOR),questa)
    COMPILE = vlog -sv $(INC_FLAGS)
    ELAB    = vsim -c $(TOP)
    RUN     = vsim -c $(TOP) +UVM_TESTNAME=$(TEST) +ntb_random_seed=$(SEED) -do "run -all; quit" -l run.log
endif

.PHONY: all compile elaborate run clean regression
all: compile elaborate run

compile:
	$(COMPILE) $(SRC_FILES)

elaborate:
	$(ELAB)

run:
	$(RUN)

regression:
	@./coverage_regression.sh

clean:
	rm -rf simv simv.daidir csrc *.log vc_hdrs.h AN.DB xcelium.d work logs coverage

# Coverage-driven regression (line/fsm/toggle/SVA assert, goal 100%)
-include coverage.mk
