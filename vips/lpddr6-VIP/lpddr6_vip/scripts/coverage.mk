#=============================================================================#
# Coverage-Driven Regression — lpddr6-VIP
# Metrics: line / fsm / toggle / assert(SVA)   Goal: $(COV_GOAL)% (default 100)
# Include from Makefile:  -include coverage.mk
# Usage:
#   make cov                 # full flow: build -> regress -> merge -> check
#   ./coverage_regression.sh # same flow, parallel test x seed matrix
#=============================================================================#

COV_GOAL     ?= 100
COV_DIR      ?= coverage
COV_LOG_DIR  ?= logs
COV_TESTS    ?= lpddr6_base_test
COV_SEEDS    ?= 12345 67890 13579 24680 99999
PYTHON       ?= python3

#-----------------------------------------------------------------------------#
# Per-simulator coverage switches (line + fsm + toggle + assert/SVA)
#-----------------------------------------------------------------------------#
ifeq ($(SIMULATOR),vcs)
  COV_CMP_FLAGS   =
  COV_ELAB_FLAGS  = -cm line+fsm+tgl+assert -cm_dir $(COV_DIR)/simv.vdb
  COV_RUN_FLAGS   = -cm line+fsm+tgl+assert -cm_name $(TEST)_$(SEED)
  COV_MERGE       = urg -full64 -dir $(COV_DIR)/simv.vdb -dbname $(COV_DIR)/merged.vdb -report $(COV_DIR)/urg_report -format both
  COV_RPT_FILES   = $(COV_DIR)/urg_report
else ifeq ($(SIMULATOR),xcelium)
  COV_CMP_FLAGS   = -coverage all
  COV_ELAB_FLAGS  = -coverage all -covdut $(TOP) -covworkdir $(COV_DIR)/cov_work
  COV_RUN_FLAGS   = -covworkdir $(COV_DIR)/cov_work -covtest $(TEST)_$(SEED) -covoverwrite
  COV_MERGE       = imc -batch -initcov merge -load $(COV_DIR)/cov_work/scope/$(TEST)_$(SEED) -out $(COV_DIR)/merged
  COV_RPT_FILES   = $(COV_DIR)/merged
else ifeq ($(SIMULATOR),questa)
  COV_CMP_FLAGS   = +cover=sbceft +assert
  COV_ELAB_FLAGS  = -coverage -assertdebug
  COV_RUN_FLAGS   = -coverage -assertdebug
  COV_MERGE       = vcover merge $(COV_DIR)/merged.ucdb $(COV_DIR)/*.ucdb
  COV_RPT_FILES   = $(COV_DIR)/questa_cov.txt
endif

.PHONY: cov cov_build cov_run_one cov_merge cov_report cov_check cov_clean

# Full coverage-driven regression, fails unless every metric >= COV_GOAL
cov: cov_build cov_merge cov_report cov_check
	@echo "=============================================================="
	@echo " [COV] $(COV_GOAL)% closure reached: line/fsm/toggle/assert"
	@echo "=============================================================="

cov_build:
	@mkdir -p $(COV_DIR) $(COV_LOG_DIR)
	$(COMPILE) $(COV_CMP_FLAGS) $(SRC_FILES)
	$(ELAB) $(COV_ELAB_FLAGS)

# Single (test,seed) run with coverage. Invoked by coverage_regression.sh.
cov_run_one:
	@mkdir -p $(COV_DIR) $(COV_LOG_DIR)
	@echo "[COV] $(TEST) seed=$(SEED)"
ifeq ($(SIMULATOR),questa)
	vsim -c $(TOP) +UVM_TESTNAME=$(TEST) +ntb_random_seed=$(SEED) $(COV_RUN_FLAGS) \
	  -do "coverage save -onexit $(COV_DIR)/$(TEST)_$(SEED).ucdb; run -all; quit" \
	  -l $(COV_LOG_DIR)/$(TEST)_$(SEED).log
else
	$(RUN) $(COV_RUN_FLAGS)
	@mv run.log $(COV_LOG_DIR)/$(TEST)_$(SEED).log 2>/dev/null || true
endif

cov_merge:
	@echo "[COV] Merging coverage databases..."
	$(COV_MERGE)

cov_report:
ifeq ($(SIMULATOR),xcelium)
	imc -batch -load $(COV_DIR)/merged -exec "report -detail -out $(COV_DIR)/imc_cov.txt"
else ifeq ($(SIMULATOR),questa)
	vcover report -details -output $(COV_DIR)/questa_cov.txt $(COV_DIR)/merged.ucdb
	vcover report -html -output $(COV_DIR)/questa_html $(COV_DIR)/merged.ucdb
else
	@echo "[COV] URG report at $(COV_DIR)/urg_report"
endif

# Hard gate: every metric (line/fsm/toggle/assert) must reach COV_GOAL (100)
cov_check:
	$(PYTHON) cov_check.py --simulator $(SIMULATOR) --report $(COV_DIR) --goal $(COV_GOAL)

cov_clean:
	rm -rf $(COV_DIR) $(COV_LOG_DIR)
