// SPDX-License-Identifier: Apache-2.0
// ============================================================================
// i2s_codec_model: an I2S audio codec (ADC + DAC) as the bus clock master for
// a SoC bench, with no UVM agent. Pins match I2S_top in open-ip-portfolio
// (the SoC's I2S port is the slave): this model drives bclk, lrck and sdin
// and samples sdout.
//  - bclk: DIV clocks per period (even; I2S_top needs 8 or more), low for the
//    first half. lrck (0 = left, 1 = right) and sdin change on the bclk
//    falling edge; Philips timing: the MSB of a word follows one bclk after
//    the lrck change, DW-bit words in SLOT-bit channel slots (bits after the
//    LSB are 0).
//  - ADC: the words of frame n (0, 1, ...) are i2s_codec_adc(n, 0) (left)
//    and i2s_codec_adc(n, 1) (right).
//  - DAC: sdout is sampled on every bclk rise with the same timing; when a
//    frame's right word is complete, dac_valid pulses for one clk with both
//    words (dac_frame = that frame's number).
//  - lrck idles high (right) from reset, so frame 0 starts with an lrck
//    change that a slave can lock to.
//  - FRAMES frames, then bclk stops high (0 = no limit); en low holds bclk.
// ============================================================================
module i2s_codec_model #(
  parameter int DW     = 16,
  parameter int SLOT   = 32,     // bits per channel slot, >= DW
  parameter int DIV    = 8,      // clocks per bclk period, even
  parameter int FRAMES = 0
) (
  input  logic          clk,
  input  logic          rst_n,
  input  logic          en,
  output logic          bclk,
  output logic          lrck,
  output logic          sdin,
  input  logic          sdout,
  output logic          dac_valid,
  output logic [DW-1:0] dac_left,
  output logic [DW-1:0] dac_right,
  output logic [31:0]   dac_frame,
  output logic          done
);
  localparam int FB = 2 * SLOT;            // bits per frame

  logic [31:0]   ph, gc;                   // clock in the bclk period, bit since start
  logic [DW-1:0] sh, lcap;

  // bit position of a global bit (delayed by one for Philips timing)
  function automatic logic adc_bit(input logic [31:0] g);
    logic [31:0] d, slot, pos;
    logic [DW-1:0] w;
    if (g == 0) return 1'b0;
    d = g - 1; slot = d / SLOT; pos = d % SLOT;
    if (pos >= DW) return 1'b0;
    w = i2s_codec_adc(slot / 2, slot[0]);
    return w[DW - 1 - pos];
  endfunction

  always_ff @(posedge clk or negedge rst_n) begin
    if (!rst_n) begin
      ph <= '0; gc <= '0; bclk <= 1'b1; lrck <= 1'b1; sdin <= 1'b0; sh <= '0; lcap <= '0;   // lrck: right idle
      dac_valid <= 1'b0; dac_left <= '0; dac_right <= '0; dac_frame <= '0; done <= 1'b0;
    end else begin
      dac_valid <= 1'b0;
      if (FRAMES != 0 && gc == FB * FRAMES + 1 && ph == 0) begin bclk <= 1'b1; done <= 1'b1; end
      else if (en || ph != 0) begin
        if (ph == 0) begin                       // falling edge: the bit gc
          bclk <= 1'b0;
          lrck <= (gc / SLOT) % 2 == 1;
          sdin <= adc_bit(gc);
        end
        if (ph == DIV / 2) begin : rise          // rising edge: sample sdout
          logic [31:0] d, slot, pos;
          logic [DW-1:0] w;
          bclk <= 1'b1;
          if (gc != 0) begin
            d = gc - 1; slot = d / SLOT; pos = d % SLOT;
            if (pos < DW) begin
              w = {sh[DW-2:0], sdout};
              sh <= w;
              if (pos == DW - 1) begin
                if (!slot[0]) lcap <= w;
                else begin dac_valid <= 1'b1; dac_left <= lcap; dac_right <= w; dac_frame <= slot / 2; end
              end
            end
          end
        end
        if (ph == DIV - 1) begin ph <= '0; gc <= gc + 1; end
        else ph <= ph + 1;
      end
    end
  end

  // the ADC words: frame n, channel ch (0 left, 1 right)
  function automatic logic [DW-1:0] i2s_codec_adc(input logic [31:0] n, input logic ch);
    logic [31:0] x = (n * 32'h0001_0123) ^ (ch ? 32'h0000_A55A : 32'h0000_3C3C);
    return x[DW-1:0];
  endfunction
endmodule
