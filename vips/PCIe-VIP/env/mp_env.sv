// Copyright 2026 VIP Portfolio Contributors
// SPDX-License-Identifier: Apache-2.0
//
//============================================================================
// Multi-Protocol Verification Environment
// Instantiates agents for all supported protocols
//============================================================================
`ifndef MP_ENV_SV
`define MP_ENV_SV

`uvm_analysis_imp_decl(_exp)
`uvm_analysis_imp_decl(_obs)

//============================================================================
// End-to-end scoreboard: compares driver-issued (expected) transactions
// against monitor-decoded (observed) transactions.
//============================================================================
class mp_e2e_scoreboard extends uvm_scoreboard;
  `uvm_component_utils(mp_e2e_scoreboard)
  uvm_analysis_imp_exp #(mp_sequence_item, mp_e2e_scoreboard) exp_ap;
  uvm_analysis_imp_obs #(mp_sequence_item, mp_e2e_scoreboard) obs_ap;

  mp_sequence_item exp_q[$], obs_q[$];
  int unsigned n_matches = 0, n_mismatches = 0;

  function new(string name = "mp_e2e_scoreboard", uvm_component parent = null);
    super.new(name, parent);
    exp_ap = new("exp_ap", this);
    obs_ap = new("obs_ap", this);
  endfunction

  function void write_exp(mp_sequence_item t); exp_q.push_back(t); check_txns(); endfunction
  function void write_obs(mp_sequence_item t); obs_q.push_back(t); check_txns(); endfunction

  function void check_txns();
    while (exp_q.size() && obs_q.size()) begin
      mp_sequence_item e = exp_q.pop_front();
      mp_sequence_item o = obs_q.pop_front();
      if (e.txn.protocol == o.txn.protocol && e.txn.address == o.txn.address &&
          e.txn.tag == o.txn.tag && e.txn.length_dw == o.txn.length_dw)
        n_matches++;
      else begin
        n_mismatches++;
        `uvm_error("E2E_SB", $sformatf("mismatch exp{%s} obs{%s}",
                   e.convert2string(), o.convert2string()))
      end
    end
  endfunction

  function void report_phase(uvm_phase phase);
    `uvm_info("E2E_SB", $sformatf("mp e2e scoreboard: n_matches=%0d n_mismatches=%0d",
              n_matches, n_mismatches), UVM_LOW)
    if (n_mismatches) `uvm_error("E2E_SB", "end-to-end mismatches detected")
  endfunction
endclass

class mp_env extends uvm_env;
  `uvm_component_utils(mp_env)

  // Protocol agents
  mp_agent pcie_gen5_agent;
  mp_agent pcie_gen6_agent;
  mp_agent cxl20_agent;
  mp_agent cxl30_agent;
  mp_agent ucie_agent;
  mp_agent ualink_agent;

  // Scoreboards
  mp_scoreboard     sb;
  mp_e2e_scoreboard e2e_sb;

  // Protocol checkers
  pcie_protocol_checker  pcie_chk;
  cxl_protocol_checker   cxl_chk;
  ucie_protocol_checker  ucie_chk;
  ualink_protocol_checker ualink_chk;

  // Coverage models
  mp_coverage_model pcie_cov;
  mp_coverage_model cxl_cov;
  mp_coverage_model ucie_cov;
  mp_coverage_model ualink_cov;

  // Configuration
  bit enable_pcie_gen5 = 1;
  bit enable_pcie_gen6 = 1;
  bit enable_cxl20     = 1;
  bit enable_cxl30     = 1;
  bit enable_ucie      = 1;
  bit enable_ualink    = 1;

  function new(string name = "mp_env", uvm_component parent = null);
    super.new(name, parent);
  endfunction

  function void build_phase(uvm_phase phase);
    super.build_phase(phase);

    uvm_config_db#(bit)::get(this, "", "enable_pcie_gen5", enable_pcie_gen5);
    uvm_config_db#(bit)::get(this, "", "enable_pcie_gen6", enable_pcie_gen6);
    uvm_config_db#(bit)::get(this, "", "enable_cxl20", enable_cxl20);
    uvm_config_db#(bit)::get(this, "", "enable_cxl30", enable_cxl30);
    uvm_config_db#(bit)::get(this, "", "enable_ucie", enable_ucie);
    uvm_config_db#(bit)::get(this, "", "enable_ualink", enable_ualink);

    if (enable_pcie_gen5) begin
      pcie_gen5_agent = mp_agent::type_id::create("pcie_gen5_agent", this);
      uvm_config_db#(protocol_e)::set(pcie_gen5_agent, "", "protocol", PROTO_PCIE_GEN5);
    end
    if (enable_pcie_gen6) begin
      pcie_gen6_agent = mp_agent::type_id::create("pcie_gen6_agent", this);
      uvm_config_db#(protocol_e)::set(pcie_gen6_agent, "", "protocol", PROTO_PCIE_GEN6);
    end
    if (enable_cxl20) begin
      cxl20_agent = mp_agent::type_id::create("cxl20_agent", this);
      uvm_config_db#(protocol_e)::set(cxl20_agent, "", "protocol", PROTO_CXL_20);
    end
    if (enable_cxl30) begin
      cxl30_agent = mp_agent::type_id::create("cxl30_agent", this);
      uvm_config_db#(protocol_e)::set(cxl30_agent, "", "protocol", PROTO_CXL_30);
    end
    if (enable_ucie) begin
      ucie_agent = mp_agent::type_id::create("ucie_agent", this);
      uvm_config_db#(protocol_e)::set(ucie_agent, "", "protocol", PROTO_UCIE);
    end
    if (enable_ualink) begin
      ualink_agent = mp_agent::type_id::create("ualink_agent", this);
      uvm_config_db#(protocol_e)::set(ualink_agent, "", "protocol", PROTO_UALINK);
    end

    // Protocol checkers
    if (enable_pcie_gen5 || enable_pcie_gen6)
      pcie_chk = pcie_protocol_checker::type_id::create("pcie_chk", this);
    if (enable_cxl20 || enable_cxl30)
      cxl_chk = cxl_protocol_checker::type_id::create("cxl_chk", this);
    if (enable_ucie)
      ucie_chk = ucie_protocol_checker::type_id::create("ucie_chk", this);
    if (enable_ualink)
      ualink_chk = ualink_protocol_checker::type_id::create("ualink_chk", this);

    sb     = mp_scoreboard::type_id::create("sb", this);
    e2e_sb = mp_e2e_scoreboard::type_id::create("e2e_sb", this);

    pcie_cov  = mp_coverage_model::type_id::create("pcie_cov", this);
    cxl_cov   = mp_coverage_model::type_id::create("cxl_cov", this);
    ucie_cov  = mp_coverage_model::type_id::create("ucie_cov", this);
    ualink_cov = mp_coverage_model::type_id::create("ualink_cov", this);
  endfunction

  function void connect_phase(uvm_phase phase);
    super.connect_phase(phase);

    // Connect protocol checkers to interfaces
    if (pcie_chk != null) begin
      if (pcie_gen5_agent != null)
        uvm_config_db#(virtual mp_vip_if)::set(pcie_chk, "", "vif", pcie_gen5_agent.mon.vif);
      else if (pcie_gen6_agent != null)
        uvm_config_db#(virtual mp_vip_if)::set(pcie_chk, "", "vif", pcie_gen6_agent.mon.vif);
      uvm_config_db#(protocol_e)::set(pcie_chk, "", "protocol", PROTO_PCIE_GEN5);
    end
    if (cxl_chk != null) begin
      if (cxl20_agent != null)
        uvm_config_db#(virtual mp_vip_if)::set(cxl_chk, "", "vif", cxl20_agent.mon.vif);
      else if (cxl30_agent != null)
        uvm_config_db#(virtual mp_vip_if)::set(cxl_chk, "", "vif", cxl30_agent.mon.vif);
      uvm_config_db#(protocol_e)::set(cxl_chk, "", "protocol", PROTO_CXL_20);
    end
    if (ucie_chk != null && ucie_agent != null)
      uvm_config_db#(virtual mp_vip_if)::set(ucie_chk, "", "vif", ucie_agent.mon.vif);
    if (ualink_chk != null && ualink_agent != null)
      uvm_config_db#(virtual mp_vip_if)::set(ualink_chk, "", "vif", ualink_agent.mon.vif);

    if (pcie_gen5_agent != null && pcie_gen5_agent.mon != null) begin
      pcie_gen5_agent.mon.analysis_port.connect(sb.analysis_imp);
      pcie_gen5_agent.mon.cov_model = pcie_cov;
    end
    if (pcie_gen6_agent != null && pcie_gen6_agent.mon != null) begin
      pcie_gen6_agent.mon.analysis_port.connect(sb.analysis_imp);
      pcie_gen6_agent.mon.cov_model = pcie_cov;
    end
    if (cxl20_agent != null && cxl20_agent.mon != null) begin
      cxl20_agent.mon.analysis_port.connect(sb.analysis_imp);
      cxl20_agent.mon.cov_model = cxl_cov;
    end
    if (cxl30_agent != null && cxl30_agent.mon != null) begin
      cxl30_agent.mon.analysis_port.connect(sb.analysis_imp);
      cxl30_agent.mon.cov_model = cxl_cov;
    end
    if (ucie_agent != null && ucie_agent.mon != null) begin
      ucie_agent.mon.analysis_port.connect(sb.analysis_imp);
      ucie_agent.mon.cov_model = ucie_cov;
    end
    if (ualink_agent != null && ualink_agent.mon != null) begin
      ualink_agent.mon.analysis_port.connect(sb.analysis_imp);
      ualink_agent.mon.cov_model = ualink_cov;
    end

    // End-to-end scoreboard connections: driver=expected, monitor=observed
    if (pcie_gen5_agent != null && pcie_gen5_agent.drv != null) begin
      pcie_gen5_agent.drv.drv_ap.connect(e2e_sb.exp_ap);
      pcie_gen5_agent.mon.analysis_port.connect(e2e_sb.obs_ap);
    end
    if (pcie_gen6_agent != null && pcie_gen6_agent.drv != null) begin
      pcie_gen6_agent.drv.drv_ap.connect(e2e_sb.exp_ap);
      pcie_gen6_agent.mon.analysis_port.connect(e2e_sb.obs_ap);
    end
    if (cxl20_agent != null && cxl20_agent.drv != null) begin
      cxl20_agent.drv.drv_ap.connect(e2e_sb.exp_ap);
      cxl20_agent.mon.analysis_port.connect(e2e_sb.obs_ap);
    end
    if (cxl30_agent != null && cxl30_agent.drv != null) begin
      cxl30_agent.drv.drv_ap.connect(e2e_sb.exp_ap);
      cxl30_agent.mon.analysis_port.connect(e2e_sb.obs_ap);
    end
    if (ucie_agent != null && ucie_agent.drv != null) begin
      ucie_agent.drv.drv_ap.connect(e2e_sb.exp_ap);
      ucie_agent.mon.analysis_port.connect(e2e_sb.obs_ap);
    end
    if (ualink_agent != null && ualink_agent.drv != null) begin
      ualink_agent.drv.drv_ap.connect(e2e_sb.exp_ap);
      ualink_agent.mon.analysis_port.connect(e2e_sb.obs_ap);
    end
  endfunction

  function void report_phase(uvm_phase phase);
    super.report_phase(phase);
    `uvm_info("ENV_REPORT", "==========================================", UVM_LOW)
    `uvm_info("ENV_REPORT", "Multi-Protocol VIP Regression Complete", UVM_LOW)
    `uvm_info("ENV_REPORT", "==========================================", UVM_LOW)
    if (pcie_cov != null)
      `uvm_info("COVERAGE", $sformatf("PCIe Coverage: %0.2f%%", pcie_cov.get_coverage()), UVM_LOW)
    if (cxl_cov != null)
      `uvm_info("COVERAGE", $sformatf("CXL Coverage: %0.2f%%", cxl_cov.get_coverage()), UVM_LOW)
    if (ucie_cov != null)
      `uvm_info("COVERAGE", $sformatf("UCIe Coverage: %0.2f%%", ucie_cov.get_coverage()), UVM_LOW)
    if (ualink_cov != null)
      `uvm_info("COVERAGE", $sformatf("UALink Coverage: %0.2f%%", ualink_cov.get_coverage()), UVM_LOW)
  endfunction
endclass
`endif
