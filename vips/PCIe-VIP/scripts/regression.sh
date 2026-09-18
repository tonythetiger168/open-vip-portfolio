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
#!/bin/bash  #=============================================================================#  # Multi-Protocol VIP Regression Runner  # Parallel execution with coverage merge  #=============================================================================#  TEST_LIST=(      mp_random_regression_test      mp_pcie_gen5_test      mp_pcie_gen6_test      mp_cxl20_test      mp_cxl30_test      mp_ucie_test      mp_ualink_test      mp_power_mgmt_test      mp_error_inject_test  )  SEEDS=(12345 67890 13579 24680 99999)  PARALLEL_JOBS=4    mkdir -p logs coverage    echo  ==========================================  echo  Multi-Protocol VIP Regression Suite  echo  Protocols: PCIe Gen5/6, CXL 2.0/3.0, UCIe, UALink  echo  ==========================================    run_test() {      local test=$1      local seed=$2      local logfile= logs/${test}_${seed}.log           echo  [$(date +%H:%M:%S)] Starting $test (seed=$seed)           ./simv +UVM_TESTNAME=$test +ntb_random_seed=$seed             +UVM_VERBOSITY=UVM_LOW             -cm_dir coverage/$test _$seed.vdb             > $logfile 2>&1           echo  [$(date +%H:%M:%S)] Completed $test (seed=$seed)  }    export -f run_test    # Generate job list and run in parallel  for test in  ${TEST_LIST[@]} ; do      for seed in  ${SEEDS[@]} ; do          echo  $test $seed      done  done | xargs -P $PARALLEL_JOBS -n 2 bash -c  run_test  $@  _    # Merge coverage  echo  Merging coverage...  urg -dir coverage/*.vdb -dbname merged.vdb -report coverage_report    echo  ==========================================  echo  Regression Complete  echo  Logs: logs/  echo  Coverage: coverage_report/  echo  ==========================================  
