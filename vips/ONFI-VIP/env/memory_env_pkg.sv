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
// Multi-protocol Memory Environment
// ONFI path is deepened: end-to-end expected (driver drv_ap) vs observed
// (monitor item_collected_port) scoreboard comparison with n_matches /
// n_mismatches and UVM_ERROR on mismatch. Sibling protocols are stubs and
// are only counted.
//------------------------------------------------------------------------------
`ifndef MEMORY_ENV_PKG_SV
`define MEMORY_ENV_PKG_SV

package memory_env_pkg;

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
  import memory_coverage_pkg::*;

  `uvm_analysis_imp_decl(_onfi_exp)
  `uvm_analysis_imp_decl(_onfi_obs)
  `uvm_analysis_imp_decl(_ddr)
  `uvm_analysis_imp_decl(_lpddr)
  `uvm_analysis_imp_decl(_hbm)
  `uvm_analysis_imp_decl(_ufs)
  `uvm_analysis_imp_decl(_unipro)
  `uvm_analysis_imp_decl(_emmc)
  `uvm_analysis_imp_decl(_sd)

  //============================================================================
  // Environment configuration
  //============================================================================
  class memory_env_cfg extends uvm_object;
    `uvm_object_utils(memory_env_cfg)

    ddr_cfg    ddr_cfg_h;
    lpddr_cfg  lpddr_cfg_h;
    hbm_cfg    hbm_cfg_h;
    ufs_cfg    ufs_cfg_h;
    unipro_cfg unipro_cfg_h;
    emmc_cfg   emmc_cfg_h;
    onfi_cfg   onfi_cfg_h;
    sd_cfg     sd_cfg_h;

    bit scoreboard_enable = 1;
    bit coverage_enable   = 1;

    int num_ddr    = 30;
    int num_lpddr  = 30;
    int num_hbm    = 30;
    int num_ufs    = 20;
    int num_unipro = 20;
    int num_emmc   = 20;
    int num_onfi   = 20;
    int num_sd     = 20;

    function new(string name = "memory_env_cfg");
      super.new(name);
      ddr_cfg_h    = ddr_cfg::type_id::create("ddr_cfg_h");
      lpddr_cfg_h  = lpddr_cfg::type_id::create("lpddr_cfg_h");
      hbm_cfg_h    = hbm_cfg::type_id::create("hbm_cfg_h");
      ufs_cfg_h    = ufs_cfg::type_id::create("ufs_cfg_h");
      unipro_cfg_h = unipro_cfg::type_id::create("unipro_cfg_h");
      emmc_cfg_h   = emmc_cfg::type_id::create("emmc_cfg_h");
      onfi_cfg_h   = onfi_cfg::type_id::create("onfi_cfg_h");
      sd_cfg_h     = sd_cfg::type_id::create("sd_cfg_h");
    endfunction
  endclass

  //============================================================================
  // Scoreboard: ONFI end-to-end compare + per-protocol counters
  //============================================================================
  class memory_scoreboard extends uvm_scoreboard;
    `uvm_component_utils(memory_scoreboard)

    uvm_analysis_imp_ddr #(ddr_seq_item, memory_scoreboard)    ddr_export;
    uvm_analysis_imp_lpddr #(lpddr_seq_item, memory_scoreboard)  lpddr_export;
    uvm_analysis_imp_hbm #(hbm_seq_item, memory_scoreboard)    hbm_export;
    uvm_analysis_imp_ufs #(ufs_seq_item, memory_scoreboard)    ufs_export;
    uvm_analysis_imp_unipro #(unipro_seq_item, memory_scoreboard) unipro_export;
    uvm_analysis_imp_emmc #(emmc_seq_item, memory_scoreboard)   emmc_export;
    // ONFI observed (monitor) export keeps its original member name
    uvm_analysis_imp_onfi_obs #(onfi_seq_item, memory_scoreboard) onfi_export;
    // ONFI expected (driver) export
    uvm_analysis_imp_onfi_exp #(onfi_seq_item, memory_scoreboard) onfi_exp_export;
    uvm_analysis_imp_sd #(sd_seq_item, memory_scoreboard)     sd_export;

    int ddr_count = 0, lpddr_count = 0, hbm_count = 0, ufs_count = 0;
    int unipro_count = 0, emmc_count = 0, onfi_count = 0, sd_count = 0;

    // ONFI end-to-end comparison state
    int unsigned n_matches    = 0;
    int unsigned n_mismatches = 0;
    protected onfi_seq_item onfi_exp_q[$];

    function new(string name, uvm_component parent);
      super.new(name, parent);
      ddr_export       = new("ddr_export", this);
      lpddr_export     = new("lpddr_export", this);
      hbm_export       = new("hbm_export", this);
      ufs_export       = new("ufs_export", this);
      unipro_export    = new("unipro_export", this);
      emmc_export      = new("emmc_export", this);
      onfi_export      = new("onfi_export", this);
      onfi_exp_export  = new("onfi_exp_export", this);
      sd_export        = new("sd_export", this);
    endfunction

    virtual function void write_ddr(ddr_seq_item item);    ddr_count++;    endfunction
    virtual function void write_lpddr(lpddr_seq_item item);  lpddr_count++;  endfunction
    virtual function void write_hbm(hbm_seq_item item);    hbm_count++;    endfunction
    virtual function void write_ufs(ufs_seq_item item);    ufs_count++;    endfunction
    virtual function void write_unipro(unipro_seq_item item); unipro_count++; endfunction
    virtual function void write_emmc(emmc_seq_item item);   emmc_count++;   endfunction
    virtual function void write_sd(sd_seq_item item);     sd_count++;     endfunction

    // expected side (from onfi_driver.drv_ap)
    virtual function void write_onfi_exp(onfi_seq_item item);
      onfi_exp_q.push_back(item);
    endfunction

    // observed side (from onfi_monitor.item_collected_port)
    virtual function void write_onfi_obs(onfi_seq_item item);
      onfi_count++;
      compare_onfi(item);
    endfunction

    // pop the oldest matching expected item and compare end-to-end
    protected function void compare_onfi(onfi_seq_item obs);
      int idx[$];
      idx = onfi_exp_q.find_first_index with (item.cmd_type == obs.cmd_type);
      if (idx.size() == 0) begin
        n_mismatches++;
        `uvm_error(get_type_name(),
          $sformatf("ONFI SB: observed %s with no matching expected item",
                    obs.convert2string()))
        return;
      end
      begin
        onfi_seq_item exp = onfi_exp_q[idx[0]];
        onfi_exp_q.delete(idx[0]);
        if (!onfi_match(exp, obs)) begin
          n_mismatches++;
          `uvm_error(get_type_name(),
            $sformatf("ONFI SB mismatch:\n  EXP: %s\n  OBS: %s",
                      exp.convert2string(), obs.convert2string()))
        end
        else begin
          n_matches++;
          `uvm_info(get_type_name(),
            $sformatf("ONFI SB match: %s", obs.convert2string()), UVM_HIGH)
        end
      end
    endfunction

    // field-level comparison (command, address, payload, read data)
    protected function bit onfi_match(onfi_seq_item exp, onfi_seq_item obs);
      if (exp.cmd_type != obs.cmd_type) return 0;
      case (exp.cmd_type)
        onfi_seq_item::READ_PAGE, onfi_seq_item::READ_MULTI_PLANE: begin
          if (exp.block_addr != obs.block_addr) return 0;
          if (exp.page_addr  != obs.page_addr)  return 0;
          if (exp.read_payload.size() != obs.read_payload.size()) return 0;
          foreach (exp.read_payload[i])
            if (exp.read_payload[i] !== obs.read_payload[i]) return 0;
        end
        onfi_seq_item::PROGRAM_PAGE, onfi_seq_item::PROGRAM_MULTI_PLANE: begin
          if (exp.block_addr != obs.block_addr) return 0;
          if (exp.page_addr  != obs.page_addr)  return 0;
          if (exp.data_payload.size() != obs.data_payload.size()) return 0;
          foreach (exp.data_payload[i])
            if (exp.data_payload[i] !== obs.data_payload[i]) return 0;
        end
        onfi_seq_item::ERASE_BLOCK: begin
          if (exp.block_addr != obs.block_addr) return 0;
        end
        onfi_seq_item::SET_FEATURES: begin
          if (exp.feature_addr != obs.feature_addr) return 0;
          if (exp.feature_val  != obs.feature_val)  return 0;
        end
        onfi_seq_item::READ_ID, onfi_seq_item::READ_PARAMETER,
        onfi_seq_item::GET_FEATURES: begin
          if (obs.read_payload.size() == 0) return 0;
        end
        onfi_seq_item::READ_STATUS: begin
          if (obs.status !== exp.status) return 0;
        end
        default: ; // RESET etc.: command-type match is sufficient
      endcase
      return 1;
    endfunction

    function void report_phase(uvm_phase phase);
      `uvm_info(get_type_name(), "==========================================", UVM_LOW)
      `uvm_info(get_type_name(), "  MEMORY SCOREBOARD REPORT", UVM_LOW)
      `uvm_info(get_type_name(), "==========================================", UVM_LOW)
      `uvm_info(get_type_name(), $sformatf("DDR:    %0d", ddr_count), UVM_LOW)
      `uvm_info(get_type_name(), $sformatf("LPDDR:  %0d", lpddr_count), UVM_LOW)
      `uvm_info(get_type_name(), $sformatf("HBM:    %0d", hbm_count), UVM_LOW)
      `uvm_info(get_type_name(), $sformatf("UFS:    %0d", ufs_count), UVM_LOW)
      `uvm_info(get_type_name(), $sformatf("UniPro: %0d", unipro_count), UVM_LOW)
      `uvm_info(get_type_name(), $sformatf("eMMC:   %0d", emmc_count), UVM_LOW)
      `uvm_info(get_type_name(), $sformatf("ONFI:   %0d", onfi_count), UVM_LOW)
      `uvm_info(get_type_name(), $sformatf("SD:     %0d", sd_count), UVM_LOW)
      `uvm_info(get_type_name(), $sformatf("TOTAL:  %0d",
        ddr_count+lpddr_count+hbm_count+ufs_count+unipro_count+emmc_count+onfi_count+sd_count), UVM_LOW)
      `uvm_info(get_type_name(), $sformatf("ONFI end-to-end: n_matches=%0d n_mismatches=%0d",
        n_matches, n_mismatches), UVM_LOW)
      if (onfi_exp_q.size() != 0)
        `uvm_error(get_type_name(),
          $sformatf("ONFI SB: %0d expected items never observed", onfi_exp_q.size()))
      if (n_mismatches != 0)
        `uvm_error(get_type_name(), "ONFI end-to-end n_mismatches detected")
      `uvm_info(get_type_name(), "==========================================", UVM_LOW)
    endfunction
  endclass : memory_scoreboard

  //============================================================================
  // Environment
  //============================================================================
  class memory_env extends uvm_env;
    `uvm_component_utils(memory_env)

    ddr_agent    ddr_ag;
    lpddr_agent  lpddr_ag;
    hbm_agent    hbm_ag;
    ufs_agent    ufs_ag;
    unipro_agent unipro_ag;
    emmc_agent   emmc_ag;
    onfi_agent   onfi_ag;
    sd_agent     sd_ag;

    ddr_coverage    ddr_cov;
    lpddr_coverage  lpddr_cov;
    hbm_coverage    hbm_cov;
    ufs_coverage    ufs_cov;
    unipro_coverage unipro_cov;
    emmc_coverage   emmc_cov;
    onfi_coverage   onfi_cov;
    sd_coverage     sd_cov;

    memory_coverage_report_checker cov_chk;
    memory_scoreboard sb;
    memory_env_cfg    cfg;

    function new(string name, uvm_component parent);
      super.new(name, parent);
    endfunction

    function void build_phase(uvm_phase phase);
      super.build_phase(phase);
      if (!uvm_config_db#(memory_env_cfg)::get(this, "", "cfg", cfg))
        cfg = memory_env_cfg::type_id::create("cfg");

      // propagate protocol cfgs to the agents
      uvm_config_db#(ddr_cfg)::set(this,    "ddr_ag*",    "cfg", cfg.ddr_cfg_h);
      uvm_config_db#(lpddr_cfg)::set(this,  "lpddr_ag*",  "cfg", cfg.lpddr_cfg_h);
      uvm_config_db#(hbm_cfg)::set(this,    "hbm_ag*",    "cfg", cfg.hbm_cfg_h);
      uvm_config_db#(ufs_cfg)::set(this,    "ufs_ag*",    "cfg", cfg.ufs_cfg_h);
      uvm_config_db#(unipro_cfg)::set(this, "unipro_ag*", "cfg", cfg.unipro_cfg_h);
      uvm_config_db#(emmc_cfg)::set(this,   "emmc_ag*",   "cfg", cfg.emmc_cfg_h);
      uvm_config_db#(onfi_cfg)::set(this,   "onfi_ag*",   "cfg", cfg.onfi_cfg_h);
      uvm_config_db#(sd_cfg)::set(this,     "sd_ag*",     "cfg", cfg.sd_cfg_h);

      ddr_ag    = ddr_agent::type_id::create("ddr_ag", this);
      lpddr_ag  = lpddr_agent::type_id::create("lpddr_ag", this);
      hbm_ag    = hbm_agent::type_id::create("hbm_ag", this);
      ufs_ag    = ufs_agent::type_id::create("ufs_ag", this);
      unipro_ag = unipro_agent::type_id::create("unipro_ag", this);
      emmc_ag   = emmc_agent::type_id::create("emmc_ag", this);
      onfi_ag   = onfi_agent::type_id::create("onfi_ag", this);
      sd_ag     = sd_agent::type_id::create("sd_ag", this);

      if (cfg.coverage_enable) begin
        ddr_cov    = ddr_coverage::type_id::create("ddr_cov", this);
        lpddr_cov  = lpddr_coverage::type_id::create("lpddr_cov", this);
        hbm_cov    = hbm_coverage::type_id::create("hbm_cov", this);
        ufs_cov    = ufs_coverage::type_id::create("ufs_cov", this);
        unipro_cov = unipro_coverage::type_id::create("unipro_cov", this);
        emmc_cov   = emmc_coverage::type_id::create("emmc_cov", this);
        onfi_cov   = onfi_coverage::type_id::create("onfi_cov", this);
        sd_cov     = sd_coverage::type_id::create("sd_cov", this);
        cov_chk    = memory_coverage_report_checker::type_id::create("cov_chk", this);
      end
      if (cfg.scoreboard_enable)
        sb = memory_scoreboard::type_id::create("sb", this);
    endfunction

    function void connect_phase(uvm_phase phase);
      super.connect_phase(phase);
      if (cfg.scoreboard_enable) begin
        ddr_ag.mon.item_collected_port.connect(sb.ddr_export);
        lpddr_ag.mon.item_collected_port.connect(sb.lpddr_export);
        hbm_ag.mon.item_collected_port.connect(sb.hbm_export);
        ufs_ag.mon.item_collected_port.connect(sb.ufs_export);
        unipro_ag.mon.item_collected_port.connect(sb.unipro_export);
        emmc_ag.mon.item_collected_port.connect(sb.emmc_export);
        onfi_ag.mon.item_collected_port.connect(sb.onfi_export);
        sd_ag.mon.item_collected_port.connect(sb.sd_export);
        // ONFI end-to-end: expected side from the driver
        if (cfg.onfi_cfg_h.is_active == UVM_ACTIVE)
          onfi_ag.drv.drv_ap.connect(sb.onfi_exp_export);
      end
      if (cfg.coverage_enable) begin
        ddr_ag.mon.item_collected_port.connect(ddr_cov.analysis_export);
        lpddr_ag.mon.item_collected_port.connect(lpddr_cov.analysis_export);
        hbm_ag.mon.item_collected_port.connect(hbm_cov.analysis_export);
        ufs_ag.mon.item_collected_port.connect(ufs_cov.analysis_export);
        unipro_ag.mon.item_collected_port.connect(unipro_cov.analysis_export);
        emmc_ag.mon.item_collected_port.connect(emmc_cov.analysis_export);
        onfi_ag.mon.item_collected_port.connect(onfi_cov.analysis_export);
        sd_ag.mon.item_collected_port.connect(sd_cov.analysis_export);
        cov_chk.ddr_cov_h    = ddr_cov;
        cov_chk.lpddr_cov_h  = lpddr_cov;
        cov_chk.hbm_cov_h    = hbm_cov;
        cov_chk.ufs_cov_h    = ufs_cov;
        cov_chk.unipro_cov_h = unipro_cov;
        cov_chk.emmc_cov_h   = emmc_cov;
        cov_chk.onfi_cov_h   = onfi_cov;
        cov_chk.sd_cov_h     = sd_cov;
      end
    endfunction
  endclass : memory_env

endpackage : memory_env_pkg

`endif // MEMORY_ENV_PKG_SV
