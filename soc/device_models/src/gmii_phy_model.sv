// SPDX-License-Identifier: Apache-2.0
// ============================================================================
// gmii_phy_model: the PHY / link partner end of a MAC's GMII for a SoC bench,
// with no UVM agent. Pins match Ethernet_top in open-ip-portfolio: the MAC
// drives gtxd / gtx_en / gtx_er, this model drives grxd / grx_dv / grx_er.
// A byte time is DIV + 1 clocks (set DIV = the MAC's cfg_div).
//  - From the MAC: each frame (any number of 0x55, the SFD 0xD5, the frame,
//    the FCS) is checked; rx_good / rx_bad count frames with a good / bad FCS
//    (gtx_er in a frame counts as bad).
//  - Originate: GEN_N frames after reset, DA = DST_MAC, SA = PHY_MAC, a
//    length field of GEN_LEN, payload byte i of frame k (0, 1, ...) =
//    8'(i) ^ 8'(k * 29); preamble 7 x 0x55, SFD, FCS, IFG idle byte times.
//  - ECHO = 1: every good frame from the MAC is sent back (after the
//    originated ones) with DA and SA swapped and a new FCS, so a frame the
//    SoC sends to PHY_MAC returns to the SoC's own address. A frame that
//    arrives while the previous echo is waiting or being sent is dropped
//    (echo_drop counts them).
// ============================================================================
module gmii_phy_model #(
  parameter int          DIV     = 1,
  parameter bit          ECHO    = 1'b1,
  parameter logic [47:0] PHY_MAC = 48'h02_00_5E_10_00_99,
  parameter logic [47:0] DST_MAC = 48'h02_00_5E_10_00_01,
  parameter int          GEN_N   = 0,
  parameter int          GEN_LEN = 64,     // 46 .. 1500
  parameter int          IFG     = 12,     // idle byte times after each frame
  parameter int          START   = 16,     // byte times after reset before the first frame
  parameter int          MAXF    = 1536    // largest frame kept for the echo (DA .. FCS)
) (
  input  logic        clk,
  input  logic        rst_n,
  input  logic [7:0]  gtxd,
  input  logic        gtx_en,
  input  logic        gtx_er,
  output logic [7:0]  grxd,
  output logic        grx_dv,
  output logic        grx_er,
  output logic [15:0] rx_good,
  output logic [15:0] rx_bad,
  output logic [15:0] tx_frames,
  output logic [15:0] echo_drop
);
  function automatic logic [31:0] crc32(input logic [31:0] c, input logic [7:0] d);
    for (int i = 0; i < 8; i++) c = (c[0] ^ d[i]) ? (c >> 1) ^ 32'hEDB88320 : c >> 1;
    return c;
  endfunction

  // ---------------- from the MAC ----------------
  logic [7:0]  rbuf [0:MAXF-1];
  logic [7:0]  ebuf [0:MAXF-1];
  logic [1:0]  rs;                 // 0 idle, 1 preamble, 2 frame
  logic [31:0] rph, rn, en_len;
  logic [31:0] rcrc;
  logic        rerr, epend;
  logic        tx_echo_take;
  wire         echo_busy;

  always_ff @(posedge clk or negedge rst_n) begin
    if (!rst_n) begin
      rs <= '0; rph <= '0; rn <= '0; rcrc <= '1; rerr <= 1'b0; epend <= 1'b0; en_len <= '0;
      rx_good <= '0; rx_bad <= '0; echo_drop <= '0;
    end else begin
      if (tx_echo_take) epend <= 1'b0;
      if (rs == 0) begin
        if (gtx_en) begin           // the first clock of a byte time
          rph <= '0;
          if (gtxd == 8'hD5) begin rs <= 2'd2; rn <= '0; rcrc <= '1; end
          else rs <= 2'd1;
          rerr <= gtx_er;
        end
      end else if (rph != DIV) rph <= rph + 1;
      else begin
        rph <= '0;
        if (!gtx_en) begin
          if (rs == 2'd2) begin
            if (!rerr && rn >= 32'd18 && rcrc == 32'hDEBB20E3) begin
              rx_good <= rx_good + 16'd1;
              if (ECHO) begin
                if (epend || echo_busy) echo_drop <= echo_drop + 16'd1;   // ebuf still in use
                else begin
                  for (int i = 0; i < MAXF; i++) ebuf[i] <= rbuf[i];
                  en_len <= rn - 4; epend <= 1'b1;
                end
              end
            end else rx_bad <= rx_bad + 16'd1;
          end
          rs <= '0;
        end else begin
          if (gtx_er) rerr <= 1'b1;
          if (rs == 2'd1) begin
            if (gtxd == 8'hD5) begin rs <= 2'd2; rn <= '0; rcrc <= '1; end
            else if (gtxd != 8'h55) rerr <= 1'b1;
          end else begin
            if (rn < MAXF) rbuf[rn] <= gtxd;
            rn <= rn + 1;
            rcrc <= crc32(rcrc, gtxd);
          end
        end
      end
    end
  end

  // ---------------- to the MAC ----------------
  localparam logic [2:0] T_WAIT = 3'd0, T_PRE = 3'd1, T_DATA = 3'd2, T_FCS = 3'd3, T_IFG = 3'd4;
  logic [2:0]  ts;
  logic [31:0] tph, ti, tlen, gk;
  logic        tgen;
  logic [31:0] tcrc;

  function automatic logic [7:0] gen_byte(input logic [31:0] k, input logic [31:0] i);
    if (i < 6)  return DST_MAC[8 * (5 - i) +: 8];
    if (i < 12) return PHY_MAC[8 * (11 - i) +: 8];
    if (i == 12) return 8'(GEN_LEN >> 8);
    if (i == 13) return 8'(GEN_LEN);
    return 8'(i - 14) ^ 8'(k * 29);
  endfunction
  function automatic logic [7:0] echo_byte(input logic [31:0] i);
    if (i < 6)  return ebuf[i + 6];
    if (i < 12) return ebuf[i - 6];
    return ebuf[i];
  endfunction
  wire [7:0] tbyte = tgen ? gen_byte(gk, ti) : echo_byte(ti);
  assign echo_busy = (ts != T_WAIT) && !tgen;

  always_ff @(posedge clk or negedge rst_n) begin
    if (!rst_n) begin
      ts <= T_WAIT; tph <= '0; ti <= '0; tlen <= '0; gk <= '0; tgen <= 1'b0; tcrc <= '1;
      grxd <= '0; grx_dv <= 1'b0; grx_er <= 1'b0; tx_frames <= '0; tx_echo_take <= 1'b0;
    end else begin
      tx_echo_take <= 1'b0;
      if (tph != DIV) tph <= tph + 1;
      else begin
        tph <= '0;
        grx_er <= 1'b0;
        case (ts)
          T_WAIT: begin
            grx_dv <= 1'b0; grxd <= '0;
            if (ti + 1 < START) ti <= ti + 1;
            else if (gk < GEN_N) begin ts <= T_PRE; ti <= '0; tgen <= 1'b1; tlen <= 32'(GEN_LEN) + 14; end
            else if (epend && !tx_echo_take) begin
              ts <= T_PRE; ti <= '0; tgen <= 1'b0; tlen <= en_len; tx_echo_take <= 1'b1;
            end
          end
          T_PRE: begin
            grx_dv <= 1'b1; grxd <= (ti == 7) ? 8'hD5 : 8'h55;
            if (ti == 7) begin ts <= T_DATA; ti <= '0; tcrc <= '1; end else ti <= ti + 1;
          end
          T_DATA: begin
            grx_dv <= 1'b1; grxd <= tbyte; tcrc <= crc32(tcrc, tbyte);
            if (ti + 1 == tlen) begin ts <= T_FCS; ti <= '0; end else ti <= ti + 1;
          end
          T_FCS: begin
            grx_dv <= 1'b1; grxd <= ~tcrc[8 * ti[1:0] +: 8];
            if (ti == 3) begin ts <= T_IFG; ti <= '0; tx_frames <= tx_frames + 16'd1; if (tgen) gk <= gk + 1; end
            else ti <= ti + 1;
          end
          default: begin                 // T_IFG
            grx_dv <= 1'b0; grxd <= '0;
            if (ti + 1 >= IFG) begin ts <= T_WAIT; ti <= START; end else ti <= ti + 1;
          end
        endcase
      end
    end
  end
endmodule
