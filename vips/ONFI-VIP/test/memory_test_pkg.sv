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
//------------------------------------------------------------------------------
// Memory VIP tests. ONFI is the deepened protocol: the base test wires the
// env; memory_coverage_regression_test runs every protocol's coverage
// sequences (ONFI runs its full directed library + regression mix);
// onfi_deep_test runs the ONFI regression mix standalone.
//------------------------------------------------------------------------------
`ifndef MEMORY_TEST_PKG_SV
`define MEMORY_TEST_PKG_SV

package memory_test_pkg;

  import uvm_pkg::*;
  `include "uvm_macros.svh"
  import ddr_pkg::*;
  import lpddr_pkg::*;
  import hbm_pkg::*;
  import ufs_pkg::*;
  import unipro_pkg::*;
  import emmc_pkg::*;
  import onfi_pkg::*;
  import sd_pkg::*;
  import memory_env_pkg::*;

  class memory_base_test extends uvm_test;
    `uvm_component_utils(memory_base_test)

    memory_env     env;
    memory_env_cfg env_cfg;
    int            random_seed;

    function new(string name, uvm_component parent);
      super.new(name, parent);
    endfunction

    function void build_phase(uvm_phase phase);
      super.build_phase(phase);
      env_cfg = memory_env_cfg::type_id::create("env_cfg");
      env_cfg.coverage_enable   = 1;
      env_cfg.scoreboard_enable = 1;
      env = memory_env::type_id::create("env", this);
      uvm_config_db#(memory_env_cfg)::set(this, "env", "cfg", env_cfg);
      if (!$value$plusargs("ntb_random_seed=%d", random_seed))
        random_seed = $urandom;
      $srandom(random_seed);
    endfunction

    function void report_phase(uvm_phase phase);
      uvm_report_server server = uvm_report_server::get_server();
      int err_count = server.get_severity_count(UVM_ERROR);
      `uvm_info(get_type_name(),
        $sformatf("Seed: %0d | Errors: %0d", random_seed, err_count), UVM_LOW)
      if (err_count == 0) `uvm_info(get_type_name(), "TEST PASSED", UVM_LOW)
      else `uvm_error(get_type_name(),
        $sformatf("TEST FAILED with %0d errors", err_count))
    endfunction
  endclass : memory_base_test

  class memory_coverage_regression_test extends memory_base_test;
    `uvm_component_utils(memory_coverage_regression_test)

    function new(string name, uvm_component parent);
      super.new(name, parent);
    endfunction

    task run_phase(uvm_phase phase);
      phase.raise_objection(this);
      `uvm_info(get_type_name(), "==========================================", UVM_NONE)
      `uvm_info(get_type_name(), "  MEMORY PROTOCOL COVERAGE REGRESSION", UVM_NONE)
      `uvm_info(get_type_name(), "  ONFI deepened; siblings are stubs", UVM_NONE)
      `uvm_info(get_type_name(), "==========================================", UVM_NONE)

      `uvm_info(get_type_name(), "[1/9] DDR Coverage Sequences", UVM_LOW)
      begin ddr_cov_cmd_seq seq = new("seq");  seq.start(env.ddr_ag.sqr); end
      begin ddr_cov_bank_seq seq = new("seq"); seq.start(env.ddr_ag.sqr); end
      begin ddr_cov_bl_seq seq = new("seq");   seq.start(env.ddr_ag.sqr); end
      begin ddr_rw_seq seq = new("seq"); seq.num_trans = env_cfg.num_ddr; seq.start(env.ddr_ag.sqr); end

      `uvm_info(get_type_name(), "[2/9] LPDDR Coverage Sequences", UVM_LOW)
      begin lpddr_cov_cmd_seq seq = new("seq");  seq.start(env.lpddr_ag.sqr); end
      begin lpddr_cov_bank_seq seq = new("seq"); seq.start(env.lpddr_ag.sqr); end
      begin lpddr_rw_seq seq = new("seq"); seq.num_trans = env_cfg.num_lpddr; seq.start(env.lpddr_ag.sqr); end

      `uvm_info(get_type_name(), "[3/9] HBM Coverage Sequences", UVM_LOW)
      begin hbm_cov_cmd_seq seq = new("seq"); seq.start(env.hbm_ag.sqr); end
      begin hbm_cov_ch_seq seq = new("seq");  seq.start(env.hbm_ag.sqr); end
      begin hbm_rw_seq seq = new("seq"); seq.num_trans = env_cfg.num_hbm; seq.start(env.hbm_ag.sqr); end

      `uvm_info(get_type_name(), "[4/9] UFS Coverage Sequences", UVM_LOW)
      begin ufs_cov_upiu_seq seq = new("seq"); seq.start(env.ufs_ag.sqr); end
      begin ufs_cov_lun_seq seq = new("seq");  seq.start(env.ufs_ag.sqr); end
      begin ufs_rw_seq seq = new("seq"); seq.num_trans = env_cfg.num_ufs; seq.start(env.ufs_ag.sqr); end

      `uvm_info(get_type_name(), "[5/9] UniPro Coverage Sequences", UVM_LOW)
      begin unipro_cov_msg_seq seq = new("seq");   seq.start(env.unipro_ag.sqr); end
      begin unipro_cov_cport_seq seq = new("seq"); seq.start(env.unipro_ag.sqr); end
      begin unipro_rw_seq seq = new("seq"); seq.num_trans = env_cfg.num_unipro; seq.start(env.unipro_ag.sqr); end

      `uvm_info(get_type_name(), "[6/9] eMMC Coverage Sequences", UVM_LOW)
      begin emmc_cov_cmd_seq seq = new("seq"); seq.start(env.emmc_ag.sqr); end
      begin emmc_cov_bw_seq seq = new("seq");  seq.start(env.emmc_ag.sqr); end
      begin emmc_rw_seq seq = new("seq"); seq.num_trans = env_cfg.num_emmc; seq.start(env.emmc_ag.sqr); end

      `uvm_info(get_type_name(), "[7/9] ONFI Coverage Sequences (deepened)", UVM_LOW)
      begin onfi_cov_cmd_seq seq = new("seq"); seq.start(env.onfi_ag.sqr); end
      begin onfi_program_read_seq seq = new("seq"); seq.start(env.onfi_ag.sqr); end
      begin onfi_erase_seq seq = new("seq");  seq.start(env.onfi_ag.sqr); end
      begin onfi_reset_seq seq = new("seq");  seq.start(env.onfi_ag.sqr); end
      begin onfi_error_seq seq = new("seq");  seq.start(env.onfi_ag.sqr); end
      begin onfi_b2b_seq seq = new("seq");    seq.start(env.onfi_ag.sqr); end
      begin onfi_corner_seq seq = new("seq"); seq.start(env.onfi_ag.sqr); end
      begin onfi_rw_seq seq = new("seq"); seq.num_trans = env_cfg.num_onfi; seq.start(env.onfi_ag.sqr); end
      begin onfi_regression_seq seq = new("seq"); seq.num_iters = 2; seq.start(env.onfi_ag.sqr); end

      `uvm_info(get_type_name(), "[8/9] SD Coverage Sequences", UVM_LOW)
      begin sd_cov_cmd_seq seq = new("seq"); seq.start(env.sd_ag.sqr); end
      begin sd_rw_seq seq = new("seq"); seq.num_trans = env_cfg.num_sd; seq.start(env.sd_ag.sqr); end

      `uvm_info(get_type_name(), "==========================================", UVM_NONE)
      `uvm_info(get_type_name(), "  All Coverage Sequences Complete", UVM_NONE)
      `uvm_info(get_type_name(), "==========================================", UVM_NONE)
      phase.drop_objection(this);
    endtask
  endclass : memory_coverage_regression_test

  // Standalone ONFI deep regression: full directed library + stress mix
  class onfi_deep_test extends memory_base_test;
    `uvm_component_utils(onfi_deep_test)

    function new(string name, uvm_component parent);
      super.new(name, parent);
    endfunction

    task run_phase(uvm_phase phase);
      phase.raise_objection(this);
      `uvm_info(get_type_name(), "ONFI deep regression start", UVM_LOW)
      begin onfi_cov_cmd_seq seq = new("seq"); seq.start(env.onfi_ag.sqr); end
      begin onfi_program_read_seq seq = new("seq"); seq.start(env.onfi_ag.sqr); end
      begin onfi_erase_seq seq = new("seq");  seq.start(env.onfi_ag.sqr); end
      begin onfi_reset_seq seq = new("seq");  seq.start(env.onfi_ag.sqr); end
      begin onfi_error_seq seq = new("seq");  seq.start(env.onfi_ag.sqr); end
      begin onfi_b2b_seq seq = new("seq");    seq.start(env.onfi_ag.sqr); end
      begin onfi_corner_seq seq = new("seq"); seq.start(env.onfi_ag.sqr); end
      begin onfi_stress_seq seq = new("seq"); seq.num_trans = 32; seq.start(env.onfi_ag.sqr); end
      begin onfi_regression_seq seq = new("seq"); seq.num_iters = 4; seq.start(env.onfi_ag.sqr); end
      `uvm_info(get_type_name(), "ONFI deep regression complete", UVM_LOW)
      phase.drop_objection(this);
    endtask
  endclass : onfi_deep_test

endpackage : memory_test_pkg

`endif // MEMORY_TEST_PKG_SV
