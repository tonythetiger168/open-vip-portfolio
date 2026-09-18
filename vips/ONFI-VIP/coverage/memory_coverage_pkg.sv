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
// Memory Protocol Coverage Package
// ONFI coverage is deepened (config / command-FSM transition / data
// covergroups with crosses). The 7 sibling protocol coverage classes are
// minimal single-covergroup collectors (stub protocols, not graded).
//------------------------------------------------------------------------------
`ifndef MEMORY_COVERAGE_PKG_SV
`define MEMORY_COVERAGE_PKG_SV

package memory_coverage_pkg;

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

  //============================================================================
  // Deepened ONFI coverage: config / FSM transition / data covergroups
  //============================================================================
  class onfi_coverage extends uvm_component;
    `uvm_component_utils(onfi_coverage)

    uvm_analysis_imp #(onfi_seq_item, onfi_coverage) analysis_export;
    onfi_seq_item item;
    real coverage_target = 100.0;

    // ---- CG1: command / configuration coverage ----------------------------
    covergroup onfi_cfg_cg;
      option.per_instance = 1;
      option.goal = 100;
      cp_cmd: coverpoint item.cmd_type {
        bins read_id    = {onfi_seq_item::READ_ID};
        bins read_stat  = {onfi_seq_item::READ_STATUS};
        bins read_page  = {onfi_seq_item::READ_PAGE};
        bins prog_page  = {onfi_seq_item::PROGRAM_PAGE};
        bins erase_blk  = {onfi_seq_item::ERASE_BLOCK};
        bins reset      = {onfi_seq_item::RESET};
        bins read_param = {onfi_seq_item::READ_PARAMETER};
        bins set_feat   = {onfi_seq_item::SET_FEATURES};
        bins get_feat   = {onfi_seq_item::GET_FEATURES};
        bins mp_ops     = {onfi_seq_item::READ_MULTI_PLANE,
                           onfi_seq_item::PROGRAM_MULTI_PLANE};
      }
      cp_block: coverpoint item.block_addr {
        bins first = {0};
        bins last  = {63};
        bins mid   = {[1:62]};
      }
      cp_page: coverpoint item.page_addr {
        bins first = {0};
        bins last  = {63};
        bins mid   = {[1:62]};
      }
      cp_len: coverpoint item.num_bytes {
        bins single = {1};
        bins short  = {[2:4]};
        bins long   = {[5:16]};
      }
      cx_cmd_block: cross cp_cmd, cp_block;
      cx_cmd_len:   cross cp_cmd, cp_len;
    endgroup

    // ---- CG2: command FSM transition coverage -----------------------------
    covergroup onfi_fsm_cg;
      option.per_instance = 1;
      option.goal = 100;
      cp_trans: coverpoint item.cmd_type {
        bins prog_then_read  = (onfi_seq_item::PROGRAM_PAGE => onfi_seq_item::READ_PAGE);
        bins prog_then_stat  = (onfi_seq_item::PROGRAM_PAGE => onfi_seq_item::READ_STATUS);
        bins erase_then_read = (onfi_seq_item::ERASE_BLOCK  => onfi_seq_item::READ_PAGE);
        bins reset_then_any  = (onfi_seq_item::RESET        => onfi_seq_item::READ_STATUS,
                                onfi_seq_item::RESET        => onfi_seq_item::READ_ID,
                                onfi_seq_item::RESET        => onfi_seq_item::PROGRAM_PAGE);
        bins read_then_prog  = (onfi_seq_item::READ_PAGE    => onfi_seq_item::PROGRAM_PAGE);
        bins b2b_reads       = (onfi_seq_item::READ_PAGE    => onfi_seq_item::READ_PAGE);
        bins b2b_progs       = (onfi_seq_item::PROGRAM_PAGE => onfi_seq_item::PROGRAM_PAGE);
        bins feat_seq        = (onfi_seq_item::SET_FEATURES => onfi_seq_item::GET_FEATURES);
      }
    endgroup

    // ---- CG3: data / status coverage --------------------------------------
    covergroup onfi_data_cg;
      option.per_instance = 1;
      option.goal = 100;
      cp_data: coverpoint item.data {
        bins zeros = {8'h00};
        bins ones  = {8'hFF};
        bins a5    = {8'hA5};
        bins other = default;
      }
      cp_status_fail: coverpoint item.status[0] {
        bins pass = {0};
        bins fail = {1};
      }
      cp_status_rdy: coverpoint item.status[6] {
        bins busy = {0};
        bins rdy  = {1};
      }
      cp_expect_fail: coverpoint item.expect_fail {
        bins normal = {0};
        bins wp_violation = {1};
      }
      cx_fail_mode: cross cp_expect_fail, cp_status_fail;
    endgroup

    function new(string name, uvm_component parent);
      super.new(name, parent);
      analysis_export = new("analysis_export", this);
      onfi_cfg_cg  = new();
      onfi_fsm_cg  = new();
      onfi_data_cg = new();
    endfunction

    virtual function void write(onfi_seq_item t);
      item = t;
      onfi_cfg_cg.sample();
      onfi_fsm_cg.sample();
      onfi_data_cg.sample();
    endfunction

    function real get_coverage();
      return (onfi_cfg_cg.get_coverage() + onfi_fsm_cg.get_coverage()
              + onfi_data_cg.get_coverage()) / 3.0;
    endfunction

    function void report_phase(uvm_phase phase);
      real cov = get_coverage();
      `uvm_info(get_type_name(), $sformatf("ONFI Coverage: %0.2f%% (cfg=%0.2f fsm=%0.2f data=%0.2f)",
                cov, onfi_cfg_cg.get_coverage(), onfi_fsm_cg.get_coverage(),
                onfi_data_cg.get_coverage()), UVM_LOW)
      if (cov < coverage_target)
        `uvm_error(get_type_name(), "ONFI Coverage < 100%")
    endfunction
  endclass : onfi_coverage

  //============================================================================
  // Minimal stub-protocol coverage collectors (coverage_target = 0: the stub
  // protocols are collected for plumbing completeness, not graded)
  //============================================================================
  class ddr_coverage extends uvm_component;
    `uvm_component_utils(ddr_coverage)
    uvm_analysis_imp #(ddr_seq_item, ddr_coverage) analysis_export;
    ddr_seq_item item;
    real coverage_target = 0.0;
    covergroup ddr_cg;
      option.per_instance = 1;
      cmd: coverpoint item.cmd_type;
    endgroup
    function new(string name, uvm_component parent);
      super.new(name, parent);
      analysis_export = new("analysis_export", this);
      ddr_cg = new();
    endfunction
    virtual function void write(ddr_seq_item t);
      item = t;
      ddr_cg.sample();
    endfunction
    function real get_coverage();
      return ddr_cg.get_coverage();
    endfunction
    function void report_phase(uvm_phase phase);
      real cov = get_coverage();
      `uvm_info(get_type_name(), $sformatf("DDR Coverage: %0.2f%%", cov), UVM_LOW)
    endfunction
  endclass : ddr_coverage

  class lpddr_coverage extends uvm_component;
    `uvm_component_utils(lpddr_coverage)
    uvm_analysis_imp #(lpddr_seq_item, lpddr_coverage) analysis_export;
    lpddr_seq_item item;
    real coverage_target = 0.0;
    covergroup lpddr_cg;
      option.per_instance = 1;
      cmd: coverpoint item.cmd_type;
    endgroup
    function new(string name, uvm_component parent);
      super.new(name, parent);
      analysis_export = new("analysis_export", this);
      lpddr_cg = new();
    endfunction
    virtual function void write(lpddr_seq_item t);
      item = t;
      lpddr_cg.sample();
    endfunction
    function real get_coverage();
      return lpddr_cg.get_coverage();
    endfunction
    function void report_phase(uvm_phase phase);
      real cov = get_coverage();
      `uvm_info(get_type_name(), $sformatf("LPDDR Coverage: %0.2f%%", cov), UVM_LOW)
    endfunction
  endclass : lpddr_coverage

  class hbm_coverage extends uvm_component;
    `uvm_component_utils(hbm_coverage)
    uvm_analysis_imp #(hbm_seq_item, hbm_coverage) analysis_export;
    hbm_seq_item item;
    real coverage_target = 0.0;
    covergroup hbm_cg;
      option.per_instance = 1;
      cmd: coverpoint item.cmd_type;
    endgroup
    function new(string name, uvm_component parent);
      super.new(name, parent);
      analysis_export = new("analysis_export", this);
      hbm_cg = new();
    endfunction
    virtual function void write(hbm_seq_item t);
      item = t;
      hbm_cg.sample();
    endfunction
    function real get_coverage();
      return hbm_cg.get_coverage();
    endfunction
    function void report_phase(uvm_phase phase);
      real cov = get_coverage();
      `uvm_info(get_type_name(), $sformatf("HBM Coverage: %0.2f%%", cov), UVM_LOW)
    endfunction
  endclass : hbm_coverage

  class ufs_coverage extends uvm_component;
    `uvm_component_utils(ufs_coverage)
    uvm_analysis_imp #(ufs_seq_item, ufs_coverage) analysis_export;
    ufs_seq_item item;
    real coverage_target = 0.0;
    covergroup ufs_cg;
      option.per_instance = 1;
      cmd: coverpoint item.cmd_type;
    endgroup
    function new(string name, uvm_component parent);
      super.new(name, parent);
      analysis_export = new("analysis_export", this);
      ufs_cg = new();
    endfunction
    virtual function void write(ufs_seq_item t);
      item = t;
      ufs_cg.sample();
    endfunction
    function real get_coverage();
      return ufs_cg.get_coverage();
    endfunction
    function void report_phase(uvm_phase phase);
      real cov = get_coverage();
      `uvm_info(get_type_name(), $sformatf("UFS Coverage: %0.2f%%", cov), UVM_LOW)
    endfunction
  endclass : ufs_coverage

  class unipro_coverage extends uvm_component;
    `uvm_component_utils(unipro_coverage)
    uvm_analysis_imp #(unipro_seq_item, unipro_coverage) analysis_export;
    unipro_seq_item item;
    real coverage_target = 0.0;
    covergroup unipro_cg;
      option.per_instance = 1;
      cmd: coverpoint item.cmd_type;
    endgroup
    function new(string name, uvm_component parent);
      super.new(name, parent);
      analysis_export = new("analysis_export", this);
      unipro_cg = new();
    endfunction
    virtual function void write(unipro_seq_item t);
      item = t;
      unipro_cg.sample();
    endfunction
    function real get_coverage();
      return unipro_cg.get_coverage();
    endfunction
    function void report_phase(uvm_phase phase);
      real cov = get_coverage();
      `uvm_info(get_type_name(), $sformatf("UniPro Coverage: %0.2f%%", cov), UVM_LOW)
    endfunction
  endclass : unipro_coverage

  class emmc_coverage extends uvm_component;
    `uvm_component_utils(emmc_coverage)
    uvm_analysis_imp #(emmc_seq_item, emmc_coverage) analysis_export;
    emmc_seq_item item;
    real coverage_target = 0.0;
    covergroup emmc_cg;
      option.per_instance = 1;
      cmd: coverpoint item.cmd_type;
    endgroup
    function new(string name, uvm_component parent);
      super.new(name, parent);
      analysis_export = new("analysis_export", this);
      emmc_cg = new();
    endfunction
    virtual function void write(emmc_seq_item t);
      item = t;
      emmc_cg.sample();
    endfunction
    function real get_coverage();
      return emmc_cg.get_coverage();
    endfunction
    function void report_phase(uvm_phase phase);
      real cov = get_coverage();
      `uvm_info(get_type_name(), $sformatf("eMMC Coverage: %0.2f%%", cov), UVM_LOW)
    endfunction
  endclass : emmc_coverage

  class sd_coverage extends uvm_component;
    `uvm_component_utils(sd_coverage)
    uvm_analysis_imp #(sd_seq_item, sd_coverage) analysis_export;
    sd_seq_item item;
    real coverage_target = 0.0;
    covergroup sd_cg;
      option.per_instance = 1;
      cmd: coverpoint item.cmd_type;
      bw: coverpoint item.bus_width { bins width[3] = {[0:2]}; }
    endgroup
    function new(string name, uvm_component parent);
      super.new(name, parent);
      analysis_export = new("analysis_export", this);
      sd_cg = new();
    endfunction
    virtual function void write(sd_seq_item t);
      item = t;
      sd_cg.sample();
    endfunction
    function real get_coverage();
      return sd_cg.get_coverage();
    endfunction
    function void report_phase(uvm_phase phase);
      real cov = get_coverage();
      `uvm_info(get_type_name(), $sformatf("SD Coverage: %0.2f%%", cov), UVM_LOW)
    endfunction
  endclass : sd_coverage

  //============================================================================
  // Final coverage report aggregator
  //============================================================================
  class memory_coverage_report_checker extends uvm_component;
    `uvm_component_utils(memory_coverage_report_checker)

    ddr_coverage    ddr_cov_h;
    lpddr_coverage  lpddr_cov_h;
    hbm_coverage    hbm_cov_h;
    ufs_coverage    ufs_cov_h;
    unipro_coverage unipro_cov_h;
    emmc_coverage   emmc_cov_h;
    onfi_coverage   onfi_cov_h;
    sd_coverage     sd_cov_h;

    real overall_target = 100.0;

    function new(string name, uvm_component parent);
      super.new(name, parent);
    endfunction

    function void report_phase(uvm_phase phase);
      real ddr_cov = 0, lpddr_cov = 0, hbm_cov = 0, ufs_cov = 0;
      real unipro_cov = 0, emmc_cov = 0, onfi_cov = 0, sd_cov = 0;
      if (ddr_cov_h != null)    ddr_cov    = ddr_cov_h.get_coverage();
      if (lpddr_cov_h != null)  lpddr_cov  = lpddr_cov_h.get_coverage();
      if (hbm_cov_h != null)    hbm_cov    = hbm_cov_h.get_coverage();
      if (ufs_cov_h != null)    ufs_cov    = ufs_cov_h.get_coverage();
      if (unipro_cov_h != null) unipro_cov = unipro_cov_h.get_coverage();
      if (emmc_cov_h != null)   emmc_cov   = emmc_cov_h.get_coverage();
      if (onfi_cov_h != null)   onfi_cov   = onfi_cov_h.get_coverage();
      if (sd_cov_h != null)     sd_cov     = sd_cov_h.get_coverage();

      `uvm_info(get_type_name(), "==========================================", UVM_NONE)
      `uvm_info(get_type_name(), "  MEMORY PROTOCOL COVERAGE FINAL REPORT", UVM_NONE)
      `uvm_info(get_type_name(), "==========================================", UVM_NONE)
      `uvm_info(get_type_name(), $sformatf("DDR    Coverage: %6.2f%%", ddr_cov), UVM_NONE)
      `uvm_info(get_type_name(), $sformatf("LPDDR  Coverage: %6.2f%%", lpddr_cov), UVM_NONE)
      `uvm_info(get_type_name(), $sformatf("HBM    Coverage: %6.2f%%", hbm_cov), UVM_NONE)
      `uvm_info(get_type_name(), $sformatf("UFS    Coverage: %6.2f%%", ufs_cov), UVM_NONE)
      `uvm_info(get_type_name(), $sformatf("UniPro Coverage: %6.2f%%", unipro_cov), UVM_NONE)
      `uvm_info(get_type_name(), $sformatf("eMMC   Coverage: %6.2f%%", emmc_cov), UVM_NONE)
      `uvm_info(get_type_name(), $sformatf("ONFI   Coverage: %6.2f%%", onfi_cov), UVM_NONE)
      `uvm_info(get_type_name(), $sformatf("SD     Coverage: %6.2f%%", sd_cov), UVM_NONE)
      `uvm_info(get_type_name(), "==========================================", UVM_NONE)
    endfunction
  endclass : memory_coverage_report_checker

endpackage : memory_coverage_pkg

`endif // MEMORY_COVERAGE_PKG_SV
