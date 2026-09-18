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
// can_pkg.sv

package can_pkg;
  import uvm_pkg::*;
  `include "uvm_macros.svh"
  import common_pkg::*;
  `include "can_crc.svh"
  `include "can_config.svh"
  `include "can_transaction.svh"
  `include "can_sequencer.svh"
  `include "can_driver.svh"
  `include "can_monitor.svh"
  `include "can_checker.svh"
  `include "can_coverage.svh"
  `include "can_agent.svh"
  `include "can_sequences.svh"
endpackage
