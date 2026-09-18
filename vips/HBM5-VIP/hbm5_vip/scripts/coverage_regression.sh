#!/bin/bash
#=============================================================================#
# Coverage-Driven Regression — HBM5-VIP
# Metrics : line / fsm / toggle / assert(SVA)
# Goal    : 100% on every metric (override with COV_GOAL=<n>)
# Sim     : SIMULATOR=vcs|xcelium|questa (default vcs)
#=============================================================================#
set -e
cd "$(dirname "$0")"

SIMULATOR=${SIMULATOR:-vcs}
COV_GOAL=${COV_GOAL:-100}
JOBS=${JOBS:-4}
SEEDS=${SEEDS:-"12345 67890 13579 24680 99999"}
TESTS=${TESTS:-"hbm5_base_test"}

echo "=============================================================="
echo " HBM5-VIP — Coverage-Driven Regression"
echo " Simulator : $SIMULATOR"
echo " Goal      : ${COV_GOAL}% (line / fsm / toggle / assert)"
echo " Tests     : $TESTS"
echo " Seeds     : $SEEDS"
echo " Jobs      : $JOBS"
echo "=============================================================="

# 1. Build with coverage instrumentation
make cov_build SIMULATOR=$SIMULATOR COV_GOAL=$COV_GOAL

# 2. Run test x seed matrix in parallel, each run dumping coverage
run_one() {
    local test=$1 seed=$2
    make cov_run_one SIMULATOR=$SIMULATOR TEST=$test SEED=$seed COV_GOAL=$COV_GOAL
}
export -f run_one
export SIMULATOR COV_GOAL

for t in $TESTS; do
    for s in $SEEDS; do
        echo "$t $s"
    done
done | xargs -P "$JOBS" -n 2 bash -c 'run_one "$@"' _

# 3. Merge + report + 100% closure gate (exits non-zero below goal)
make cov_merge  SIMULATOR=$SIMULATOR COV_GOAL=$COV_GOAL
make cov_report SIMULATOR=$SIMULATOR COV_GOAL=$COV_GOAL
make cov_check  SIMULATOR=$SIMULATOR COV_GOAL=$COV_GOAL

echo "=============================================================="
echo " REGRESSION PASSED — coverage goal ${COV_GOAL}% reached"
echo "=============================================================="
