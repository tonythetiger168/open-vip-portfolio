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
#=============================================================================#  # AMBA VIP Makefile  #=============================================================================#  SIMULATOR ?= vcs  TOP       ?= top_tb  TEST      ?= amba_axi_test  SEED      ?= $(shell date +%s)    SRC_DIRS  = ../vip/base ../vip/axi ../vip/ahb ../vip/apb ../rtl ../env ../tests ../tb  INC_FLAGS = $(foreach d,$(SRC_DIRS),+incdir+$d)    SRC_FILES = ../vip/base/amba_vip_pkg.sv ../vip/axi/axi_protocol_checker.sv ../vip/ahb/ahb_protocol_checker.sv ../vip/apb/apb_protocol_checker.sv ../rtl/amba_vip_if.sv ../env/amba_env.sv ../tests/amba_tests.sv ../tb/top_tb.sv    ifeq ($(SIMULATOR),vcs)      COMPILE = vlogan -sverilog -ntb_opts uvm-1.2 $(INC_FLAGS)     ELAB    = vcs -sverilog -ntb_opts uvm-1.2 -timescale=1ns/1ps $(TOP) -o simv     RUN     = ./simv +UVM_TESTNAME=$(TEST) +ntb_random_seed=$(SEED) -l run.log  else ifeq ($(SIMULATOR),xcelium)      COMPILE = xmvlog -sv $(INC_FLAGS)     ELAB    = xmelab -access +rwc -timescale 1ns/1ps $(TOP)     RUN     = xmsim $(TOP) +UVM_TESTNAME=$(TEST) +ntb_random_seed=$(SEED) -l run.log  else ifeq ($(SIMULATOR),questa)      COMPILE = vlog -sv $(INC_FLAGS)     ELAB    = vsim -c $(TOP)     RUN     = vsim -c $(TOP) +UVM_TESTNAME=$(TEST) +ntb_random_seed=$(SEED) -do  run -all; quit  -l run.log  endif    .PHONY: all compile elaborate run clean  all: compile elaborate run  compile: $(COMPILE) $(SRC_FILES)  elaborate: $(ELAB)  run: $(RUN)  clean:         rm -rf simv simv.daidir csrc *.log vc_hdrs.h AN.DB xcelium.d work
# Coverage-driven regression (line/fsm/toggle/SVA assert, goal 100%)
-include coverage.mk
