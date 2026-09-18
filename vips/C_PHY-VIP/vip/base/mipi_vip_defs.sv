// Copyright 2026 VIP Portfolio Contributors
// SPDX-License-Identifier: Apache-2.0
//
// mipi_vip_defs.sv -- compile-order anchor for single-unit compilation
// The package and the protocol-checker classes must be elaborated before
// the environment and the tests. Every included file carries its own
// include guard, so standalone compilation of the individual files later
// in the file list is a no-op.

`ifndef MIPI_VIP_DEFS_SV
`define MIPI_VIP_DEFS_SV

`include "mipi_vip_pkg.sv"
import mipi_vip_pkg::*;

`include "cphy_protocol_checker.sv"
`include "cse_protocol_checker.sv"
`include "csi2_protocol_checker.sv"
`include "digrf_protocol_checker.sv"
`include "dphy_protocol_checker.sv"
`include "dsi_protocol_checker.sv"
`include "hsi_protocol_checker.sv"
`include "mphy_protocol_checker.sv"
`include "unipro_protocol_checker.sv"

`endif
