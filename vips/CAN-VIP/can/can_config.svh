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
// can_config.svh

class can_config extends uvm_object;
  `uvm_object_utils(can_config)
  bit enable_checker  = 1;
  bit enable_coverage = 1;
  bit can_fd_enabled  = 1;
  bit can_tt_enabled  = 1;
  int max_data_len    = 64;   // CAN FD max
  int std_id_mask     = 11'h7FF;
  int ext_id_mask     = 29'h1FFFFFFF;
  bit [15:0] bit_rate = 500;  // kbps
  bit [15:0] fd_bit_rate = 2000; // kbps (CAN FD data phase)
  function new(string name = "can_config");
    super.new(name);
  endfunction
endclass
