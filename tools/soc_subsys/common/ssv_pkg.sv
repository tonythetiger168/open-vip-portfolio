// Copyright 2026 VIP Portfolio Contributors
// SPDX-License-Identifier: Apache-2.0
//
// ssv_pkg.sv -- shared verification components for the open-ip-portfolio
// SoC subsystem IPs (<P>_apb APB4 register wrapper + AXI4 manager port):
//   ssv_mem.svh          sparse memory (AXI front door + test back door)
//   ssv_apb.svh          APB4 requester agent + RAL adapter
//   ssv_axi.svh          AXI4 manager-port verification: subordinate,
//                        monitor with transaction rules, coverage, agent
//   ssv_axi_mgr_bfm.svh  AXI4 manager BFM with rule-violation injection
//   ssv_util.svh         report catcher for expected errors
//   ssv_env.svh          env (APB agent + RAL + AXI4 manager-port agent) and
//                        the base test every subsystem test extends
// Every VIP of the family ships an identical copy of this package
// (tools/gen_soc_subsys_vips.py in open-vip-portfolio).

package ssv_pkg;
  import uvm_pkg::*;
  `include "uvm_macros.svh"

  `include "ssv_mem.svh"
  `include "ssv_apb.svh"
  `include "ssv_axi.svh"
  `include "ssv_axi_mgr_bfm.svh"
  `include "ssv_util.svh"
  `include "ssv_env.svh"
endpackage
