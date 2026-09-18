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
// can_crc.svh -- CAN CRC-15 (polynomial 0x4599) helper + frame bit utilities
`ifndef CAN_CRC_SVH
`define CAN_CRC_SVH

// CAN CRC-15: x^15 + x^14 + x^10 + x^8 + x^7 + x^4 + x^3 + 1, init 0.
// bits are processed MSB-first exactly as they appear on the bus
// (SOF .. end of data field, destuffed).
function automatic bit [14:0] can_crc15(const ref bit bits[$]);
  bit [14:0] crc = 15'h0;
  foreach (bits[i]) begin
    bit nxt = bits[i] ^ crc[14];
    crc = {crc[13:0], 1'b0};
    if (nxt) crc = crc ^ 15'h4599;
  end
  return crc;
endfunction

`endif
