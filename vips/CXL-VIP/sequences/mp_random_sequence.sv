// Copyright 2026 VIP Portfolio Contributors
// SPDX-License-Identifier: Apache-2.0
//
//============================================================================
// Multi-Protocol Random Sequence
// Generates random transactions for a target protocol
//============================================================================
`ifndef MP_RANDOM_SEQUENCE_SV
`define MP_RANDOM_SEQUENCE_SV
class mp_random_sequence extends mp_base_sequence;
  `uvm_object_utils(mp_random_sequence)

  rand bit enable_pcie;
  rand bit enable_cxl;
  rand bit enable_ucie;
  rand bit enable_ualink;

  constraint c_protocol_dist {
    if (enable_pcie) target_protocol inside {PROTO_PCIE_GEN5, PROTO_PCIE_GEN6};
    if (enable_cxl)  target_protocol inside {PROTO_CXL_20, PROTO_CXL_30};
    if (enable_ucie) target_protocol == PROTO_UCIE;
    if (enable_ualink) target_protocol == PROTO_UALINK;
  }

  function new(string name = "mp_random_sequence");
    super.new(name);
  endfunction
endclass
`endif
