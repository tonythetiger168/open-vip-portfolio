# AMBA CHI (Issue E opcodes) request node agent against a Home Node with
# memory. Channels are split into fields (no packed flits; CHI_H-UVM-VIP
# covers the Issue H flit layouts):
#   TXREQ  req_*   RN -> HN  Opcode, TxnID, Addr, Size, AllowRetry, PCrdType, ExpCompAck
#   TXDAT  wdat_*  RN -> HN  NonCopyBackWrData / CopyBackWrData, TxnID = DBID, DataID, BE, Resp
#   TXRSP  srsp_*  RN -> HN  CompAck, TxnID = DBID
#   RXRSP  crsp_*  HN -> RN  RetryAck, PCrdGrant, Comp, CompDBIDResp
#   RXDAT  rdat_*  HN -> RN  CompData, four 128-bit beats (DataID 0..3)
# Every channel uses link-layer credits: a flit may only be sent while the
# sender holds an L-credit from the receiver (*_lcrdv pulses, one credit
# each); the receiver returns a credit for every flit it consumes.
#
# tb/top_tb.sv chi_model is the HN-F with a 4 KB memory (64 lines):
#   - grants 2 L-credits on each inbound channel after reset; a flit without
#     a credit is dropped and flagged (proto_code 1)
#   - two request trackers; DBID = tracker index. A request that finds no
#     free tracker and has AllowRetry gets RetryAck (PCrdType 1); a PCrdGrant
#     follows when a tracker frees, which reserves it for the retried request
#     (AllowRetry 0, PCrdType 1)
#   - ReadNoSnp / ReadOnce: CompData I; ReadClean / ReadShared: CompData SC;
#     ReadUnique: CompData UC (CompAck required for the last three)
#   - CleanShared / CleanInvalid / MakeInvalid / Evict: Comp I; CleanUnique /
#     MakeUnique: Comp UC, then CompAck
#   - WriteNoSnp / WriteUnique (Full or Ptl, NonCopyBackWrData with BE),
#     WriteBackFull / WriteCleanFull / WriteEvictFull (CopyBackWrData; resp I
#     means the line was lost and nothing is written): CompDBIDResp, then
#     four data beats with TxnID = DBID
#   - an address above 4 KB: CompData with RespErr DERR (zero data), Comp /
#     CompDBIDResp with NDERR, no memory change
#   - protocol errors answered with Comp NDERR (DBID FFF, no tracker) and
#     proto_err / proto_code: 2 TxnID still outstanding, 3 Size not 64 bytes
#     or address not line aligned, 4 ExpCompAck missing where required,
#     5 AllowRetry 0 without a granted P-credit, 7 unsupported opcode;
#     6: write data or CompAck for no waiting tracker (dropped)

DEFS = """
// REQ opcodes (CHI Issue E)
localparam bit [6:0] CHI_READ_SHARED   = 7'h01;
localparam bit [6:0] CHI_READ_CLEAN    = 7'h02;
localparam bit [6:0] CHI_READ_ONCE     = 7'h03;
localparam bit [6:0] CHI_READ_NOSNP    = 7'h04;
localparam bit [6:0] CHI_READ_UNIQUE   = 7'h07;
localparam bit [6:0] CHI_CLEAN_SHARED  = 7'h08;
localparam bit [6:0] CHI_CLEAN_INVALID = 7'h09;
localparam bit [6:0] CHI_MAKE_INVALID  = 7'h0A;
localparam bit [6:0] CHI_CLEAN_UNIQUE  = 7'h0B;
localparam bit [6:0] CHI_MAKE_UNIQUE   = 7'h0C;
localparam bit [6:0] CHI_EVICT         = 7'h0D;
localparam bit [6:0] CHI_WRITE_EVICT_FULL = 7'h15;
localparam bit [6:0] CHI_WRITE_CLEAN_FULL = 7'h17;
localparam bit [6:0] CHI_WRITE_UNIQUE_PTL = 7'h18;
localparam bit [6:0] CHI_WRITE_UNIQUE_FULL = 7'h19;
localparam bit [6:0] CHI_WRITE_BACK_FULL  = 7'h1B;
localparam bit [6:0] CHI_WRITE_NOSNP_PTL  = 7'h1C;
localparam bit [6:0] CHI_WRITE_NOSNP_FULL = 7'h1D;
// RSP opcodes
localparam bit [4:0] CHI_COMP_ACK = 5'h2, CHI_RETRY_ACK = 5'h3, CHI_COMP = 5'h4, CHI_COMP_DBID = 5'h5,
                     CHI_PCRD_GRANT = 5'h7;
// DAT opcodes
localparam bit [3:0] CHI_COPYBACK_WR = 4'h2, CHI_NONCOPYBACK_WR = 4'h3, CHI_COMP_DATA = 4'h4;
// Resp (cache state) and RespErr
localparam bit [2:0] CHI_I = 3'b000, CHI_SC = 3'b001, CHI_UC = 3'b010, CHI_UD_PD = 3'b110;
localparam bit [1:0] CHI_RE_OK = 2'b00, CHI_RE_DERR = 2'b10, CHI_RE_NDERR = 2'b11;

typedef enum bit [2:0] {CHI_X_NONE, CHI_X_SIZE, CHI_X_ALIGN, CHI_X_NOACK, CHI_X_OP, CHI_X_OOR} chi_inj_e;

function automatic bit chi_is_read(bit [6:0] op);
  return op inside {CHI_READ_SHARED, CHI_READ_CLEAN, CHI_READ_ONCE, CHI_READ_NOSNP, CHI_READ_UNIQUE};
endfunction
function automatic bit chi_is_dataless(bit [6:0] op);
  return op inside {CHI_CLEAN_SHARED, CHI_CLEAN_INVALID, CHI_MAKE_INVALID, CHI_CLEAN_UNIQUE, CHI_MAKE_UNIQUE, CHI_EVICT};
endfunction
function automatic bit chi_is_copyback(bit [6:0] op);
  return op inside {CHI_WRITE_EVICT_FULL, CHI_WRITE_CLEAN_FULL, CHI_WRITE_BACK_FULL};
endfunction
function automatic bit chi_is_write(bit [6:0] op);
  return chi_is_copyback(op) || op inside {CHI_WRITE_UNIQUE_PTL, CHI_WRITE_UNIQUE_FULL, CHI_WRITE_NOSNP_PTL,
                                           CHI_WRITE_NOSNP_FULL};
endfunction
function automatic bit chi_is_ptl(bit [6:0] op);
  return op inside {CHI_WRITE_UNIQUE_PTL, CHI_WRITE_NOSNP_PTL};
endfunction
// requests that must set ExpCompAck
function automatic bit chi_needs_ack(bit [6:0] op);
  return op inside {CHI_READ_SHARED, CHI_READ_CLEAN, CHI_READ_UNIQUE, CHI_CLEAN_UNIQUE, CHI_MAKE_UNIQUE};
endfunction
function automatic bit chi_known(bit [6:0] op);
  return chi_is_read(op) || chi_is_dataless(op) || chi_is_write(op);
endfunction
// default memory contents of line l
function automatic bit [511:0] chi_mem_init(int unsigned l);
  bit [511:0] v;
  for (int j = 0; j < 16; j++) v[32*j +: 32] = 32'hC0DE_0000 | (l * 16 + j);
  return v;
endfunction
"""

MODEL = """
module chi_model (
  input  logic         clk,
  input  logic         rst_n,
  input  logic         req_flitv,
  input  logic [6:0]   req_opcode,
  input  logic [11:0]  req_txnid,
  input  logic [43:0]  req_addr,
  input  logic [2:0]   req_size,
  input  logic         req_allowretry,
  input  logic [3:0]   req_pcrdtype,
  input  logic         req_expcompack,
  output logic         req_lcrdv,
  input  logic         wdat_flitv,
  input  logic [3:0]   wdat_opcode,
  input  logic [11:0]  wdat_txnid,
  input  logic [2:0]   wdat_resp,
  input  logic [1:0]   wdat_dataid,
  input  logic [15:0]  wdat_be,
  input  logic [127:0] wdat_data,
  output logic         wdat_lcrdv,
  input  logic         srsp_flitv,
  input  logic [4:0]   srsp_opcode,
  input  logic [11:0]  srsp_txnid,
  output logic         srsp_lcrdv,
  output logic         crsp_flitv,
  output logic [4:0]   crsp_opcode,
  output logic [11:0]  crsp_txnid,
  output logic [11:0]  crsp_dbid,
  output logic [2:0]   crsp_resp,
  output logic [1:0]   crsp_resperr,
  output logic [3:0]   crsp_pcrdtype,
  input  logic         crsp_lcrdv,
  output logic         rdat_flitv,
  output logic [3:0]   rdat_opcode,
  output logic [11:0]  rdat_txnid,
  output logic [11:0]  rdat_dbid,
  output logic [2:0]   rdat_resp,
  output logic [1:0]   rdat_resperr,
  output logic [1:0]   rdat_dataid,
  output logic [127:0] rdat_data,
  input  logic         rdat_lcrdv,
  output logic         proto_err,
  output logic [2:0]   proto_code
);
  localparam int TRK = 2, NCR = 2, QD = 8;
  localparam logic [2:0] T_FREE = 3'd0, T_RD = 3'd1, T_RACK = 3'd2, T_WD = 3'd3, T_DACK = 3'd4;

  logic [511:0] mem [0:63];
  initial for (int l = 0; l < 64; l++) for (int j = 0; j < 16; j++) mem[l][32*j +: 32] = 32'hC0DE_0000 | (l * 16 + j);

  // trackers
  logic [2:0]  t_st   [0:TRK-1];
  logic [11:0] t_txn  [0:TRK-1];
  logic [5:0]  t_line [0:TRK-1];
  logic        t_oor  [0:TRK-1];
  logic        t_ack  [0:TRK-1];
  logic [2:0]  t_resp [0:TRK-1];
  logic [6:0]  t_op   [0:TRK-1];
  logic [1:0]  t_beat [0:TRK-1];
  logic [3:0]  t_mask [0:TRK-1];
  // L-credits: held by the RN on our inbound channels, to grant, held by us on the outbound ones
  logic [2:0]  rn_req, rn_wdat, rn_srsp, g_req, g_wdat, g_srsp;
  logic [3:0]  cr_crsp, cr_rdat;
  // P-credits
  logic [2:0]  pend_grant, resv;
  // RXRSP queue
  logic [4:0]  q_op  [0:QD-1];
  logic [11:0] q_txn [0:QD-1];
  logic [11:0] q_dbid[0:QD-1];
  logic [2:0]  q_resp[0:QD-1];
  logic [1:0]  q_err [0:QD-1];
  logic [3:0]  q_pt  [0:QD-1];
  logic [3:0]  q_n;

  // working copies (blocking)
  logic [3:0]  n;
  logic [2:0]  ec, nfree, rd_i, pg, rv, fc;
  logic        found, sent, gr_req, gr_wdat, gr_srsp, req_ok, wdat_ok, srsp_ok;
  logic [11:0] di;
  integer      i, k;

  task automatic push(input logic [4:0] op, input logic [11:0] txn, input logic [11:0] dbid, input logic [2:0] rs,
                      input logic [1:0] er, input logic [3:0] pt);
    q_op[n] <= op; q_txn[n] <= txn; q_dbid[n] <= dbid; q_resp[n] <= rs; q_err[n] <= er; q_pt[n] <= pt;
    n = n + 4'd1;
  endtask

  always_ff @(posedge clk or negedge rst_n) begin
    if (!rst_n) begin
      for (i = 0; i < TRK; i++) begin
        t_st[i] <= T_FREE; t_txn[i] <= 12'h0; t_line[i] <= 6'h0; t_oor[i] <= 1'b0; t_ack[i] <= 1'b0;
        t_resp[i] <= 3'h0; t_op[i] <= 7'h0; t_beat[i] <= 2'h0; t_mask[i] <= 4'h0;
      end
      rn_req <= 3'd0; rn_wdat <= 3'd0; rn_srsp <= 3'd0; g_req <= NCR; g_wdat <= NCR; g_srsp <= NCR;
      cr_crsp <= 4'd0; cr_rdat <= 4'd0; pend_grant <= 3'd0; resv <= 3'd0; q_n <= 4'd0;
      req_lcrdv <= 1'b0; wdat_lcrdv <= 1'b0; srsp_lcrdv <= 1'b0;
      crsp_flitv <= 1'b0; crsp_opcode <= 5'h0; crsp_txnid <= 12'h0; crsp_dbid <= 12'h0; crsp_resp <= 3'h0;
      crsp_resperr <= 2'h0; crsp_pcrdtype <= 4'h0;
      rdat_flitv <= 1'b0; rdat_opcode <= 4'h0; rdat_txnid <= 12'h0; rdat_dbid <= 12'h0; rdat_resp <= 3'h0;
      rdat_resperr <= 2'h0; rdat_dataid <= 2'h0; rdat_data <= 128'h0;
      proto_err <= 1'b0; proto_code <= 3'h0;
    end else begin
      proto_err <= 1'b0;
      n = q_n; pg = pend_grant; rv = resv; nfree = 3'd0;
      fc = 3'd0;
      for (i = 0; i < TRK; i++) if (t_st[i] == T_FREE) fc = fc + 3'd1;

      // ---- RXRSP: the queue head, when we hold a credit
      crsp_flitv <= 1'b0;
      if (n != 0 && cr_crsp != 0) begin
        crsp_flitv <= 1'b1; crsp_opcode <= q_op[0]; crsp_txnid <= q_txn[0]; crsp_dbid <= q_dbid[0];
        crsp_resp <= q_resp[0]; crsp_resperr <= q_err[0]; crsp_pcrdtype <= q_pt[0];
        for (k = 0; k < QD - 1; k++) begin
          q_op[k] <= q_op[k+1]; q_txn[k] <= q_txn[k+1]; q_dbid[k] <= q_dbid[k+1]; q_resp[k] <= q_resp[k+1];
          q_err[k] <= q_err[k+1]; q_pt[k] <= q_pt[k+1];
        end
        n = n - 4'd1;
        cr_crsp <= cr_crsp - 4'd1 + crsp_lcrdv;
      end else cr_crsp <= cr_crsp + crsp_lcrdv;

      // ---- RXDAT: one CompData beat, lowest tracker first
      rdat_flitv <= 1'b0;
      sent = 1'b0;
      for (i = 0; i < TRK; i++) begin
        if (!sent && t_st[i] == T_RD && cr_rdat != 0) begin
          sent = 1'b1;
          rdat_flitv <= 1'b1; rdat_opcode <= 4'h4; rdat_txnid <= t_txn[i]; rdat_dbid <= i;
          rdat_resp <= t_resp[i]; rdat_resperr <= t_oor[i] ? 2'b10 : 2'b00; rdat_dataid <= t_beat[i];
          rdat_data <= t_oor[i] ? 128'h0 : mem[t_line[i]][128 * t_beat[i] +: 128];
          t_beat[i] <= t_beat[i] + 2'd1;
          if (t_beat[i] == 2'd3) begin
            if (t_ack[i]) t_st[i] <= T_RACK;
            else begin t_st[i] <= T_FREE; nfree = nfree + 3'd1; end
          end
        end
      end
      cr_rdat <= cr_rdat - sent + rdat_lcrdv;

      // ---- L-credits we grant on the inbound channels, one per clock each; a REQ credit only while
      //      the RXRSP queue has room for every REQ the RN may still send plus the P-credit grants
      gr_req = (g_req != 0) && (q_n + rn_req < QD - TRK); gr_wdat = (g_wdat != 0); gr_srsp = (g_srsp != 0);
      req_lcrdv <= gr_req; wdat_lcrdv <= gr_wdat; srsp_lcrdv <= gr_srsp;
      req_ok  = req_flitv && rn_req != 0;
      wdat_ok = wdat_flitv && rn_wdat != 0;
      srsp_ok = srsp_flitv && rn_srsp != 0;
      rn_req  <= rn_req + gr_req - req_ok;    g_req  <= g_req - gr_req + req_ok;
      rn_wdat <= rn_wdat + gr_wdat - wdat_ok; g_wdat <= g_wdat - gr_wdat + wdat_ok;
      rn_srsp <= rn_srsp + gr_srsp - srsp_ok; g_srsp <= g_srsp - gr_srsp + srsp_ok;
      if ((req_flitv && !req_ok) || (wdat_flitv && !wdat_ok) || (srsp_flitv && !srsp_ok)) begin
        proto_err <= 1'b1; proto_code <= 3'd1;
      end

      // ---- TXRSP: CompAck, TxnID = DBID
      if (srsp_ok) begin
        di = srsp_txnid;
        if (srsp_opcode == 5'h2 && di < TRK && (t_st[di] == T_RACK || t_st[di] == T_DACK)) begin
          t_st[di] <= T_FREE; nfree = nfree + 3'd1;
        end else begin proto_err <= 1'b1; proto_code <= 3'd6; end
      end

      // ---- TXDAT: write data, TxnID = DBID
      if (wdat_ok) begin
        di = wdat_txnid;
        if (di < TRK && t_st[di] == T_WD &&
            wdat_opcode == ((t_op[di] == 7'h15 || t_op[di] == 7'h17 || t_op[di] == 7'h1B) ? 4'h2 : 4'h3)) begin
          if (!t_oor[di] && !(wdat_opcode == 4'h2 && wdat_resp == 3'b000))
            for (k = 0; k < 16; k++)
              if (wdat_be[k]) mem[t_line[di]][128 * wdat_dataid + 8 * k +: 8] <= wdat_data[8 * k +: 8];
          t_mask[di] <= t_mask[di] | (4'h1 << wdat_dataid);
          if ((t_mask[di] | (4'h1 << wdat_dataid)) == 4'hF) begin t_st[di] <= T_FREE; nfree = nfree + 3'd1; end
        end else begin proto_err <= 1'b1; proto_code <= 3'd6; end
      end

      // ---- TXREQ
      if (req_ok) begin
        ec = 3'd0;
        found = 1'b0;
        for (i = 0; i < TRK; i++) if (t_st[i] != T_FREE && t_txn[i] == req_txnid) found = 1'b1;
        if (!((req_opcode >= 7'h01 && req_opcode <= 7'h04) || (req_opcode >= 7'h07 && req_opcode <= 7'h0D) ||
              req_opcode == 7'h15 || (req_opcode >= 7'h17 && req_opcode <= 7'h19) ||
              (req_opcode >= 7'h1B && req_opcode <= 7'h1D))) ec = 3'd7;
        else if (found) ec = 3'd2;
        else if (req_size != 3'd6 || req_addr[5:0] != 6'h0) ec = 3'd3;
        else if (!req_expcompack && (req_opcode == 7'h01 || req_opcode == 7'h02 || req_opcode == 7'h07 ||
                                     req_opcode == 7'h0B || req_opcode == 7'h0C)) ec = 3'd4;
        else if (!req_allowretry && (rv == 0 || req_pcrdtype != 4'd1)) ec = 3'd5;
        if (ec != 3'd0) begin
          proto_err <= 1'b1; proto_code <= ec;
          push(5'h4, req_txnid, 12'hFFF, 3'b000, 2'b11, 4'h0);
        end else if (req_allowretry && fc <= rv) begin
          // no unreserved tracker: retry, and grant a P-credit when one frees
          push(5'h3, req_txnid, 12'h0, 3'b000, 2'b00, 4'h1);
          pg = pg + 3'd1;
        end else begin
          if (!req_allowretry) rv = rv - 3'd1;
          rd_i = 3'd0;
          for (i = TRK - 1; i >= 0; i--) if (t_st[i] == T_FREE) rd_i = i;
          t_txn[rd_i] <= req_txnid; t_line[rd_i] <= req_addr[11:6]; t_oor[rd_i] <= (req_addr[43:12] != 0);
          t_op[rd_i] <= req_opcode; t_beat[rd_i] <= 2'd0; t_mask[rd_i] <= 4'h0; t_ack[rd_i] <= req_expcompack;
          if (req_opcode <= 7'h07) begin
            t_st[rd_i] <= T_RD;
            t_resp[rd_i] <= (req_opcode == 7'h07) ? 3'b010 : (req_opcode <= 7'h02) ? 3'b001 : 3'b000;
          end else if (req_opcode <= 7'h0D) begin
            push(5'h4, req_txnid, rd_i, (req_opcode == 7'h0B || req_opcode == 7'h0C) ? 3'b010 : 3'b000,
                 (req_addr[43:12] != 0) ? 2'b11 : 2'b00, 4'h0);
            if (req_expcompack) t_st[rd_i] <= T_DACK;
            else begin t_st[rd_i] <= T_FREE; nfree = nfree + 3'd1; end
          end else begin
            push(5'h5, req_txnid, rd_i, 3'b000, (req_addr[43:12] != 0) ? 2'b11 : 2'b00, 4'h0);
            t_st[rd_i] <= T_WD;
          end
        end
      end

      // ---- every tracker freed while requests wait for a retry: PCrdGrant, reserving it
      for (i = 0; i < TRK; i++)
        if (nfree != 0 && pg != 0) begin
          push(5'h7, 12'h0, 12'h0, 3'b000, 2'b00, 4'h1);
          pg = pg - 3'd1; rv = rv + 3'd1; nfree = nfree - 3'd1;
        end
      pend_grant <= pg; resv <= rv; q_n <= n;
    end
  end
endmodule
"""

SPEC = dict(
    vip="CHI-UVM-VIP", p="chi", P="CHI", dir="chi", family="Processor & Interconnect",
    desc="AMBA CHI (Issue E opcodes) request-node VIP: reads, dataless, write and copy-back transactions "
         "with TxnID / DBID, CompAck, RetryAck / PCrdGrant retry, link-layer L-credits on all five "
         "channels and RespErr, against a Home Node with memory; with error injection.",
    about="""
The agent is a request node on split CHI channels (TXREQ, TXDAT, TXRSP out;
RXRSP, RXDAT in). It keeps up to four transactions outstanding, allocates
TxnIDs, holds and returns link-layer credits on every channel, answers
CompDBIDResp with four write-data beats (NonCopyBackWrData, or
CopyBackWrData with UD_PD or I), sends CompAck after CompData / Comp when the
request set ExpCompAck, and re-sends a request after RetryAck once the Home
Node grants a P-credit (AllowRetry 0, PCrdType 1). Requests can be broken on
purpose: a Size other than 64 bytes, an unaligned address, a missing
ExpCompAck, an unsupported opcode or an address outside the Home Node's
memory.

The monitor follows every transaction by TxnID and DBID across the five
channels and publishes it in request order; the scoreboard's reference
model keeps a mirror of the memory and predicts the response state,
RespErr, the read data, the protocol error code, and checks that only
requests with AllowRetry are retried.

The Home Node model serves one request node (no snoops); the two-node
coherent Home Node model with snoops is chi_hn/tb/chi_hn_model.sv.""",
    defs=DEFS,
    timeout=2000,
    ports=[
        ("in", "logic", "req_flitv"), ("in", "logic [6:0]", "req_opcode"), ("in", "logic [11:0]", "req_txnid"),
        ("in", "logic [43:0]", "req_addr"), ("in", "logic [2:0]", "req_size"), ("in", "logic", "req_allowretry"),
        ("in", "logic [3:0]", "req_pcrdtype"), ("in", "logic", "req_expcompack"), ("out", "logic", "req_lcrdv"),
        ("in", "logic", "wdat_flitv"), ("in", "logic [3:0]", "wdat_opcode"), ("in", "logic [11:0]", "wdat_txnid"),
        ("in", "logic [2:0]", "wdat_resp"), ("in", "logic [1:0]", "wdat_dataid"), ("in", "logic [15:0]", "wdat_be"),
        ("in", "logic [127:0]", "wdat_data"), ("out", "logic", "wdat_lcrdv"),
        ("in", "logic", "srsp_flitv"), ("in", "logic [4:0]", "srsp_opcode"), ("in", "logic [11:0]", "srsp_txnid"),
        ("out", "logic", "srsp_lcrdv"),
        ("out", "logic", "crsp_flitv"), ("out", "logic [4:0]", "crsp_opcode"), ("out", "logic [11:0]", "crsp_txnid"),
        ("out", "logic [11:0]", "crsp_dbid"), ("out", "logic [2:0]", "crsp_resp"), ("out", "logic [1:0]", "crsp_resperr"),
        ("out", "logic [3:0]", "crsp_pcrdtype"), ("in", "logic", "crsp_lcrdv"),
        ("out", "logic", "rdat_flitv"), ("out", "logic [3:0]", "rdat_opcode"), ("out", "logic [11:0]", "rdat_txnid"),
        ("out", "logic [11:0]", "rdat_dbid"), ("out", "logic [2:0]", "rdat_resp"), ("out", "logic [1:0]", "rdat_resperr"),
        ("out", "logic [1:0]", "rdat_dataid"), ("out", "logic [127:0]", "rdat_data"), ("in", "logic", "rdat_lcrdv"),
        ("out", "logic", "proto_err"), ("out", "logic [2:0]", "proto_code"),
    ],
    cfg="int unsigned max_out = 4;   // outstanding transactions",
    fields=[
        ("bit [6:0]", "opcode", "req"),
        ("bit [11:0]", "txnid", "req", "norand"),
        ("bit [43:0]", "addr", "req", "norand"),
        ("bit [2:0]", "size", "req", "norand"),
        ("bit", "allowretry", "req", "norand"),
        ("bit [3:0]", "pcrdtype", "req", "norand"),
        ("bit", "expcompack", "req", "norand"),
        ("bit [511:0]", "wdata", "req"),
        ("bit [63:0]", "be", "req", "norand"),
        ("bit [2:0]", "cb_resp", "req", "norand"),
        ("bit", "retried", "rsp"),
        ("bit [2:0]", "resp", "rsp"),
        ("bit [1:0]", "resperr", "rsp"),
        ("bit [511:0]", "rdata", "rsp"),
        ("bit [2:0]", "perr", "rsp"),
        ("chi_inj_e", "inj", "info", "rand"),
        ("bit [5:0]", "line", "info", "rand"),
        ("bit", "ackopt", "info", "rand"),
        ("bit", "cbi", "info", "rand"),
        ("bit [63:0]", "pbe", "info", "rand"),
        ("bit [3:0]", "gap", "info", "rand"),
        ("bit [11:0]", "dbid", "info"),
        ("bit [2:0]", "nbeat", "info"),
        ("bit", "mdone", "info"),
    ],
    constraints="""
constraint c_op  { opcode inside {CHI_READ_SHARED, CHI_READ_CLEAN, CHI_READ_ONCE, CHI_READ_NOSNP, CHI_READ_UNIQUE,
                                  CHI_CLEAN_SHARED, CHI_CLEAN_INVALID, CHI_MAKE_INVALID, CHI_CLEAN_UNIQUE, CHI_MAKE_UNIQUE,
                                  CHI_EVICT, CHI_WRITE_EVICT_FULL, CHI_WRITE_CLEAN_FULL, CHI_WRITE_UNIQUE_PTL,
                                  CHI_WRITE_UNIQUE_FULL, CHI_WRITE_BACK_FULL, CHI_WRITE_NOSNP_PTL, CHI_WRITE_NOSNP_FULL}; }
constraint c_inj { inj dist { CHI_X_NONE := 24, [CHI_X_SIZE : CHI_X_OOR] :/ 6 }; }
constraint c_dat { !chi_is_write(opcode) -> wdata == 0; line inside {[0:15]}; gap inside {[0:3]}; }
""",
    drv_rsp=False,
    drv_desc="one request per item, up to cfg.max_out outstanding; background threads hold the link credits, "
             "send write data and CompAck and re-send retried requests",
    drv_members="""int unsigned cr_req = 0, cr_wdat = 0, cr_srsp = 0;   // L-credits granted by the Home Node
int unsigned owe_crsp = 0, owe_rdat = 0;            // L-credits we still have to grant
chi_transaction outq [bit [11:0]];                  // by TxnID, waiting for the first response
chi_transaction retryq [$];
bit [3:0]    rbeats [bit [11:0]];
bit          busy_line [64];
bit          inuse [16];
int unsigned n_out = 0;
bit [3:0]    next_id = 0;
bit          lk_req, lk_wdat, lk_srsp;   // channel locks (Verilator's semaphore spins in zero time)""",
    # the Home Node grants its first L-credits right after reset: count them from there
    drv_bg_at_reset=True,
    drv_bg="""
begin
  lk_req = 0; lk_wdat = 0; lk_srsp = 0;
  owe_crsp = 4; owe_rdat = 4;
  fork
    forever begin
      @(vif.drv_cb);
      if (vif.drv_cb.req_lcrdv === 1'b1) cr_req++;
      if (vif.drv_cb.wdat_lcrdv === 1'b1) cr_wdat++;
      if (vif.drv_cb.srsp_lcrdv === 1'b1) cr_srsp++;
    end
    forever begin
      vif.drv_cb.crsp_lcrdv <= (owe_crsp != 0);
      vif.drv_cb.rdat_lcrdv <= (owe_rdat != 0);
      if (owe_crsp != 0) owe_crsp--;
      if (owe_rdat != 0) owe_rdat--;
      @(vif.drv_cb);
      if (vif.drv_cb.crsp_flitv === 1'b1) begin owe_crsp++; on_rsp(); end
      if (vif.drv_cb.rdat_flitv === 1'b1) begin owe_rdat++; on_dat(); end
    end
  join_none
end""",
    drv_idle="""
vif.drv_cb.req_flitv <= 1'b0; vif.drv_cb.req_opcode <= '0; vif.drv_cb.req_txnid <= '0; vif.drv_cb.req_addr <= '0;
vif.drv_cb.req_size <= '0; vif.drv_cb.req_allowretry <= 1'b0; vif.drv_cb.req_pcrdtype <= '0; vif.drv_cb.req_expcompack <= 1'b0;
vif.drv_cb.wdat_flitv <= 1'b0; vif.drv_cb.wdat_opcode <= '0; vif.drv_cb.wdat_txnid <= '0; vif.drv_cb.wdat_resp <= '0;
vif.drv_cb.wdat_dataid <= '0; vif.drv_cb.wdat_be <= '0; vif.drv_cb.wdat_data <= '0;
vif.drv_cb.srsp_flitv <= 1'b0; vif.drv_cb.srsp_opcode <= '0; vif.drv_cb.srsp_txnid <= '0;
vif.drv_cb.crsp_lcrdv <= 1'b0; vif.drv_cb.rdat_lcrdv <= 1'b0;
""",
    drv_item="""
repeat (t.gap) @(vif.drv_cb);
while (n_out >= cfg.max_out || busy_line[t.line]) @(vif.drv_cb);
while (inuse[next_id]) next_id++;
t.txnid = next_id; inuse[next_id] = 1; next_id++;
if (t.inj == CHI_X_OP) t.opcode = 7'h05 + t.pbe[0];
t.size = (t.inj == CHI_X_SIZE) ? 3'd5 : 3'd6;
t.addr = {(t.inj == CHI_X_OOR) ? 32'h1 : 32'h0, t.line, (t.inj == CHI_X_ALIGN) ? 6'h20 : 6'h00};
if (t.inj inside {CHI_X_NONE, CHI_X_OOR})
  t.expcompack = chi_needs_ack(t.opcode) || (chi_is_read(t.opcode) && t.ackopt);
else t.expcompack = 0;
t.allowretry = 1; t.pcrdtype = 0;
t.be = !chi_is_write(t.opcode) ? 64'h0 : chi_is_ptl(t.opcode) ? t.pbe : '1;
t.cb_resp = chi_is_copyback(t.opcode) ? (t.cbi ? CHI_I : CHI_UD_PD) : CHI_I;
if (!chi_is_write(t.opcode)) t.wdata = 0;
outq[t.txnid] = t; rbeats[t.txnid] = 0;
n_out++; busy_line[t.line] = 1;
send_req(t);
""",
    drv_tasks="""
task send_req(chi_transaction t);
  while (lk_req) @(vif.drv_cb); lk_req = 1;
  while (cr_req == 0) @(vif.drv_cb);
  cr_req--;
  vif.drv_cb.req_flitv <= 1'b1; vif.drv_cb.req_opcode <= t.opcode; vif.drv_cb.req_txnid <= t.txnid;
  vif.drv_cb.req_addr <= t.addr; vif.drv_cb.req_size <= t.size; vif.drv_cb.req_allowretry <= t.allowretry;
  vif.drv_cb.req_pcrdtype <= t.pcrdtype; vif.drv_cb.req_expcompack <= t.expcompack;
  @(vif.drv_cb);
  vif.drv_cb.req_flitv <= 1'b0;
  lk_req = 0;
endtask

// a retried request goes again with the granted P-credit
task resend(chi_transaction t);
  chi_transaction c;
  t.allowretry = 0; t.pcrdtype = 4'd1;
  outq[t.txnid] = t; rbeats[t.txnid] = 0;
  send_req(t);
  $cast(c, t.clone());
  ap.write(c);
endtask

task send_wdata(chi_transaction t, bit [11:0] dbid);
  while (lk_wdat) @(vif.drv_cb); lk_wdat = 1;
  for (int b = 0; b < 4; b++) begin
    while (cr_wdat == 0) begin vif.drv_cb.wdat_flitv <= 1'b0; @(vif.drv_cb); end   // no flit while out of credits
    cr_wdat--;
    vif.drv_cb.wdat_flitv <= 1'b1;
    vif.drv_cb.wdat_opcode <= chi_is_copyback(t.opcode) ? CHI_COPYBACK_WR : CHI_NONCOPYBACK_WR;
    vif.drv_cb.wdat_txnid <= dbid; vif.drv_cb.wdat_resp <= t.cb_resp; vif.drv_cb.wdat_dataid <= b;
    vif.drv_cb.wdat_be <= t.be[16*b +: 16]; vif.drv_cb.wdat_data <= t.wdata[128*b +: 128];
    @(vif.drv_cb);
  end
  vif.drv_cb.wdat_flitv <= 1'b0;
  lk_wdat = 0;
  done(t);
endtask

task send_ack(bit [11:0] dbid);
  while (lk_srsp) @(vif.drv_cb); lk_srsp = 1;
  while (cr_srsp == 0) @(vif.drv_cb);
  cr_srsp--;
  vif.drv_cb.srsp_flitv <= 1'b1; vif.drv_cb.srsp_opcode <= CHI_COMP_ACK; vif.drv_cb.srsp_txnid <= dbid;
  @(vif.drv_cb);
  vif.drv_cb.srsp_flitv <= 1'b0;
  lk_srsp = 0;
endtask

function void done(chi_transaction t);
  inuse[t.txnid[3:0]] = 0; busy_line[t.line] = 0; n_out--;
endfunction

// RXRSP flit (sampled this clock)
function void on_rsp();
  bit [11:0] id = vif.drv_cb.crsp_txnid, db = vif.drv_cb.crsp_dbid;
  chi_transaction t;
  case (vif.drv_cb.crsp_opcode)
    CHI_PCRD_GRANT:
      if (retryq.size() == 0) `uvm_error("DRV", "CHI PCrdGrant with no retried request")
      else begin
        chi_transaction r = retryq.pop_front();
        fork resend(r); join_none
      end
    CHI_RETRY_ACK, CHI_COMP, CHI_COMP_DBID: begin
      if (!outq.exists(id)) begin `uvm_error("DRV", $sformatf("CHI response for TxnID %0d not outstanding", id)) return; end
      t = outq[id]; outq.delete(id);
      if (vif.drv_cb.crsp_opcode == CHI_RETRY_ACK) retryq.push_back(t);
      else if (vif.drv_cb.crsp_opcode == CHI_COMP_DBID) fork send_wdata(t, db); join_none
      else begin
        if (t.expcompack && db != 12'hFFF) fork send_ack(db); join_none
        done(t);
      end
    end
    default: `uvm_error("DRV", "CHI unexpected RXRSP opcode")
  endcase
endfunction

// RXDAT flit: CompData beat
function void on_dat();
  bit [11:0] id = vif.drv_cb.rdat_txnid, db = vif.drv_cb.rdat_dbid;
  chi_transaction t;
  if (!outq.exists(id)) begin `uvm_error("DRV", $sformatf("CHI CompData for TxnID %0d not outstanding", id)) return; end
  t = outq[id];
  rbeats[id]++;
  if (rbeats[id] == 4) begin
    outq.delete(id);
    if (t.expcompack) fork send_ack(db); join_none
    done(t);
  end
endfunction
""",
    mon_desc="every transaction followed by TxnID / DBID over the five channels, published in request order",
    mon_run="""
chi_transaction rob[$];
chi_transaction byid [bit [11:0]];
chi_transaction bydw [bit [11:0]];
chi_transaction byda [bit [11:0]];
chi_transaction pend_perr;
forever begin
  @(vif.mon_cb);
  if (vif.mon_cb.rst_n !== 1'b1) begin rob.delete(); byid.delete(); bydw.delete(); byda.delete(); pend_perr = null; continue; end
  if (pend_perr != null) begin pend_perr.perr = vif.mon_cb.proto_err ? vif.mon_cb.proto_code : 3'd0; pend_perr = null; end
  if (vif.mon_cb.req_flitv) begin
    chi_transaction t = chi_transaction::type_id::create("t");
    t.opcode = vif.mon_cb.req_opcode; t.txnid = vif.mon_cb.req_txnid; t.addr = vif.mon_cb.req_addr;
    t.size = vif.mon_cb.req_size; t.allowretry = vif.mon_cb.req_allowretry; t.pcrdtype = vif.mon_cb.req_pcrdtype;
    t.expcompack = vif.mon_cb.req_expcompack; t.cb_resp = CHI_I;
    if (byid.exists(t.txnid)) `uvm_error("MON", $sformatf("CHI TxnID %0d reused while outstanding", t.txnid))
    rob.push_back(t); byid[t.txnid] = t; pend_perr = t;
  end
  if (vif.mon_cb.crsp_flitv) begin
    bit [11:0] id = vif.mon_cb.crsp_txnid, db = vif.mon_cb.crsp_dbid;
    if (vif.mon_cb.crsp_opcode == CHI_PCRD_GRANT) begin
      if (vif.mon_cb.crsp_pcrdtype != 4'd1) `uvm_error("MON", "CHI PCrdGrant with an unexpected PCrdType")
    end else if (!byid.exists(id)) `uvm_error("MON", $sformatf("CHI RXRSP for TxnID %0d not outstanding", id))
    else begin
      chi_transaction t = byid[id];
      byid.delete(id);
      t.dbid = db;
      case (vif.mon_cb.crsp_opcode)
        CHI_RETRY_ACK: begin
          t.retried = 1; t.mdone = 1;
          if (vif.mon_cb.crsp_pcrdtype != 4'd1) `uvm_error("MON", "CHI RetryAck with an unexpected PCrdType")
        end
        CHI_COMP: begin
          t.resp = vif.mon_cb.crsp_resp; t.resperr = vif.mon_cb.crsp_resperr;
          if (t.expcompack && db != 12'hFFF) byda[db] = t; else t.mdone = 1;
        end
        CHI_COMP_DBID: begin t.resperr = vif.mon_cb.crsp_resperr; bydw[db] = t; end
        default: `uvm_error("MON", "CHI unexpected RXRSP opcode")
      endcase
    end
  end
  if (vif.mon_cb.rdat_flitv) begin
    bit [11:0] id = vif.mon_cb.rdat_txnid;
    if (vif.mon_cb.rdat_opcode != CHI_COMP_DATA || !byid.exists(id))
      `uvm_error("MON", $sformatf("CHI RXDAT for TxnID %0d not outstanding", id))
    else begin
      chi_transaction t = byid[id];
      t.rdata[128 * vif.mon_cb.rdat_dataid +: 128] = vif.mon_cb.rdat_data;
      t.resp = vif.mon_cb.rdat_resp; t.resperr = vif.mon_cb.rdat_resperr; t.dbid = vif.mon_cb.rdat_dbid;
      if (++t.nbeat == 4) begin
        byid.delete(id);
        if (t.expcompack) byda[t.dbid] = t; else t.mdone = 1;
      end
    end
  end
  if (vif.mon_cb.wdat_flitv) begin
    bit [11:0] db = vif.mon_cb.wdat_txnid;
    if (!bydw.exists(db)) `uvm_error("MON", $sformatf("CHI write data for DBID %0d not expected", db))
    else begin
      chi_transaction t = bydw[db];
      t.wdata[128 * vif.mon_cb.wdat_dataid +: 128] = vif.mon_cb.wdat_data;
      t.be[16 * vif.mon_cb.wdat_dataid +: 16] = vif.mon_cb.wdat_be;
      t.cb_resp = vif.mon_cb.wdat_resp;
      if (++t.nbeat == 4) begin bydw.delete(db); t.mdone = 1; end
    end
  end
  if (vif.mon_cb.srsp_flitv) begin
    bit [11:0] db = vif.mon_cb.srsp_txnid;
    if (vif.mon_cb.srsp_opcode != CHI_COMP_ACK || !byda.exists(db)) `uvm_error("MON", $sformatf("CHI CompAck for DBID %0d not expected", db))
    else begin byda[db].mdone = 1; byda.delete(db); end
  end
  while (rob.size() != 0 && rob[0].mdone && rob[0] != pend_perr) publish(rob.pop_front());
end
""",
    sb_members="""bit [511:0] mir [int];   // memory mirror, by line
// a retried or rejected (protocol error) request carries no data: compare the request flit only
function bit agree(chi_transaction e, chi_transaction o);
  if (!o.retried && o.perr == 0) return e.req_equal(o);
  return e.opcode == o.opcode && e.txnid == o.txnid && e.addr == o.addr && e.size == o.size &&
         e.allowretry == o.allowretry && e.pcrdtype == o.pcrdtype && e.expcompack == o.expcompack;
endfunction""",
    pair_agree="agree(e, o)",
    predict="""
bit oor;
bit [5:0] l = t.addr[11:6];
bit [511:0] m;
t.perr = 0; t.resp = 0; t.resperr = CHI_RE_OK; t.rdata = 0;
if (!chi_known(t.opcode)) t.perr = 7;
else if (t.size != 3'd6 || t.addr[5:0] != 0) t.perr = 3;
else if (chi_needs_ack(t.opcode) && !t.expcompack) t.perr = 4;
else if (!t.allowretry && t.pcrdtype != 4'd1) t.perr = 5;
if (t.perr != 0) begin t.resperr = CHI_RE_NDERR; t.retried = 0; end
else if (!(t.retried && t.allowretry)) begin
  t.retried = 0;
  oor = (t.addr[43:12] != 0);
  m = mir.exists(l) ? mir[l] : chi_mem_init(l);
  if (chi_is_read(t.opcode)) begin
    t.resp = (t.opcode == CHI_READ_UNIQUE) ? CHI_UC : (t.opcode inside {CHI_READ_SHARED, CHI_READ_CLEAN}) ? CHI_SC : CHI_I;
    t.resperr = oor ? CHI_RE_DERR : CHI_RE_OK;
    t.rdata = oor ? 512'h0 : m;
  end else if (chi_is_dataless(t.opcode)) begin
    t.resp = (t.opcode inside {CHI_CLEAN_UNIQUE, CHI_MAKE_UNIQUE}) ? CHI_UC : CHI_I;
    t.resperr = oor ? CHI_RE_NDERR : CHI_RE_OK;
  end else begin
    t.resperr = oor ? CHI_RE_NDERR : CHI_RE_OK;
    if (!oor && !(chi_is_copyback(t.opcode) && t.cb_resp == CHI_I)) begin
      for (int k = 0; k < 64; k++) if (t.be[k]) m[8*k +: 8] = t.wdata[8*k +: 8];
      mir[l] = m;
    end
  end
end
""",
    checks="""
if (t.retried && !t.allowretry) fail(t, "request without AllowRetry was retried");
if (t.resperr == CHI_RE_DERR && t.rdata != 0) fail(t, "CompData with DERR carries data");
if (!t.retried && t.perr == 0 && chi_is_write(t.opcode) && t.be == 0 && !chi_is_ptl(t.opcode)) fail(t, "full write without byte enables");
""",
    coverage="""
cp_op    : coverpoint tr.opcode { bins rd_shared = {CHI_READ_SHARED}; bins rd_clean = {CHI_READ_CLEAN}; bins rd_once = {CHI_READ_ONCE};
                                  bins rd_nosnp = {CHI_READ_NOSNP}; bins rd_unique = {CHI_READ_UNIQUE};
                                  bins cl_shared = {CHI_CLEAN_SHARED}; bins cl_inval = {CHI_CLEAN_INVALID};
                                  bins mk_inval = {CHI_MAKE_INVALID}; bins cl_unique = {CHI_CLEAN_UNIQUE};
                                  bins mk_unique = {CHI_MAKE_UNIQUE}; bins evict = {CHI_EVICT};
                                  bins wr_evict = {CHI_WRITE_EVICT_FULL}; bins wr_clean = {CHI_WRITE_CLEAN_FULL};
                                  bins wr_uptl = {CHI_WRITE_UNIQUE_PTL}; bins wr_ufull = {CHI_WRITE_UNIQUE_FULL};
                                  bins wr_back = {CHI_WRITE_BACK_FULL}; bins wr_nptl = {CHI_WRITE_NOSNP_PTL};
                                  bins wr_nfull = {CHI_WRITE_NOSNP_FULL}; bins bad = {7'h05, 7'h06}; }
cp_retry : coverpoint tr.retried;
cp_ar    : coverpoint tr.allowretry;
cp_err   : coverpoint tr.resperr { bins ok = {CHI_RE_OK}; bins derr = {CHI_RE_DERR}; bins nderr = {CHI_RE_NDERR}; }
cp_perr  : coverpoint tr.perr { bins none = {0}; bins size = {3}; bins ack = {4}; bins op = {7}; }
cp_resp  : coverpoint tr.resp iff (!tr.retried && tr.perr == 0) { bins i = {CHI_I}; bins sc = {CHI_SC}; bins uc = {CHI_UC}; }
cp_ack   : coverpoint tr.expcompack iff (chi_is_read(tr.opcode) && !chi_needs_ack(tr.opcode));
cp_cb    : coverpoint tr.cb_resp iff (chi_is_copyback(tr.opcode) && !tr.retried && tr.perr == 0) { bins i = {CHI_I}; bins ud = {CHI_UD_PD}; }
cp_rop   : coverpoint tr.opcode { bins rd_shared = {CHI_READ_SHARED}; bins rd_clean = {CHI_READ_CLEAN}; bins rd_once = {CHI_READ_ONCE};
                                  bins rd_nosnp = {CHI_READ_NOSNP}; bins rd_unique = {CHI_READ_UNIQUE};
                                  bins cl_shared = {CHI_CLEAN_SHARED}; bins cl_inval = {CHI_CLEAN_INVALID};
                                  bins mk_inval = {CHI_MAKE_INVALID}; bins cl_unique = {CHI_CLEAN_UNIQUE};
                                  bins mk_unique = {CHI_MAKE_UNIQUE}; bins evict = {CHI_EVICT};
                                  bins wr_evict = {CHI_WRITE_EVICT_FULL}; bins wr_clean = {CHI_WRITE_CLEAN_FULL};
                                  bins wr_uptl = {CHI_WRITE_UNIQUE_PTL}; bins wr_ufull = {CHI_WRITE_UNIQUE_FULL};
                                  bins wr_back = {CHI_WRITE_BACK_FULL}; bins wr_nptl = {CHI_WRITE_NOSNP_PTL};
                                  bins wr_nfull = {CHI_WRITE_NOSNP_FULL}; }   // legal opcodes only (Verilator counts cross ignore_bins as bins)
x_retry  : cross cp_rop, cp_retry;
""",
    directed="""
bit [6:0] ops [18] = '{CHI_READ_SHARED, CHI_READ_CLEAN, CHI_READ_ONCE, CHI_READ_NOSNP, CHI_READ_UNIQUE, CHI_CLEAN_SHARED,
                       CHI_CLEAN_INVALID, CHI_MAKE_INVALID, CHI_CLEAN_UNIQUE, CHI_MAKE_UNIQUE, CHI_EVICT,
                       CHI_WRITE_EVICT_FULL, CHI_WRITE_CLEAN_FULL, CHI_WRITE_UNIQUE_PTL, CHI_WRITE_UNIQUE_FULL,
                       CHI_WRITE_BACK_FULL, CHI_WRITE_NOSNP_PTL, CHI_WRITE_NOSNP_FULL};
// every opcode, one at a time and then back to back (four outstanding: retries)
foreach (ops[i]) begin t = item(); t.opcode = ops[i]; t.inj = CHI_X_NONE; t.line = i % 16; t.gap = 0; send(t); end
for (int r = 0; r < 2; r++)
  foreach (ops[i]) begin t = item(); t.opcode = ops[i]; t.inj = CHI_X_NONE; t.line = (i + r) % 16; t.gap = 0; t.cbi = r; t.ackopt = r; send(t); end
// four of one opcode back to back: two trackers, so each opcode also gets retried
foreach (ops[i]) for (int k = 0; k < 4; k++) begin t = item(); t.opcode = ops[i]; t.inj = CHI_X_NONE; t.line = 8 + 2 * k; t.gap = 0; send(t); end
// write then read back, partial write, lost copy-back
t = item(); t.opcode = CHI_WRITE_NOSNP_FULL; t.inj = CHI_X_NONE; t.line = 3; t.wdata = {16{32'h1234_5678}}; send(t);
t = item(); t.opcode = CHI_READ_NOSNP; t.inj = CHI_X_NONE; t.line = 3; send(t);
t = item(); t.opcode = CHI_WRITE_UNIQUE_PTL; t.inj = CHI_X_NONE; t.line = 3; t.pbe = 64'h00FF_0000_F0F0_0001; t.wdata = '1; send(t);
t = item(); t.opcode = CHI_READ_ONCE; t.inj = CHI_X_NONE; t.line = 3; send(t);
t = item(); t.opcode = CHI_WRITE_BACK_FULL; t.inj = CHI_X_NONE; t.line = 3; t.cbi = 1; send(t);
t = item(); t.opcode = CHI_READ_SHARED; t.inj = CHI_X_NONE; t.line = 3; send(t);
// every injected error on a read, a dataless request and a write
for (int i = 1; i < 6; i++) begin
  t = item(); t.opcode = CHI_READ_UNIQUE; t.inj = chi_inj_e'(i); t.line = 4; send(t);
  t = item(); t.opcode = CHI_CLEAN_UNIQUE; t.inj = chi_inj_e'(i); t.line = 5; send(t);
  t = item(); t.opcode = CHI_WRITE_NOSNP_FULL; t.inj = chi_inj_e'(i); t.line = 6; send(t);
end
""",
    drain_ns=3000,
    model=MODEL,
)

SPEC["sva"] = """
// flits only with a link credit: count the credits each side holds
int unsigned cr_crsp = 0, cr_rdat = 0;
always @(posedge clk or negedge rst_n)
  if (!rst_n) begin cr_crsp <= 0; cr_rdat <= 0; end
  else begin
    cr_crsp <= cr_crsp + crsp_lcrdv - crsp_flitv;
    cr_rdat <= cr_rdat + rdat_lcrdv - rdat_flitv;
  end
assert property (@(posedge clk) disable iff (!rst_n) crsp_flitv |-> cr_crsp != 0)
  else $error("CHI: RXRSP flit without an L-credit");
assert property (@(posedge clk) disable iff (!rst_n) rdat_flitv |-> cr_rdat != 0)
  else $error("CHI: RXDAT flit without an L-credit");
assert property (@(posedge clk) disable iff (!rst_n) rdat_flitv |-> rdat_opcode == 4'h4)
  else $error("CHI: RXDAT opcode other than CompData");
assert property (@(posedge clk) disable iff (!rst_n) rdat_flitv && rdat_resperr == 2'b10 |-> rdat_data == 128'h0)
  else $error("CHI: CompData with DERR carries data");
assert property (@(posedge clk) disable iff (!rst_n)
                 crsp_flitv && crsp_opcode inside {5'h3, 5'h7} |-> crsp_pcrdtype == 4'd1)
  else $error("CHI: RetryAck / PCrdGrant with an unexpected PCrdType");
assert property (@(posedge clk) disable iff (!rst_n) !$isunknown({crsp_flitv, rdat_flitv, req_lcrdv, wdat_lcrdv, srsp_lcrdv, proto_err}))
  else $error("CHI: X on Home Node outputs");
cover property (@(posedge clk) disable iff (!rst_n) crsp_flitv && crsp_opcode == 5'h3);
cover property (@(posedge clk) disable iff (!rst_n) crsp_flitv && crsp_opcode == 5'h7);
cover property (@(posedge clk) disable iff (!rst_n) rdat_flitv && rdat_resperr == 2'b10);
"""

SPEC["smoke"] = """
int checks = 0;
int fails  = 0;

logic clk = 1'b0;
logic rst_n = 1'b0;
logic req_flitv = 0, req_allowretry = 0, req_expcompack = 0;
logic [6:0] req_opcode = 0;
logic [11:0] req_txnid = 0;
logic [43:0] req_addr = 0;
logic [2:0] req_size = 0;
logic [3:0] req_pcrdtype = 0;
logic wdat_flitv = 0;
logic [3:0] wdat_opcode = 0;
logic [11:0] wdat_txnid = 0;
logic [2:0] wdat_resp = 0;
logic [1:0] wdat_dataid = 0;
logic [15:0] wdat_be = 0;
logic [127:0] wdat_data = 0;
logic srsp_flitv = 0;
logic [4:0] srsp_opcode = 0;
logic [11:0] srsp_txnid = 0;
logic crsp_lcrdv = 0, rdat_lcrdv = 0;
wire req_lcrdv, wdat_lcrdv, srsp_lcrdv, crsp_flitv, rdat_flitv, proto_err;
wire [4:0] crsp_opcode;
wire [11:0] crsp_txnid, crsp_dbid, rdat_txnid, rdat_dbid;
wire [2:0] crsp_resp, rdat_resp, proto_code;
wire [1:0] crsp_resperr, rdat_resperr, rdat_dataid;
wire [3:0] crsp_pcrdtype, rdat_opcode;
wire [127:0] rdat_data;

always #5 clk = ~clk;

chi_model u_dut (.clk(clk), .rst_n(rst_n), .req_flitv(req_flitv), .req_opcode(req_opcode), .req_txnid(req_txnid),
                 .req_addr(req_addr), .req_size(req_size), .req_allowretry(req_allowretry), .req_pcrdtype(req_pcrdtype),
                 .req_expcompack(req_expcompack), .req_lcrdv(req_lcrdv), .wdat_flitv(wdat_flitv),
                 .wdat_opcode(wdat_opcode), .wdat_txnid(wdat_txnid), .wdat_resp(wdat_resp), .wdat_dataid(wdat_dataid),
                 .wdat_be(wdat_be), .wdat_data(wdat_data), .wdat_lcrdv(wdat_lcrdv), .srsp_flitv(srsp_flitv),
                 .srsp_opcode(srsp_opcode), .srsp_txnid(srsp_txnid), .srsp_lcrdv(srsp_lcrdv), .crsp_flitv(crsp_flitv),
                 .crsp_opcode(crsp_opcode), .crsp_txnid(crsp_txnid), .crsp_dbid(crsp_dbid), .crsp_resp(crsp_resp),
                 .crsp_resperr(crsp_resperr), .crsp_pcrdtype(crsp_pcrdtype), .crsp_lcrdv(crsp_lcrdv),
                 .rdat_flitv(rdat_flitv), .rdat_opcode(rdat_opcode), .rdat_txnid(rdat_txnid), .rdat_dbid(rdat_dbid),
                 .rdat_resp(rdat_resp), .rdat_resperr(rdat_resperr), .rdat_dataid(rdat_dataid), .rdat_data(rdat_data),
                 .rdat_lcrdv(rdat_lcrdv), .proto_err(proto_err), .proto_code(proto_code));

task automatic chk(input bit ok, input string msg);
  checks++;
  if (!ok) begin fails++; $display("  [FAIL] %s", msg); end
endtask

// credits the Home Node granted us, and the ones we grant it (auto: one back per flit unless held)
int g_req = 0, g_wdat = 0, g_srsp = 0;
int owe_crsp = 0, owe_rdat = 0;
bit hold = 0;
// RXRSP flits and RXDAT beats seen
logic [4:0]  r_op [0:63];
logic [11:0] r_txn [0:63], r_db [0:63];
logic [2:0]  r_rs [0:63];
logic [1:0]  r_er [0:63];
logic [3:0]  r_pt [0:63];
int nr = 0;
logic [11:0] d_txn [0:255], d_db [0:255];
logic [2:0]  d_rs [0:255];
logic [1:0]  d_er [0:255], d_id [0:255];
logic [127:0] d_dat [0:255];
int nd = 0, nperr = 0, gave_crsp = 0, cr0 = 0, nacc = 0;
logic [2:0] lcode = 0;
always @(negedge clk) begin
  if (req_lcrdv) g_req++;
  if (wdat_lcrdv) g_wdat++;
  if (srsp_lcrdv) g_srsp++;
  if (crsp_flitv) begin
    r_op[nr % 64] = crsp_opcode; r_txn[nr % 64] = crsp_txnid; r_db[nr % 64] = crsp_dbid; r_rs[nr % 64] = crsp_resp;
    r_er[nr % 64] = crsp_resperr; r_pt[nr % 64] = crsp_pcrdtype; nr++;
    if (!hold) owe_crsp++;
  end
  if (rdat_flitv) begin
    d_txn[nd % 256] = rdat_txnid; d_db[nd % 256] = rdat_dbid; d_rs[nd % 256] = rdat_resp; d_er[nd % 256] = rdat_resperr;
    d_id[nd % 256] = rdat_dataid; d_dat[nd % 256] = rdat_data; nd++;
    if (!hold) owe_rdat++;
  end
  if (proto_err) begin nperr++; lcode = proto_code; end
  crsp_lcrdv = (owe_crsp != 0); if (owe_crsp != 0) begin owe_crsp--; gave_crsp++; end
  rdat_lcrdv = (owe_rdat != 0); if (owe_rdat != 0) owe_rdat--;
end

task automatic idle(input int n);
  repeat (n) @(negedge clk);
  #1;
endtask

// one flit each; they use the credit (the count may go negative when sent without one on purpose)
task automatic req(input logic [6:0] op, input logic [11:0] txn, input logic [43:0] a, input bit ack,
                   input bit ar = 1, input logic [3:0] pt = 0, input logic [2:0] sz = 6);
  @(negedge clk); #1;
  req_flitv = 1; req_opcode = op; req_txnid = txn; req_addr = a; req_size = sz; req_allowretry = ar;
  req_pcrdtype = pt; req_expcompack = ack; g_req--;
  @(negedge clk); #1 req_flitv = 0;
endtask
task automatic wd(input logic [3:0] op, input logic [11:0] db, input logic [2:0] rs, input logic [1:0] id,
                  input logic [15:0] be, input logic [127:0] d);
  @(negedge clk); #1;
  wdat_flitv = 1; wdat_opcode = op; wdat_txnid = db; wdat_resp = rs; wdat_dataid = id; wdat_be = be; wdat_data = d;
  g_wdat--;
  @(negedge clk); #1 wdat_flitv = 0;
endtask
task automatic line_wr(input logic [3:0] op, input logic [11:0] db, input logic [2:0] rs, input logic [63:0] be,
                       input logic [511:0] d);
  for (int b = 0; b < 4; b++) wd(op, db, rs, b, be[16*b +: 16], d[128*b +: 128]);
endtask
task automatic ack(input logic [11:0] db);
  @(negedge clk); #1;
  srsp_flitv = 1; srsp_opcode = 5'h2; srsp_txnid = db; g_srsp--;
  @(negedge clk); #1 srsp_flitv = 0;
endtask

function automatic logic [511:0] init_line(input int l);
  logic [511:0] v;
  for (int j = 0; j < 16; j++) v[32*j +: 32] = 32'hC0DE_0000 | (l * 16 + j);
  return v;
endfunction

// the last four CompData beats as one line
function automatic logic [511:0] last_line();
  logic [511:0] v;
  for (int b = 0; b < 4; b++) v[128 * d_id[(nd - 4 + b) % 256] +: 128] = d_dat[(nd - 4 + b) % 256];
  return v;
endfunction

int r0, d0, p0;
task automatic mark(); r0 = nr; d0 = nd; p0 = nperr; endtask
// a read: four beats with TxnID txn, resp rs, err er, then (if ack) CompAck with the DBID
task automatic rd(input logic [6:0] op, input logic [11:0] txn, input logic [43:0] a, input bit ak,
                  input logic [2:0] rs, input logic [1:0] er, input logic [511:0] exp, input string msg);
  bit ok;
  mark();
  req(op, txn, a, ak);
  idle(10);
  ok = (nd == d0 + 4) && (nr == r0) && (nperr == p0);
  for (int b = 0; b < 4; b++)
    ok &= d_txn[(d0 + b) % 256] == txn && d_rs[(d0 + b) % 256] == rs && d_er[(d0 + b) % 256] == er &&
          d_id[(d0 + b) % 256] == b;
  chk(ok && last_line() == exp, $sformatf("%s: four CompData beats (%0d beats, %0d rsp, %0d errors)", msg,
      nd - d0, nr - r0, nperr - p0));
  if (ak) ack(d_db[(nd - 1) % 256]);
  idle(2);
endtask
// a dataless request: one Comp
task automatic dl(input logic [6:0] op, input logic [11:0] txn, input logic [43:0] a, input bit ak,
                  input logic [2:0] rs, input logic [1:0] er, input string msg);
  mark();
  req(op, txn, a, ak);
  idle(6);
  chk(nr == r0 + 1 && r_op[r0 % 64] == 5'h4 && r_txn[r0 % 64] == txn && r_rs[r0 % 64] == rs && r_er[r0 % 64] == er &&
      nperr == p0 && nd == d0, $sformatf("%s: Comp (op %0h rs %0d er %0d)", msg, r_op[r0 % 64], r_rs[r0 % 64], r_er[r0 % 64]));
  if (ak) ack(r_db[r0 % 64]);
  idle(2);
endtask
// a write: CompDBIDResp, then the line
task automatic wr(input logic [6:0] op, input logic [11:0] txn, input logic [43:0] a, input logic [3:0] dop,
                  input logic [2:0] rs, input logic [63:0] be, input logic [511:0] d, input logic [1:0] er,
                  input string msg);
  mark();
  req(op, txn, a, 0);
  idle(6);
  chk(nr == r0 + 1 && r_op[r0 % 64] == 5'h5 && r_txn[r0 % 64] == txn && r_er[r0 % 64] == er && r_db[r0 % 64] < 2 &&
      nperr == p0, $sformatf("%s: CompDBIDResp (op %0h er %0d)", msg, r_op[r0 % 64], r_er[r0 % 64]));
  line_wr(dop, r_db[r0 % 64], rs, be, d);
  idle(2);
  chk(nperr == p0, $sformatf("%s: data accepted", msg));
endtask
// a request refused as a protocol error: Comp NDERR with DBID FFF
task automatic bad(input logic [6:0] op, input logic [11:0] txn, input logic [43:0] a, input bit ak, input bit ar,
                   input logic [3:0] pt, input logic [2:0] sz, input logic [2:0] code, input string msg);
  mark();
  req(op, txn, a, ak, ar, pt, sz);
  idle(6);
  chk(nperr == p0 + 1 && lcode == code && nr == r0 + 1 && r_op[r0 % 64] == 5'h4 && r_er[r0 % 64] == 2'b11 &&
      r_db[r0 % 64] == 12'hFFF && r_txn[r0 % 64] == txn && nd == d0,
      $sformatf("%s: protocol error %0d (got %0d, %0d errors)", msg, code, lcode, nperr - p0));
endtask

logic [511:0] pat, exp_l;
int db0, db1;
initial begin
  idle(3);
  chk(!crsp_flitv && !rdat_flitv && !req_lcrdv && !proto_err, "reset values");
  // a flit on the first clock out of reset, before any credit
  rst_n = 1; req_flitv = 1; req_opcode = 7'h04; req_txnid = 1; req_size = 6; req_allowretry = 1; @(posedge clk); #1;
  req_flitv = 0;
  idle(1);
  chk(nperr == 1 && lcode == 1, "REQ flit before an L-credit: error 1");
  idle(6);
  chk(g_req == 2 && g_wdat == 2 && g_srsp == 2, $sformatf("two L-credits per inbound channel (%0d %0d %0d)", g_req, g_wdat, g_srsp));
  chk(nr == 0 && nd == 0, "the flit without credit was dropped");

  // no RXDAT credit yet: the data waits
  mark();
  hold = 1;
  req(7'h04, 12'd2, 44'h0, 0);
  idle(8);
  chk(nd == d0 && g_req == 2, "no CompData before we grant RXDAT credits; REQ credit returned");
  owe_rdat = 2; owe_crsp = 4; idle(8);
  chk(nd == d0 + 2, $sformatf("two RXDAT credits: two beats (%0d)", nd - d0));
  owe_rdat = 6; idle(6);
  chk(nd == d0 + 4 && last_line() == init_line(0), "ReadNoSnp: the rest of the line");
  chk(d_db[d0 % 256] == 0 && d_rs[d0 % 256] == 3'b000 && d_er[d0 % 256] == 2'b00, "ReadNoSnp: DBID 0, I, OK");
  hold = 0;

  // reads
  rd(7'h04, 12'd3, 44'h040, 0, 3'b000, 2'b00, init_line(1), "ReadNoSnp line 1");
  rd(7'h03, 12'd4, 44'h080, 0, 3'b000, 2'b00, init_line(2), "ReadOnce");
  rd(7'h03, 12'd5, 44'h0C0, 1, 3'b000, 2'b00, init_line(3), "ReadOnce with CompAck");
  rd(7'h01, 12'd6, 44'h100, 1, 3'b001, 2'b00, init_line(4), "ReadShared: SC");
  rd(7'h02, 12'd7, 44'h140, 1, 3'b001, 2'b00, init_line(5), "ReadClean: SC");
  rd(7'h07, 12'd8, 44'hFC0, 1, 3'b010, 2'b00, init_line(63), "ReadUnique line 63: UC");
  rd(7'h04, 12'd9, 44'h1000, 0, 3'b000, 2'b10, 512'h0, "ReadNoSnp above 4 KB: DERR, no data");
  rd(7'h07, 12'd10, 44'h0800_0000_1040, 1, 3'b010, 2'b10, 512'h0, "ReadUnique far above 4 KB: DERR");

  // dataless
  dl(7'h08, 12'd11, 44'h040, 0, 3'b000, 2'b00, "CleanShared");
  dl(7'h09, 12'd12, 44'h040, 0, 3'b000, 2'b00, "CleanInvalid");
  dl(7'h0A, 12'd13, 44'h040, 0, 3'b000, 2'b00, "MakeInvalid");
  dl(7'h0D, 12'd14, 44'h040, 0, 3'b000, 2'b00, "Evict");
  dl(7'h0B, 12'd15, 44'h040, 1, 3'b010, 2'b00, "CleanUnique: UC");
  dl(7'h0C, 12'd16, 44'h040, 1, 3'b010, 2'b00, "MakeUnique: UC");
  dl(7'h08, 12'd17, 44'h2040, 0, 3'b000, 2'b11, "CleanShared above 4 KB: NDERR");
  dl(7'h0B, 12'd18, 44'h2040, 1, 3'b010, 2'b11, "CleanUnique above 4 KB: NDERR, still waits for CompAck");
  dl(7'h08, 12'd17, 44'h040, 1, 3'b000, 2'b00, "CleanShared with ExpCompAck waits for CompAck");

  // writes
  for (int j = 0; j < 16; j++) pat[32*j +: 32] = 32'hA5A5_0000 + j * 32'h0101;
  wr(7'h1D, 12'd20, 44'h200, 4'h3, 3'b000, '1, pat, 2'b00, "WriteNoSnpFull line 8");
  rd(7'h04, 12'd21, 44'h200, 0, 3'b000, 2'b00, pat, "read back line 8");
  wr(7'h1C, 12'd22, 44'h200, 4'h3, 3'b000, 64'h8000_0001_0000_00F0, '1, 2'b00, "WriteNoSnpPtl");
  exp_l = pat;
  for (int k = 0; k < 64; k++) if (k inside {4, 5, 6, 7, 32, 63}) exp_l[8*k +: 8] = 8'hFF;
  rd(7'h04, 12'd23, 44'h200, 0, 3'b000, 2'b00, exp_l, "partial write merged by byte enable");
  wr(7'h19, 12'd24, 44'h240, 4'h3, 3'b000, '1, ~pat, 2'b00, "WriteUniqueFull line 9");
  wr(7'h18, 12'd25, 44'h240, 4'h3, 3'b000, 64'h0, pat, 2'b00, "WriteUniquePtl with no byte enabled");
  rd(7'h03, 12'd26, 44'h240, 0, 3'b000, 2'b00, ~pat, "line 9 unchanged by the empty partial write");
  wr(7'h1B, 12'd27, 44'h280, 4'h2, 3'b110, '1, pat ^ 1, 2'b00, "WriteBackFull UD_PD line 10");
  rd(7'h04, 12'd28, 44'h280, 0, 3'b000, 2'b00, pat ^ 1, "copy-back written");
  wr(7'h1B, 12'd29, 44'h280, 4'h2, 3'b000, '1, 512'h0, 2'b00, "WriteBackFull with resp I");
  rd(7'h04, 12'd30, 44'h280, 0, 3'b000, 2'b00, pat ^ 1, "lost copy-back writes nothing");
  wr(7'h17, 12'd31, 44'h2C0, 4'h2, 3'b001, '1, pat ^ 2, 2'b00, "WriteCleanFull SC");
  wr(7'h15, 12'd32, 44'h300, 4'h2, 3'b010, '1, pat ^ 3, 2'b00, "WriteEvictFull UC");
  rd(7'h04, 12'd33, 44'h2C0, 0, 3'b000, 2'b00, pat ^ 2, "WriteCleanFull written");
  rd(7'h04, 12'd34, 44'h300, 0, 3'b000, 2'b00, pat ^ 3, "WriteEvictFull written");
  wr(7'h1D, 12'd35, 44'h1300, 4'h3, 3'b000, '1, pat, 2'b11, "WriteNoSnpFull above 4 KB: NDERR");
  rd(7'h04, 12'd36, 44'h300, 0, 3'b000, 2'b00, pat ^ 3, "out-of-range write does not alias line 12");

  // write data errors
  mark();
  req(7'h1D, 12'd37, 44'h340, 0); idle(6);
  db0 = r_db[r0 % 64];
  wd(4'h2, db0, 3'b110, 0, '1, '1); idle(2);
  chk(nperr == p0 + 1 && lcode == 6, "CopyBackWrData for a WriteNoSnp: error 6");
  wd(4'h3, db0 ^ 1, 3'b000, 0, '1, '1); idle(2);
  chk(nperr == p0 + 2 && lcode == 6, "write data for a DBID not waiting: error 6");
  wd(4'h3, 12'h800, 3'b000, 0, '1, '1); idle(2);
  chk(nperr == p0 + 3 && lcode == 6, "write data for DBID 800: error 6");
  line_wr(4'h3, db0, 3'b000, '1, pat); idle(2);
  chk(nperr == p0 + 3, "then the right data completes the write");
  mark();
  req(7'h1B, 12'd38, 44'h340, 0); idle(6);
  wd(4'h3, r_db[r0 % 64], 3'b000, 0, '1, '1); idle(2);
  chk(nperr == p0 + 1 && lcode == 6, "NonCopyBackWrData for a WriteBack: error 6");
  line_wr(4'h2, r_db[r0 % 64], 3'b110, '1, ~pat); idle(2);
  rd(7'h04, 12'd39, 44'h340, 0, 3'b000, 2'b00, ~pat, "beats in any order");
  ack(12'd0); idle(2);
  chk(nperr == p0 + 1 && lcode == 6, "CompAck with no tracker waiting: error 6");
  mark();
  @(negedge clk); #1 srsp_flitv = 1; srsp_opcode = 5'h1; srsp_txnid = 0; g_srsp--; @(negedge clk); #1 srsp_flitv = 0; idle(2);
  chk(nperr == p0 + 1 && lcode == 6, "TXRSP opcode other than CompAck: error 6");

  // request errors
  bad(7'h04, 12'd40, 44'h040, 0, 1, 0, 3'd5, 3'd3, "Size 32 bytes");
  bad(7'h1D, 12'd41, 44'h060, 0, 1, 0, 3'd6, 3'd3, "address not line aligned");
  bad(7'h04, 12'd42, 44'h041, 0, 1, 0, 3'd6, 3'd3, "address bit 0 set");
  bad(7'h01, 12'd43, 44'h040, 0, 1, 0, 3'd6, 3'd4, "ReadShared without ExpCompAck");
  bad(7'h02, 12'd44, 44'h040, 0, 1, 0, 3'd6, 3'd4, "ReadClean without ExpCompAck");
  bad(7'h07, 12'd45, 44'h040, 0, 1, 0, 3'd6, 3'd4, "ReadUnique without ExpCompAck");
  bad(7'h0B, 12'd46, 44'h040, 0, 1, 0, 3'd6, 3'd4, "CleanUnique without ExpCompAck");
  bad(7'h0C, 12'd47, 44'h040, 0, 1, 0, 3'd6, 3'd4, "MakeUnique without ExpCompAck");
  bad(7'h04, 12'd48, 44'h040, 0, 0, 1, 3'd6, 3'd5, "AllowRetry 0 without a P-credit");
  bad(7'h00, 12'd49, 44'h040, 0, 1, 0, 3'd6, 3'd7, "opcode 00");
  bad(7'h05, 12'd49, 44'h040, 0, 1, 0, 3'd6, 3'd7, "opcode 05");
  bad(7'h06, 12'd49, 44'h040, 0, 1, 0, 3'd6, 3'd7, "opcode 06");
  bad(7'h0E, 12'd49, 44'h040, 0, 1, 0, 3'd6, 3'd7, "opcode 0E");
  bad(7'h14, 12'd49, 44'h040, 0, 1, 0, 3'd6, 3'd7, "opcode 14");
  bad(7'h16, 12'd49, 44'h040, 0, 1, 0, 3'd6, 3'd7, "opcode 16");
  bad(7'h1A, 12'd49, 44'h040, 0, 1, 0, 3'd6, 3'd7, "opcode 1A");
  bad(7'h1E, 12'd49, 44'h040, 0, 1, 0, 3'd6, 3'd7, "opcode 1E");
  bad(7'h7F, 12'd49, 44'h040, 0, 1, 0, 3'd5, 3'd7, "opcode 7F before the size check");
  bad(7'h01, 12'd49, 44'h041, 0, 1, 0, 3'd6, 3'd3, "size before ExpCompAck");

  // trackers, TxnID, retry and P-credits
  mark();
  req(7'h07, 12'd50, 44'h000, 1); req(7'h07, 12'd51, 44'h040, 1); idle(14);
  chk(nd == d0 + 8 && nperr == p0, "two ReadUniques hold both trackers");
  db0 = d_db[d0 % 256]; db1 = d_db[(d0 + 4) % 256];
  chk(db0 != db1 && db0 < 2 && db1 < 2, "distinct DBIDs");
  bad(7'h04, 12'd50, 44'h080, 0, 1, 0, 3'd6, 3'd2, "TxnID 50 still outstanding");
  mark();
  req(7'h04, 12'd52, 44'h080, 0); idle(6);
  chk(nr == r0 + 1 && r_op[r0 % 64] == 5'h3 && r_txn[r0 % 64] == 12'd52 && r_pt[r0 % 64] == 4'd1 && nd == d0,
      "no tracker: RetryAck with PCrdType 1");
  req(7'h04, 12'd53, 44'h0C0, 0); idle(6);
  chk(nr == r0 + 2 && r_op[(r0 + 1) % 64] == 5'h3, "a second RetryAck");
  bad(7'h04, 12'd52, 44'h080, 0, 0, 1, 3'd6, 3'd5, "re-sent before the grant");
  mark();
  ack(db0); idle(6);
  chk(nr == r0 + 1 && r_op[r0 % 64] == 5'h7 && r_pt[r0 % 64] == 4'd1, "CompAck frees a tracker: PCrdGrant");
  req(7'h04, 12'd54, 44'h100, 0); idle(6);
  chk(nr == r0 + 2 && r_op[(r0 + 1) % 64] == 5'h3 && nd == d0, "the freed tracker is reserved: RetryAck");
  bad(7'h04, 12'd52, 44'h080, 0, 0, 2, 3'd6, 3'd5, "PCrdType 2 does not match the grant");
  mark();
  req(7'h04, 12'd52, 44'h080, 0, 0, 1); idle(10);
  chk(nd == d0 + 4 && d_txn[d0 % 256] == 12'd52 && last_line() == init_line(2) && nperr == p0,
      "re-sent with AllowRetry 0: served on the reserved tracker");
  mark();
  ack(db1); idle(4);
  chk(nr == r0 + 1 && r_op[r0 % 64] == 5'h7, "next free tracker: grant for the second retry");
  req(7'h04, 12'd53, 44'h0C0, 0, 0, 1); idle(10);
  chk(nd == d0 + 4 && d_txn[d0 % 256] == 12'd53, "second retried request served");
  mark();
  ack(12'd0); idle(2);
  chk(nperr == p0 + 1, "no tracker left waiting for CompAck");
  // the third grant came when the first re-sent read finished
  idle(4);
  chk(nr == r0, "three retries, three grants: none left");
  req(7'h04, 12'd54, 44'h100, 0, 0, 1); idle(10);
  chk(nd == d0 + 4 && d_txn[d0 % 256] == 12'd54, "third retried request served");
  bad(7'h04, 12'd55, 44'h100, 0, 0, 1, 3'd6, 3'd5, "no P-credit left");
  // both trackers free again: a write and a read in flight together
  mark();
  req(7'h1D, 12'd56, 44'h380, 0); req(7'h04, 12'd57, 44'h3C0, 0); idle(12);
  chk(nr == r0 + 1 && nd == d0 + 4 && d_txn[d0 % 256] == 12'd57, "write waiting for data while a read completes");
  line_wr(4'h3, r_db[r0 % 64], 3'b000, '1, pat); idle(2);
  rd(7'h04, 12'd58, 44'h380, 0, 3'b000, 2'b00, pat, "write with a read in flight");
  // a dataless request without CompAck does not hold a tracker
  mark();
  req(7'h07, 12'd59, 44'h000, 1); req(7'h07, 12'd60, 44'h040, 1); idle(12);
  db0 = d_db[d0 % 256]; db1 = d_db[(d0 + 4) % 256];
  mark();
  req(7'h0D, 12'd61, 44'h080, 0); idle(6);
  chk(nr == r0 + 1 && r_op[r0 % 64] == 5'h3, "Evict while both trackers wait: RetryAck");
  ack(db0); ack(db1); idle(8);
  chk(nr == r0 + 2 && r_op[(r0 + 1) % 64] == 5'h7, "one grant for one retry");
  mark();
  req(7'h0D, 12'd61, 44'h080, 0, 0, 1); idle(6);
  chk(nr == r0 + 1 && r_op[r0 % 64] == 5'h4 && nperr == p0, "retried Evict completes");
  mark();
  req(7'h0D, 12'd62, 44'h080, 0); req(7'h0D, 12'd63, 44'h080, 0); req(7'h0D, 12'd64, 44'h080, 0); idle(8);
  chk(nr == r0 + 3 && r_op[r0 % 64] == 5'h4 && r_op[(r0 + 2) % 64] == 5'h4, "back-to-back Evicts need no tracker");

  // RXRSP queue while we hold the credits back: REQ credits stop before it can overflow
  hold = 1;
  idle(10);
  mark();
  cr0 = gave_crsp - nr;      // RXRSP credits the Home Node still holds
  for (int i = 0; i < 16; i++) if (g_req > 0) begin req(7'h08, 12'd70 + i, 44'h000, 0); nacc++; idle(2); end
  idle(10);
  chk(nr == r0 + cr0 && g_req == 0 && nperr == p0 && nacc == cr0 + 6,
      $sformatf("no RXRSP credit: six Comps queued, REQ credits withheld (%0d sent, %0d accepted)", nr - r0, nacc));
  hold = 0; owe_crsp = 8; idle(20);
  chk(nr == r0 + nacc, $sformatf("queued Comps delivered (%0d)", nr - r0));
  for (int i = 0; i < nacc; i++) chk(r_txn[(r0 + i) % 64] == 12'd70 + i, $sformatf("Comp %0d in order", i));
  chk(g_req == 2, $sformatf("REQ credits granted again (%0d)", g_req));

  // reset clears trackers and credits
  mark();
  req(7'h07, 12'd80, 44'h000, 1); idle(10);
  rst_n = 0; idle(2);
  chk(!crsp_flitv && !rdat_flitv && !req_lcrdv, "reset");
  g_req = 0; g_wdat = 0; g_srsp = 0; owe_crsp = 0; owe_rdat = 0;
  rst_n = 1; idle(8);
  chk(g_req == 2, "credits granted again after reset");
  owe_crsp = 4; owe_rdat = 4; idle(4);
  mark();
  req(7'h04, 12'd80, 44'h380, 0); idle(10);
  chk(nd == d0 + 4 && last_line() == pat && nperr == p0, "after reset: TxnID 80 is free, memory kept");

  if (fails == 0) $display("FUNC_PASS checks=%0d", checks);
  else            $display("FUNC_FAIL checks=%0d fails=%0d", checks, fails);
  $finish;
end

initial begin
  #4000000;
  $display("FUNC_FAIL timeout");
  $finish;
end
"""
