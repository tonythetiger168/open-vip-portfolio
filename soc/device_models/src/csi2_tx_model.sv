// SPDX-License-Identifier: Apache-2.0
// ============================================================================
// csi2_tx_model: a MIPI CSI-2 camera sensor transmitter for a SoC bench, with
// no UVM agent. It drives a CSI-2 receiver's serial lane pins (CSI_2_top in
// open-ip-portfolio: rx_valid / rx_bit, one bit per clk, LSB first) with
// FRAMES frames (0 = until en drops), each sent as one HS burst per packet:
//   FS (short, DT 0x00, data = frame number 1, 2, ...)
//   LINES long packets of WIDTH payload bytes (VC, DT; default RAW8 0x2A),
//     payload byte j of line l (1..LINES) of frame f = csi2_tx_pixel(f, l, j)
//   FE (short, DT 0x01, same frame number)
// Every burst: LEAD HS-zero bits, the 0xB8 sync byte, DI, WC (low byte
// first), the ECC byte (CSI-2 Hamming code, bits 7:6 zero), for long
// packets the payload and the CRC-16 (poly 0x1021 reflected, init 0xFFFF,
// low byte first), then TRAIL bits of the inverse of the last bit; rx_valid
// is low for GAP clocks between bursts. done rises after the last FE.
// ============================================================================
module csi2_tx_model #(
  parameter int         FRAMES = 2,      // frames to send, 0 = no limit
  parameter int         LINES  = 4,      // long packets per frame
  parameter int         WIDTH  = 16,     // payload bytes per line (WC)
  parameter logic [1:0] VC     = 2'd0,
  parameter logic [5:0] DT     = 6'h2A,  // RAW8
  parameter int         LEAD   = 8,      // HS-zero bits before the sync byte
  parameter int         TRAIL  = 8,      // trailer bits after the packet
  parameter int         GAP    = 32,     // clocks with rx_valid low between bursts
  parameter int         START  = 16      // clocks after reset (and en) before the first burst
) (
  input  logic        clk,
  input  logic        rst_n,
  input  logic        en,                // sending starts / continues while high
  output logic        rx_valid,
  output logic        rx_bit,
  output logic [15:0] frames_sent,
  output logic        done
);
  function automatic logic [5:0] ecc6(input logic [23:0] d);
    logic [5:0] e;
    e[0] = d[0]^d[1]^d[2]^d[4]^d[5]^d[7]^d[10]^d[11]^d[13]^d[16]^d[20]^d[21]^d[22]^d[23];
    e[1] = d[0]^d[1]^d[3]^d[4]^d[6]^d[8]^d[10]^d[12]^d[14]^d[17]^d[20]^d[21]^d[22]^d[23];
    e[2] = d[0]^d[2]^d[3]^d[5]^d[6]^d[9]^d[11]^d[12]^d[15]^d[18]^d[20]^d[21]^d[22];
    e[3] = d[1]^d[2]^d[3]^d[7]^d[8]^d[9]^d[13]^d[14]^d[15]^d[19]^d[20]^d[21]^d[23];
    e[4] = d[4]^d[5]^d[6]^d[7]^d[8]^d[9]^d[16]^d[17]^d[18]^d[19]^d[20]^d[22]^d[23];
    e[5] = d[10]^d[11]^d[12]^d[13]^d[14]^d[15]^d[16]^d[17]^d[18]^d[19]^d[21]^d[22]^d[23];
    return e;
  endfunction
  function automatic logic [15:0] crc16(input logic [15:0] c, input logic [7:0] d);
    logic [15:0] v = c ^ {8'h00, d};
    for (int k = 0; k < 8; k++) v = v[0] ? (v >> 1) ^ 16'h8408 : (v >> 1);
    return v;
  endfunction

  localparam logic [2:0] S_START = 3'd0, S_LEAD = 3'd1, S_BYTE = 3'd2, S_TRAIL = 3'd3, S_GAP = 3'd4, S_DONE = 3'd5;
  logic [2:0]  st;
  logic [31:0] cnt;
  logic [31:0] pk;        // 0 FS, 1..LINES lines, LINES + 1 FE
  logic [31:0] bi;        // byte of the packet
  logic [2:0]  bn;        // bit of the byte
  logic [7:0]  cur;
  logic [15:0] crc;
  logic        lastb;

  wire         short_p = (pk == 0) || (pk == LINES + 1);
  wire  [7:0]  di      = {VC, (pk == 0) ? 6'h00 : (pk == LINES + 1) ? 6'h01 : DT};
  wire  [15:0] wc      = short_p ? frames_sent + 16'd1 : 16'(WIDTH);
  wire  [31:0] nbytes  = short_p ? 32'd5 : 32'(WIDTH) + 32'd7;

  function automatic logic [7:0] byte_at(input logic [31:0] i);
    if (i == 0) return 8'hB8;
    if (i == 1) return di;
    if (i == 2) return wc[7:0];
    if (i == 3) return wc[15:8];
    if (i == 4) return {2'b00, ecc6({wc, di})};
    if (i < 32'(WIDTH) + 5) return csi2_tx_pixel(frames_sent + 16'd1, pk[15:0], i[15:0] - 16'd5);
    if (i == 32'(WIDTH) + 5) return crc[7:0];
    return crc[15:8];
  endfunction

  always_ff @(posedge clk or negedge rst_n) begin
    if (!rst_n) begin
      st <= S_START; cnt <= '0; pk <= '0; bi <= '0; bn <= '0; cur <= '0; crc <= 16'hFFFF; lastb <= 1'b0;
      rx_valid <= 1'b0; rx_bit <= 1'b0; frames_sent <= '0; done <= 1'b0;
    end else begin
      case (st)
        S_START: begin
          rx_valid <= 1'b0; rx_bit <= 1'b0;
          if (!en) cnt <= '0;
          else if (cnt == START) begin st <= S_LEAD; cnt <= '0; end
          else cnt <= cnt + 1;
        end
        S_LEAD: begin
          rx_valid <= 1'b1; rx_bit <= 1'b0;
          if (cnt + 1 >= LEAD) begin st <= S_BYTE; bi <= '0; bn <= '0; cnt <= '0; end
          else cnt <= cnt + 1;
        end
        S_BYTE: begin : sb
          logic [7:0] b;
          if (bn == 0) begin
            b = byte_at(bi);
            cur <= b;
            if (bi == 1) crc <= 16'hFFFF;
            else if (bi >= 5 && bi < 32'(WIDTH) + 5 && !short_p) crc <= crc16(crc, b);
          end else b = cur;
          rx_valid <= 1'b1; rx_bit <= b[bn]; lastb <= b[bn];
          bn <= bn + 3'd1;
          if (bn == 3'd7) begin
            bi <= bi + 1;
            if (bi + 1 == nbytes) begin st <= S_TRAIL; cnt <= '0; end
          end
        end
        S_TRAIL: begin
          rx_valid <= 1'b1; rx_bit <= !lastb;
          if (cnt + 1 >= TRAIL) begin st <= S_GAP; cnt <= '0; end
          else cnt <= cnt + 1;
        end
        S_GAP: begin
          rx_valid <= 1'b0; rx_bit <= 1'b0;
          if (cnt + 1 >= GAP && en) begin
            cnt <= '0;
            if (pk == LINES + 1) begin
              pk <= '0;
              frames_sent <= frames_sent + 16'd1;
              if (FRAMES != 0 && frames_sent + 1 == FRAMES) begin st <= S_DONE; done <= 1'b1; end
              else st <= S_LEAD;
            end else begin pk <= pk + 1; st <= S_LEAD; end
          end else if (cnt + 1 < GAP) cnt <= cnt + 1;
        end
        default: begin rx_valid <= 1'b0; rx_bit <= 1'b0; end
      endcase
    end
  end

  // the test pattern: frame f (1, 2, ...), line l (1..LINES), byte j (0..WIDTH-1)
  function automatic logic [7:0] csi2_tx_pixel(input logic [15:0] f, input logic [15:0] l, input logic [15:0] j);
    return 8'(j) ^ 8'(l * 16'd37) ^ 8'(f * 16'd101);
  endfunction
endmodule
