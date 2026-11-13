# DMTF SPDM 1.4 (DSP0274 1.4.1) VIP: an SPDM Responder (the attestation
# endpoint of a PCIe device, reached through its DOE mailbox or MCTP) and a
# Requester agent, at the SPDM message level.
#
# Transport: SPDM messages as byte streams, one byte per clock, last byte
# flagged (the payload a DOE data object or an MCTP message carries; the
# transport headers themselves are out of scope).
#
# tb/top_tb.sv spdm_model is a Responder that supports SPDM 1.4 only and
# reports measurements without signatures (MEAS_CAP = 01b, no CERT / CHAL /
# KEY_EX / CHUNK). It follows DSP0274:
#   GET_VERSION (10.2): SPDMVersion 0x10 only, 4 bytes; VERSION lists 1.4
#     (entry 0x1400). A valid GET_VERSION clears the connection state; an
#     invalid one does not change it and gets an ERROR with SPDMVersion 0x10.
#   Before VERSION every other request gets ERROR UnexpectedRequest. After
#   it, every request must carry SPDMVersion 0x14, else VersionMismatch.
#   GET_CAPABILITIES (10.3), 20 bytes, after VERSION: InvalidRequest when
#   Param1 bit 0 (Supported Algorithms block: needs CHUNK_CAP) is set, when
#   DataTransferSize < MinDataTransferSize (42), when MaxSPDMmsgSize <
#   DataTransferSize, or when the Requester has no CHUNK_CAP and the two
#   differ. CAPABILITIES: CTExponent 12, Flags MEAS_CAP = 01b,
#   DataTransferSize = MaxSPDMmsgSize = 64.
#   NEGOTIATE_ALGORITHMS (10.4), after CAPABILITIES: Length must equal the
#   message size (at least 32). ALGORITHMS (36 bytes, no algorithm structure
#   tables): MeasurementSpecificationSel = DMTF if the Requester offers it,
#   MeasurementHashAlgo = Raw Bit Stream Only (bit 0) then, else 0;
#   BaseAsymSel = BaseHashSel = PqcAsymSel = 0 (no signing or hashing).
#   Retries (17): an identical GET_CAPABILITIES / NEGOTIATE_ALGORITHMS gets
#   the same response again; a non-identical one, or one out of order, gets
#   UnexpectedRequest.
#   GET_MEASUREMENTS (10.11), after ALGORITHMS with DMTF selected, 12 bytes
#   (no Nonce / SlotIDParam, 8-byte Context): SignatureRequested is an
#   InvalidRequest (the Requester shall use 0 when MEAS_CAP = 01b), Param2 0
#   returns the number of indices (3) in Param1, 1..3 one block, 0xFF all,
#   any other index InvalidRequest. Blocks (Table 59 / 60, raw bit streams):
#   1 immutable ROM (4 bytes), 2 mutable firmware (8), 3 firmware version (2).
#   MEASUREMENTS carries a 32-byte Nonce (xorshift32 from 0x5EED1234, 8 words
#   per response), OpaqueDataLength 0 and the request's Context.
#   A response longer than the Requester's MaxSPDMmsgSize is replaced by
#   ERROR ResponseTooLarge with ActualSize (Table 69); a request longer than
#   64 bytes gets RequestTooLarge; any other request code gets
#   UnsupportedRequest with the code in Param2, except RESPOND_IF_READY,
#   which gets UnexpectedRequest (this Responder never answers
#   ResponseNotReady). A message of fewer than 2 bytes is silently discarded.
#   Request bytes that arrive while a response is being sent are dropped and
#   pulse err.

SPDM_DEFS = """
localparam bit [7:0] SPDM_V10 = 8'h10, SPDM_V14 = 8'h14;
localparam bit [7:0] SPDM_GET_VERSION = 8'h84, SPDM_GET_CAPS = 8'hE1, SPDM_NEG_ALGS = 8'hE3, SPDM_GET_MEAS = 8'hE0;
localparam bit [7:0] SPDM_ERROR = 8'h7F;
localparam bit [7:0] SPDM_E_INVALID = 8'h01, SPDM_E_UNEXPECTED = 8'h04, SPDM_E_UNSUPPORTED = 8'h07,
                     SPDM_E_RSP_TOO_LARGE = 8'h0D, SPDM_E_REQ_TOO_LARGE = 8'h0E, SPDM_E_VERSION = 8'h41;
"""

SPEC = dict(
    vip="SPDM-UVM-VIP", p="spdm", P="SPDM", dir="spdm", family="Security",
    desc="DMTF SPDM 1.4 (DSP0274) VIP for PCIe device attestation: Responder model with GET_VERSION, "
         "GET_CAPABILITIES, NEGOTIATE_ALGORITHMS and unsigned GET_MEASUREMENTS (DMTF raw measurement blocks, "
         "Nonce, Context), the connection-state and retry rules and the ERROR codes (UnexpectedRequest, "
         "VersionMismatch, InvalidRequest, UnsupportedRequest, ResponseTooLarge, RequestTooLarge); Requester agent.",
    about="""
SPDM is how a PCIe device (through its DOE mailbox) or an MCTP endpoint
proves what firmware it runs. This VIP works at the SPDM message level: the
DUT model is a Responder that supports SPDM 1.4 and reports its measurements
without signatures, and the agent is the Requester. The agent runs the
version / capabilities / algorithms negotiation (VCA) with valid and broken
fields, retries messages identically and non-identically, sends requests out
of order or with the wrong SPDMVersion, asks for the measurement count, each
measurement block and all of them, requests a signature the Responder cannot
give, sets a MaxSPDMmsgSize too small for the answer, sends oversized and
unsupported requests and restarts the connection with GET_VERSION. The
scoreboard runs its own copy of the Responder and predicts every response
byte, including the Nonce sequence. Certificates, CHALLENGE, signed
measurements, sessions and the Large SPDM message (chunking) mechanism are
out of scope, as are the DOE and MCTP transport headers.""",
    defs=SPDM_DEFS,
    timeout=200000,
    cfg="""int unsigned wait_rsp = 40;    // clocks to wait for a response to start before calling it discarded""",
    ports=[
        ("in", "logic", "req_valid"), ("in", "logic [7:0]", "req_data"), ("in", "logic", "req_last"),
        ("out", "logic", "rsp_valid"), ("out", "logic [7:0]", "rsp_data"), ("out", "logic", "rsp_last"),
        ("out", "logic", "err"),
    ],
    fields=[
        ("bit [7:0]", "rq", "req", "q"),       # the request message
        ("bit [7:0]", "rs", "rsp", "q"),       # the response message (empty: discarded)
        ("bit [3:0]", "kind", "info", "rand"),
        ("bit [7:0]", "p", "info", "rand"),
        ("bit [31:0]", "seed", "info", "rand"),
    ],
    constraints="""
constraint c_kind { kind dist { 0 := 2, 1 := 3, 2 := 3, 3 := 6, 4 := 2, 5 := 2, 6 := 1, 7 := 1 }; kind <= 7; }
""",
    tr_functions="""
// message builders (little-endian multi-byte fields, as DSP0274 requires)
function void get_version(bit [7:0] v = SPDM_V10, int extra = 0);
  rq.delete(); rq = '{v, SPDM_GET_VERSION, 8'h00, 8'h00};
  repeat (extra) rq.push_back(8'h00);
endfunction
function void get_caps(bit [7:0] v = SPDM_V14, bit [31:0] dts = 64, bit [31:0] mx = 64, bit chunk = 0,
                       bit [7:0] p1 = 0, int len = 20);
  bit [31:0] fl = {14'h0, chunk, 17'h0};
  rq.delete();
  rq = '{v, SPDM_GET_CAPS, p1, 8'h00, 8'h00, 8'd10, 8'h00, 8'h00,
         fl[7:0], fl[15:8], fl[23:16], fl[31:24], dts[7:0], dts[15:8], dts[23:16], dts[31:24],
         mx[7:0], mx[15:8], mx[23:16], mx[31:24]};
  while (rq.size() > len) void'(rq.pop_back());
  while (rq.size() < len) rq.push_back(8'h00);
endfunction
function void neg_algs(bit [7:0] v = SPDM_V14, bit [7:0] mspec = 8'h01, int len = 32, int lfield = -1);
  bit [15:0] l = (lfield < 0) ? 16'(len) : 16'(lfield);
  rq.delete();
  rq = '{v, SPDM_NEG_ALGS, 8'h00, 8'h00, l[7:0], l[15:8], mspec, 8'h00};
  rq.push_back(8'h10); rq.push_back(8'h00); rq.push_back(8'h00); rq.push_back(8'h00);   // BaseAsymAlgo: ECDSA P-256
  rq.push_back(8'h01); rq.push_back(8'h00); rq.push_back(8'h00); rq.push_back(8'h00);   // BaseHashAlgo: SHA-256
  while (rq.size() < len) rq.push_back(8'h00);
endfunction
function void get_meas(bit [7:0] op, bit [7:0] p1 = 0, bit [63:0] ctx = 64'h0, bit [7:0] v = SPDM_V14, int len = 12);
  rq.delete();
  rq = '{v, SPDM_GET_MEAS, p1, op};
  for (int i = 0; i < 8; i++) rq.push_back(ctx[8 * i +: 8]);
  while (rq.size() > len) void'(rq.pop_back());
  while (rq.size() < len) rq.push_back(8'h00);
endfunction
function void raw(bit [7:0] v, bit [7:0] code, int len);
  rq.delete(); rq.push_back(v); rq.push_back(code);
  for (int i = 2; i < len; i++) rq.push_back(8'(i * 37));
  while (rq.size() > len) void'(rq.pop_back());
endfunction
// for coverage
function bit [7:0] rcode(); return (rs.size() >= 2) ? rs[1] : 8'h00; endfunction
function bit [7:0] ecode(); return (rs.size() >= 3 && rs[1] == SPDM_ERROR) ? rs[2] : 8'h00; endfunction
function bit [7:0] qcode(); return (rq.size() >= 2) ? rq[1] : 8'h00; endfunction
function int mop(); return (rs.size() >= 2 && rs[1] == 8'h60 && rq.size() >= 4) ? rq[3] : -1; endfunction
""",
    drv_rsp=False,
    drv_desc="one item per request message: its bytes one per clock (last flagged), then the response until its last "
             "byte, or cfg.wait_rsp clocks without one (a discarded request), then two idle clocks",
    drv_idle="""
vif.drv_cb.req_valid <= 1'b0; vif.drv_cb.req_data <= 8'h00; vif.drv_cb.req_last <= 1'b0;
""",
    drv_item="""
int w = 0;
bit got = 0, done = 0;
foreach (t.rq[i]) begin
  vif.drv_cb.req_valid <= 1'b1;
  vif.drv_cb.req_data  <= t.rq[i];
  vif.drv_cb.req_last  <= (i == t.rq.size() - 1);
  @(vif.drv_cb);
end
vif.drv_cb.req_valid <= 1'b0; vif.drv_cb.req_last <= 1'b0; vif.drv_cb.req_data <= 8'h00;
while (!done) begin
  @(vif.drv_cb);
  if (vif.drv_cb.rsp_valid === 1'b1) begin
    got = 1;
    if (vif.drv_cb.rsp_last === 1'b1) done = 1;
  end else if (!got && ++w >= cfg.wait_rsp) done = 1;
end
repeat (2) @(vif.drv_cb);
""",
    mon_desc="one item per request message, completed by the response message (or by the next request when the "
             "Responder discarded it)",
    mon_run="""
spdm_transaction t = null;
bit in_req = 0;
wait (vif.rst_n === 1'b1);
forever begin
  @(vif.mon_cb);
  if (vif.mon_cb.req_valid === 1'b1) begin
    if (!in_req) begin
      if (t != null) publish(t);            // the previous request got no response
      t = spdm_transaction::type_id::create("t");
      in_req = 1;
    end
    t.rq.push_back(vif.mon_cb.req_data);
    if (vif.mon_cb.req_last === 1'b1) in_req = 0;
  end
  if (vif.mon_cb.rsp_valid === 1'b1 && t != null) begin
    t.rs.push_back(vif.mon_cb.rsp_data);
    if (vif.mon_cb.rsp_last === 1'b1) begin publish(t); t = null; end
  end
end
""",
    sb_members="""// the Responder (scoreboard copy), kept across items
int        st = 0;                     // 0 start, 1 VERSION sent, 2 CAPABILITIES sent, 3 ALGORITHMS sent
bit [7:0]  caps [$], algs [$];
bit [31:0] rmax = 0;
bit        msel = 0;
bit [31:0] ns = 32'h5EED1234;
function void err(ref bit [7:0] r [$], input bit [7:0] v, bit [7:0] code, bit [7:0] d = 8'h00);
  r = '{v, SPDM_ERROR, code, d};
endfunction
function void block(ref bit [7:0] r [$], input int i);
  bit [7:0] val [$];
  case (i)
    1: val = '{8'h12, 8'h34, 8'h56, 8'h78};
    2: val = '{8'hA0, 8'hA1, 8'hA2, 8'hA3, 8'hA4, 8'hA5, 8'hA6, 8'hA7};
    default: val = '{8'h04, 8'h01};
  endcase
  r.push_back(8'(i)); r.push_back(8'h01); r.push_back(8'(3 + val.size())); r.push_back(8'h00);
  r.push_back((i == 1) ? 8'h80 : (i == 2) ? 8'h81 : 8'h86); r.push_back(8'(val.size())); r.push_back(8'h00);
  foreach (val[k]) r.push_back(val[k]);
endfunction
function void respond(bit [7:0] q [$], ref bit [7:0] r [$]);
  int n = q.size();
  r.delete();
  if (n < 2) return;
  if (n > 64) begin err(r, (st == 0 || q[1] == SPDM_GET_VERSION) ? SPDM_V10 : SPDM_V14, SPDM_E_REQ_TOO_LARGE); return; end
  if (q[1] == SPDM_GET_VERSION) begin
    if (q[0] != SPDM_V10) err(r, SPDM_V10, SPDM_E_VERSION);
    else if (n != 4) err(r, SPDM_V10, SPDM_E_INVALID);
    else begin st = 1; caps.delete(); algs.delete(); msel = 0; r = '{SPDM_V10, 8'h04, 8'h00, 8'h00, 8'h00, 8'h01, 8'h00, 8'h14}; end
    return;
  end
  if (st == 0) begin err(r, SPDM_V10, SPDM_E_UNEXPECTED); return; end
  if (q[0] != SPDM_V14) begin err(r, SPDM_V14, SPDM_E_VERSION); return; end
  case (q[1])
    SPDM_GET_CAPS: begin
      bit [31:0] dts = {q[15], q[14], q[13], q[12]}, mx = {q[19], q[18], q[17], q[16]};
      if (st == 3 || (st == 2 && q != caps)) err(r, SPDM_V14, SPDM_E_UNEXPECTED);
      else if (n != 20 || q[2][0] || dts < 42 || mx < dts || (!q[10][1] && mx != dts)) err(r, SPDM_V14, SPDM_E_INVALID);
      else begin
        st = 2; caps = q; rmax = mx;
        r = '{SPDM_V14, 8'h61, 8'h00, 8'h00, 8'h00, 8'd12, 8'h00, 8'h00, 8'h08, 8'h00, 8'h00, 8'h00,
              8'd64, 8'h00, 8'h00, 8'h00, 8'd64, 8'h00, 8'h00, 8'h00};
      end
    end
    SPDM_NEG_ALGS: begin
      if (st == 1 || (st == 3 && q != algs)) err(r, SPDM_V14, SPDM_E_UNEXPECTED);
      else if (n < 32 || {q[5], q[4]} != n) err(r, SPDM_V14, SPDM_E_INVALID);
      else begin
        st = 3; algs = q; msel = q[6][0];
        r = '{SPDM_V14, 8'h63, 8'h00, 8'h00, 8'd36, 8'h00, {7'h0, msel}, 8'h00, {7'h0, msel}};
        while (r.size() < 36) r.push_back(8'h00);
      end
    end
    SPDM_GET_MEAS: begin
      if (st != 3 || !msel) err(r, SPDM_V14, SPDM_E_UNEXPECTED);
      else if (n != 12 || q[2][0] || !(q[3] inside {[0:3], 8'hFF})) err(r, SPDM_V14, SPDM_E_INVALID);
      else begin
        bit [7:0] rec [$];
        int nb = 0;
        if (q[3] == 8'hFF) begin for (int i = 1; i <= 3; i++) block(rec, i); nb = 3; end
        else if (q[3] != 0) begin block(rec, q[3]); nb = 1; end
        r = '{SPDM_V14, 8'h60, (q[3] == 0) ? 8'd3 : 8'h00, 8'h00, 8'(nb), 8'(rec.size()), 8'h00, 8'h00};
        foreach (rec[i]) r.push_back(rec[i]);
        if (r.size() + 42 > rmax) begin
          bit [31:0] a = r.size() + 42;
          err(r, SPDM_V14, SPDM_E_RSP_TOO_LARGE);
          r.push_back(a[7:0]); r.push_back(a[15:8]); r.push_back(a[23:16]); r.push_back(a[31:24]);
        end else begin
          for (int w = 0; w < 8; w++) begin
            ns ^= ns << 13; ns ^= ns >> 17; ns ^= ns << 5;
            for (int b = 0; b < 4; b++) r.push_back(ns[8 * b +: 8]);
          end
          r.push_back(8'h00); r.push_back(8'h00);
          for (int i = 4; i < 12; i++) r.push_back(q[i]);
        end
      end
    end
    8'hFF: err(r, SPDM_V14, SPDM_E_UNEXPECTED);
    default: err(r, SPDM_V14, SPDM_E_UNSUPPORTED, q[1]);
  endcase
endfunction
""",
    predict="""
respond(t.rq, t.rs);
""",
    checks="""
if (t.rs.size() != 0 && t.rs.size() < 4) fail(t, "response shorter than the 4-byte SPDM header");
if (t.rs.size() >= 2 && t.rq.size() >= 2 && t.rs[1] != SPDM_ERROR && t.rs[1] != (t.rq[1] & 8'h7F))
  fail(t, "response code is not the request code with bit 7 cleared");
""",
    coverage="""
cp_req  : coverpoint tr.qcode() { bins version = {8'h84}; bins caps = {8'hE1}; bins algs = {8'hE3}; bins meas = {8'hE0};
                                  bins rir = {8'hFF}; bins other = default; }
cp_rsp  : coverpoint tr.rcode() { bins version = {8'h04}; bins caps = {8'h61}; bins algs = {8'h63}; bins meas = {8'h60};
                                  bins error = {8'h7F}; bins none = {8'h00}; }
cp_err  : coverpoint tr.ecode() { bins invalid = {8'h01}; bins unexpected = {8'h04}; bins unsupported = {8'h07};
                                  bins rsp_large = {8'h0D}; bins req_large = {8'h0E}; bins version = {8'h41}; bins none = {8'h00}; }
cp_mop  : coverpoint tr.mop() { bins count = {0}; bins one[] = {[1:3]}; bins all = {255}; }
cx_req_err : cross cp_req, cp_err {
  ignore_bins na = binsof(cp_req.version) && binsof(cp_err.unsupported);
  ignore_bins na2 = binsof(cp_req.version) && binsof(cp_err.unexpected);
  ignore_bins na3 = binsof(cp_req.rir) && (binsof(cp_err.invalid) || binsof(cp_err.unsupported) || binsof(cp_err.rsp_large));
  ignore_bins na4 = binsof(cp_req.other) && (binsof(cp_err.invalid) || binsof(cp_err.rsp_large));
  ignore_bins na5 = (binsof(cp_req.caps) || binsof(cp_req.algs) || binsof(cp_req.version)) && (binsof(cp_err.unsupported) || binsof(cp_err.rsp_large));
  ignore_bins na6 = binsof(cp_req.meas) && binsof(cp_err.unsupported);
  ignore_bins na7 = (binsof(cp_req.version) || binsof(cp_req.caps) || binsof(cp_req.algs) || binsof(cp_req.meas) || binsof(cp_req.rir)) && binsof(cp_err.req_large);
  ignore_bins na8 = binsof(cp_req.other) && binsof(cp_err.none);
  ignore_bins na9 = binsof(cp_req.rir) && binsof(cp_err.none);
}
""",
    directed="""
// the connection from scratch: out of order, version errors, VCA, retries, every measurement operation,
// size limits, unsupported requests, a restart
t = item(); t.get_caps(); send(t);                                   // before GET_VERSION
t = item(); t.get_version(8'h11); send(t);                           // VersionMismatch
t = item(); t.get_version(SPDM_V10, 1); send(t);                     // 5 bytes: InvalidRequest
t = item(); t.raw(SPDM_V10, 8'hFF, 4); send(t);                      // RESPOND_IF_READY before VERSION
t = item(); t.raw(SPDM_V14, 8'h81, 4); send(t);                      // GET_DIGESTS before VERSION
t = item(); t.get_version(); send(t);
t = item(); t.get_caps(8'h12); send(t);                              // wrong SPDMVersion
t = item(); t.neg_algs(8'h12); send(t);
t = item(); t.get_meas(8'h00, 0, 0, 8'h13); send(t);
t = item(); t.raw(8'h13, 8'h81, 4); send(t);
t = item(); t.raw(SPDM_V10, 8'hFF, 4); send(t);
t = item(); t.neg_algs(); send(t);                                   // before CAPABILITIES
t = item(); t.get_caps(SPDM_V14, 41, 41); send(t);                   // DataTransferSize < 42
t = item(); t.get_caps(SPDM_V14, 64, 64, 0, 8'h01); send(t);         // Supported Algorithms block
t = item(); t.get_caps(SPDM_V14, 64, 63, 1); send(t);                // MaxSPDMmsgSize < DataTransferSize
t = item(); t.get_caps(SPDM_V14, 64, 96, 0); send(t);                // no CHUNK_CAP, sizes differ
t = item(); t.get_caps(SPDM_V14, 64, 64, 0, 0, 19); send(t);         // short
t = item(); t.get_caps(SPDM_V14, 64, 64); send(t);
t = item(); t.get_caps(SPDM_V14, 64, 64); send(t);                   // identical retry
t = item(); t.get_caps(SPDM_V14, 80, 80); send(t);                   // non-identical
t = item(); t.get_meas(8'h00); send(t);                              // before ALGORITHMS
t = item(); t.neg_algs(SPDM_V14, 8'h01, 32, 34); send(t);            // Length field wrong
t = item(); t.neg_algs(SPDM_V14, 8'h01, 30, 30); send(t);            // too short
t = item(); t.neg_algs(); send(t);
t = item(); t.neg_algs(); send(t);                                   // identical retry
t = item(); t.neg_algs(SPDM_V14, 8'h01, 36); send(t);                // non-identical
t = item(); t.get_caps(SPDM_V14, 64, 64); send(t);                   // out of order now
for (int op = 0; op <= 4; op++) begin t = item(); t.get_meas(8'(op), 0, 64'h0102030405060708 + op); send(t); end
t = item(); t.get_meas(8'hFF); send(t);                              // 85 bytes > 64: ResponseTooLarge
t = item(); t.get_meas(8'h01, 8'h01); send(t);                       // SignatureRequested
t = item(); t.get_meas(8'h01, 8'h02); send(t);                       // RawBitStreamRequested
t = item(); t.get_meas(8'h01, 0, 0, SPDM_V14, 11); send(t);          // short
t = item(); t.raw(SPDM_V14, 8'h81, 4); send(t);                      // GET_DIGESTS: unsupported
t = item(); t.raw(SPDM_V14, 8'h83, 40); send(t);                     // CHALLENGE: unsupported
t = item(); t.raw(SPDM_V14, 8'h60, 4); send(t);                      // a response code as a request
t = item(); t.raw(SPDM_V14, 8'hFF, 4); send(t);                      // RESPOND_IF_READY: nothing pending
t = item(); t.raw(SPDM_V14, 8'hE0, 70); send(t);                     // RequestTooLarge
t = item(); t.raw(SPDM_V14, 8'h81, 70); send(t);
t = item(); t.raw(SPDM_V14, 8'hE0, 1); send(t);                      // 1 byte: discarded
t = item(); t.get_meas(8'h03, 0, 64'hFEED); send(t);
// restart with room for every block, and without the DMTF measurement specification
t = item(); t.get_version(); send(t);
t = item(); t.get_meas(8'h01); send(t);                              // state cleared
t = item(); t.get_caps(SPDM_V14, 128, 128); send(t);
t = item(); t.neg_algs(); send(t);
t = item(); t.get_meas(8'hFF, 8'h06, 64'hC0FFEE); send(t);
t = item(); t.get_meas(8'h02); send(t);
t = item(); t.get_version(); send(t);
t = item(); t.get_caps(SPDM_V14, 256, 1024, 1); send(t);
t = item(); t.neg_algs(SPDM_V14, 8'h00); send(t);                    // no DMTF: nothing selected
t = item(); t.get_meas(8'h00); send(t);
""",
    seq_after="""
case (req.kind)
  0: req.get_version((req.p[7:6] == 0) ? 8'h11 : SPDM_V10, (req.p[5:4] == 0) ? 1 : 0);
  1: req.get_caps((req.p[7:5] == 0) ? 8'h13 : SPDM_V14, 32'(40 + req.p[3:0] * 8), 32'(40 + req.p[3:0] * 8 + (req.p[4] ? 16 : 0)), req.p[4]);
  2: req.neg_algs(SPDM_V14, {7'h0, req.p[0]}, 32 + 4 * req.p[2:1], (req.p[7:5] == 0) ? 40 : -1);
  3: req.get_meas((req.p[2:0] == 7) ? 8'hFF : 8'(req.p[2:0] % 5), {7'h0, req.p[7:6] == 0}, {req.seed, req.seed ^ 32'hA5A5});
  4: req.raw(SPDM_V14, 8'h80 | req.p[6:0], 4 + req.p[3:0]);
  5: req.raw(SPDM_V14, 8'hE0, 60 + req.p[3:0]);
  6: req.raw(SPDM_V14, 8'hFF, 4);
  default: req.raw(SPDM_V14, req.p, 1);
endcase
""",
    drain_ns=2000,
    model="""
module spdm_model (
  input  logic       clk,
  input  logic       rst_n,
  input  logic       req_valid,
  input  logic [7:0] req_data,
  input  logic       req_last,
  output logic       rsp_valid,
  output logic [7:0] rsp_data,
  output logic       rsp_last,
  output logic       err
);
  logic [7:0]  q  [0:63];
  logic [7:0]  r  [0:127];
  logic [7:0]  cq [0:19];          // the GET_CAPABILITIES that succeeded
  logic [7:0]  aq [0:63];          // the NEGOTIATE_ALGORITHMS that succeeded
  integer      qn, rn, ri, an, st, i, w, nb, k;
  logic [31:0] rmax, ns, dts, mx, a;
  logic        msel, busy, same;

  task automatic put(input logic [7:0] b); r[rn] = b; rn = rn + 1; endtask
  task automatic error(input logic [7:0] v, input logic [7:0] code, input logic [7:0] d);
    rn = 0; put(v); put(8'h7F); put(code); put(d);
  endtask
  task automatic block(input integer idx);
    put(idx[7:0]); put(8'h01);
    case (idx)
      1: begin put(8'd7);  put(8'h00); put(8'h80); put(8'd4); put(8'h00);
               put(8'h12); put(8'h34); put(8'h56); put(8'h78); end
      2: begin put(8'd11); put(8'h00); put(8'h81); put(8'd8); put(8'h00);
               for (k = 0; k < 8; k = k + 1) put(8'hA0 + k[7:0]); end
      default: begin put(8'd5); put(8'h00); put(8'h86); put(8'd2); put(8'h00); put(8'h04); put(8'h01); end
    endcase
  endtask

  task automatic respond();
    rn = 0;
    if (qn < 2) rn = 0;
    else if (qn > 64) error((st == 0 || q[1] == 8'h84) ? 8'h10 : 8'h14, 8'h0E, 8'h00);
    else if (q[1] == 8'h84) begin
      if (q[0] != 8'h10) error(8'h10, 8'h41, 8'h00);
      else if (qn != 4) error(8'h10, 8'h01, 8'h00);
      else begin
        st = 1; an = 0; msel = 1'b0;
        put(8'h10); put(8'h04); put(8'h00); put(8'h00); put(8'h00); put(8'h01); put(8'h00); put(8'h14);
      end
    end
    else if (st == 0) error(8'h10, 8'h04, 8'h00);
    else if (q[0] != 8'h14) error(8'h14, 8'h41, 8'h00);
    else if (q[1] == 8'hE1) begin
      dts = {q[15], q[14], q[13], q[12]};
      mx  = {q[19], q[18], q[17], q[16]};
      same = (qn == 20);
      for (i = 0; i < 20; i = i + 1) if (i < qn && q[i] != cq[i]) same = 1'b0;
      if (st == 3 || (st == 2 && !same)) error(8'h14, 8'h04, 8'h00);
      else if (qn != 20 || q[2][0] || dts < 42 || mx < dts || (!q[10][1] && mx != dts)) error(8'h14, 8'h01, 8'h00);
      else begin
        st = 2; rmax = mx;
        for (i = 0; i < 20; i = i + 1) cq[i] = q[i];
        put(8'h14); put(8'h61); put(8'h00); put(8'h00); put(8'h00); put(8'd12); put(8'h00); put(8'h00);
        put(8'h08); put(8'h00); put(8'h00); put(8'h00); put(8'd64); put(8'h00); put(8'h00); put(8'h00);
        put(8'd64); put(8'h00); put(8'h00); put(8'h00);
      end
    end
    else if (q[1] == 8'hE3) begin
      same = (qn == an);
      for (i = 0; i < 64; i = i + 1) if (i < qn && q[i] != aq[i]) same = 1'b0;
      if (st == 1 || (st == 3 && !same)) error(8'h14, 8'h04, 8'h00);
      else if (qn < 32 || {q[5], q[4]} != qn) error(8'h14, 8'h01, 8'h00);
      else begin
        st = 3; an = qn; msel = q[6][0];
        for (i = 0; i < 64; i = i + 1) aq[i] = (i < qn) ? q[i] : 8'h00;
        put(8'h14); put(8'h63); put(8'h00); put(8'h00); put(8'd36); put(8'h00); put({7'h0, msel}); put(8'h00);
        put({7'h0, msel});
        while (rn < 36) put(8'h00);
      end
    end
    else if (q[1] == 8'hE0) begin
      if (st != 3 || !msel) error(8'h14, 8'h04, 8'h00);
      else if (qn != 12 || q[2][0] || (q[3] > 8'd3 && q[3] != 8'hFF)) error(8'h14, 8'h01, 8'h00);
      else begin
        nb = (q[3] == 8'hFF) ? 3 : (q[3] == 8'h00) ? 0 : 1;
        put(8'h14); put(8'h60); put((q[3] == 8'h00) ? 8'd3 : 8'h00); put(8'h00); put(nb[7:0]);
        put(8'h00); put(8'h00); put(8'h00);           // MeasurementRecordLength, filled in below
        if (q[3] == 8'hFF) for (i = 1; i <= 3; i = i + 1) block(i);
        else if (q[3] != 8'h00) block(q[3]);
        r[5] = rn - 8;
        if (rn + 42 > rmax) begin
          a = rn + 42;
          error(8'h14, 8'h0D, 8'h00); put(a[7:0]); put(a[15:8]); put(a[23:16]); put(a[31:24]);
        end else begin
          for (w = 0; w < 8; w = w + 1) begin
            ns = ns ^ (ns << 13); ns = ns ^ (ns >> 17); ns = ns ^ (ns << 5);
            put(ns[7:0]); put(ns[15:8]); put(ns[23:16]); put(ns[31:24]);
          end
          put(8'h00); put(8'h00);
          for (i = 4; i < 12; i = i + 1) put(q[i]);
        end
      end
    end
    else if (q[1] == 8'hFF) error(8'h14, 8'h04, 8'h00);
    else error(8'h14, 8'h07, q[1]);
  endtask

  always @(posedge clk or negedge rst_n) begin
    if (!rst_n) begin
      qn = 0; rn = 0; ri = 0; an = 0; st = 0; rmax = 0; ns = 32'h5EED1234; msel = 1'b0; busy = 1'b0;
      rsp_valid <= 1'b0; rsp_data <= 8'h00; rsp_last <= 1'b0; err <= 1'b0;
    end else begin
      err <= 1'b0;
      if (req_valid && busy) err <= 1'b1;          // the Responder is still answering: dropped
      else if (req_valid) begin
        if (qn < 64) q[qn] = req_data;
        qn = qn + 1;
        if (req_last) begin
          respond();
          qn = 0; ri = 0;
          busy = (rn > 0);
        end
      end
      if (busy) begin
        rsp_valid <= 1'b1; rsp_data <= r[ri]; rsp_last <= (ri == rn - 1);
        ri = ri + 1;
        if (ri == rn) busy = 1'b0;
      end else begin
        rsp_valid <= 1'b0; rsp_data <= 8'h00; rsp_last <= 1'b0;
      end
    end
  end
endmodule
""",
    sva="""
// outputs are never X out of reset
assert property (@(posedge clk) disable iff (!rst_n) !$isunknown({rsp_valid, rsp_last, err}))
  else $error("SPDM: X on rsp_valid / rsp_last / err");
assert property (@(posedge clk) disable iff (!rst_n) rsp_valid |-> !$isunknown(rsp_data))
  else $error("SPDM: X on response data");
// a response follows the last byte of a request, without gaps, and ends once
assert property (@(posedge clk) disable iff (!rst_n) $rose(rsp_valid) |-> $past(req_valid && req_last))
  else $error("SPDM: response without a request");
assert property (@(posedge clk) disable iff (!rst_n) rsp_valid && !rsp_last |=> rsp_valid)
  else $error("SPDM: gap inside a response");
assert property (@(posedge clk) disable iff (!rst_n) rsp_last |-> rsp_valid)
  else $error("SPDM: rsp_last without rsp_valid");
// every response starts with an SPDMVersion of 1.0 or 1.4 (4-byte header, SPDM version)
assert property (@(posedge clk) disable iff (!rst_n) $rose(rsp_valid) |-> rsp_data inside {8'h10, 8'h14})
  else $error("SPDM: response SPDMVersion");
cover property (@(posedge clk) disable iff (!rst_n) err);
cover property (@(posedge clk) disable iff (!rst_n) rsp_valid && rsp_last);
""",
    smoke=r"""
int checks = 0;
int fails  = 0;

logic clk = 1'b0;
logic rst_n = 1'b0;
logic       req_valid = 1'b0, req_last = 1'b0;
logic [7:0] req_data = 8'h00;
wire        rsp_valid, rsp_last, err;
wire  [7:0] rsp_data;

always #5 clk = ~clk;

spdm_model u_dut (.clk(clk), .rst_n(rst_n), .req_valid(req_valid), .req_data(req_data), .req_last(req_last),
                  .rsp_valid(rsp_valid), .rsp_data(rsp_data), .rsp_last(rsp_last), .err(err));

task automatic chk(input bit ok, input string msg);
  checks++;
  if (!ok) begin fails++; $display("  [FAIL] %s", msg); end
endtask

// the response collector
logic [7:0] rb [0:255];
integer rl = 0, nresp = 0, nerr = 0;
logic   rdone = 1'b0;
always @(posedge clk) begin
  if (rsp_valid) begin
    rb[rl] = rsp_data; rl = rl + 1;
    if (rsp_last) begin rdone = 1'b1; nresp = nresp + 1; end
  end
  if (err) nerr = nerr + 1;
end
// the request being built
logic [7:0] m [0:127];
integer ml;
task automatic b(input logic [7:0] x); m[ml] = x; ml = ml + 1; endtask
task automatic b4(input logic [31:0] x); b(x[7:0]); b(x[15:8]); b(x[23:16]); b(x[31:24]); endtask
// send m[0:ml-1] and wait for the response (or 30 quiet clocks)
task automatic xfer();
  integer i, wq;
  rl = 0; rdone = 1'b0;
  for (i = 0; i < ml; i++) begin
    @(negedge clk); req_valid = 1'b1; req_data = m[i]; req_last = (i == ml - 1);
  end
  @(negedge clk); req_valid = 1'b0; req_last = 1'b0;
  wq = 0;
  while (!rdone && wq < 30) begin @(negedge clk); if (rl == 0) wq = wq + 1; end
  @(negedge clk);
endtask
function automatic bit is_err(input logic [7:0] v, input logic [7:0] code, input logic [7:0] d = 8'h00);
  is_err = rl == 4 && rb[0] == v && rb[1] == 8'h7F && rb[2] == code && rb[3] == d;
endfunction
task automatic get_version(input logic [7:0] v = 8'h10, input integer len = 4);
  ml = 0; b(v); b(8'h84); b(8'h00); b(8'h00); while (ml < len) b(8'h00); xfer();
endtask
task automatic get_caps(input logic [31:0] dts, input logic [31:0] mx, input bit chunk = 0, input logic [7:0] p1 = 0,
                        input logic [7:0] v = 8'h14, input integer len = 20);
  ml = 0; b(v); b(8'hE1); b(p1); b(8'h00); b(8'h00); b(8'd10); b(8'h00); b(8'h00);
  b4({14'h0, chunk, 17'h0}); b4(dts); b4(mx);
  ml = len; xfer();
endtask
task automatic neg_algs(input logic [7:0] mspec = 8'h01, input integer len = 32, input integer lf = -1);
  integer i;
  ml = 0; b(8'h14); b(8'hE3); b(8'h00); b(8'h00);
  b((lf < 0) ? len[7:0] : lf[7:0]); b(8'h00); b(mspec); b(8'h00); b4(32'h10); b4(32'h01);
  while (ml < len) b(8'h00);
  xfer();
endtask
task automatic get_meas(input logic [7:0] op, input logic [7:0] p1 = 0, input logic [63:0] ctx = 0, input integer len = 12);
  integer i;
  ml = 0; b(8'h14); b(8'hE0); b(p1); b(op);
  for (i = 0; i < 8; i++) b(ctx[8 * i +: 8]);
  ml = len; xfer();
endtask
// the Responder's Nonce stream, computed here independently
logic [31:0] xs = 32'h5EED1234;
function automatic bit nonce_ok(input integer at);
  integer wd, j;
  logic [31:0] v;
  nonce_ok = 1;
  for (wd = 0; wd < 8; wd++) begin
    xs = xs ^ (xs << 13); xs = xs ^ (xs >> 17); xs = xs ^ (xs << 5);
    v = {rb[at + 4 * wd + 3], rb[at + 4 * wd + 2], rb[at + 4 * wd + 1], rb[at + 4 * wd]};
    if (v != xs) nonce_ok = 0;
  end
endfunction
integer i;
bit ok;

initial begin
  repeat (3) @(posedge clk);
  #1 chk(rsp_valid === 1'b0 && err === 1'b0, "reset: no response");
  rst_n = 1;
  repeat (2) @(posedge clk);

  // before GET_VERSION
  get_caps(64, 64);
  chk(is_err(8'h10, 8'h04), "GET_CAPABILITIES before GET_VERSION: ERROR UnexpectedRequest (SPDMVersion 1.0)");
  get_version(8'h11);
  chk(is_err(8'h10, 8'h41), "GET_VERSION with SPDMVersion 1.1: ERROR VersionMismatch with SPDMVersion 1.0");
  get_version(8'h10, 5);
  chk(is_err(8'h10, 8'h01), "5-byte GET_VERSION: ERROR InvalidRequest");
  get_caps(64, 64);
  chk(is_err(8'h10, 8'h04), "an invalid GET_VERSION does not start the connection");
  get_version();
  chk(rl == 8 && rb[0] == 8'h10 && rb[1] == 8'h04 && rb[4] == 8'h00 && rb[5] == 8'h01 && rb[6] == 8'h00 && rb[7] == 8'h14,
      "VERSION: SPDMVersion 1.0, one entry 0x1400 (1.4) little-endian");
  // GET_CAPABILITIES
  get_caps(64, 64, 0, 0, 8'h12);
  chk(is_err(8'h14, 8'h41), "GET_CAPABILITIES with SPDMVersion 1.2: VersionMismatch");
  neg_algs();
  chk(is_err(8'h14, 8'h04), "NEGOTIATE_ALGORITHMS before CAPABILITIES: UnexpectedRequest");
  get_caps(41, 41);
  chk(is_err(8'h14, 8'h01), "DataTransferSize 41 < MinDataTransferSize 42: InvalidRequest");
  get_caps(42, 42);
  chk(rl == 20 && rb[1] == 8'h61, "DataTransferSize 42 accepted");
  get_version();
  get_caps(64, 64, 0, 8'h01);
  chk(is_err(8'h14, 8'h01), "Param1 bit 0 (Supported Algorithms) without CHUNK_CAP: InvalidRequest");
  get_caps(64, 63, 1);
  chk(is_err(8'h14, 8'h01), "MaxSPDMmsgSize < DataTransferSize: InvalidRequest");
  get_caps(64, 96, 0);
  chk(is_err(8'h14, 8'h01), "no CHUNK_CAP and MaxSPDMmsgSize != DataTransferSize: InvalidRequest");
  get_caps(64, 64, 0, 0, 8'h14, 19);
  chk(is_err(8'h14, 8'h01), "19-byte GET_CAPABILITIES: InvalidRequest");
  get_caps(64, 64);
  ok = rl == 20 && rb[0] == 8'h14 && rb[1] == 8'h61 && rb[5] == 8'd12 && rb[8] == 8'h08 && rb[9] == 8'h00 &&
       rb[12] == 8'd64 && rb[16] == 8'd64;
  for (i = 2; i < 20; i++) if (i != 5 && i != 8 && i != 12 && i != 16 && rb[i] != 8'h00) ok = 0;
  chk(ok, "CAPABILITIES: CTExponent 12, MEAS_CAP = 01b only, DataTransferSize = MaxSPDMmsgSize = 64");
  get_caps(64, 64);
  chk(rl == 20 && rb[1] == 8'h61, "identical GET_CAPABILITIES retry: CAPABILITIES again");
  get_caps(80, 80);
  chk(is_err(8'h14, 8'h04), "non-identical GET_CAPABILITIES: UnexpectedRequest");
  get_meas(8'h00);
  chk(is_err(8'h14, 8'h04), "GET_MEASUREMENTS before ALGORITHMS: UnexpectedRequest");
  // NEGOTIATE_ALGORITHMS
  neg_algs(8'h01, 32, 34);
  chk(is_err(8'h14, 8'h01), "Length field 34 in a 32-byte request: InvalidRequest");
  neg_algs(8'h01, 30, 30);
  chk(is_err(8'h14, 8'h01), "30-byte NEGOTIATE_ALGORITHMS: InvalidRequest");
  neg_algs();
  ok = rl == 36 && rb[1] == 8'h63 && rb[4] == 8'd36 && rb[5] == 8'h00 && rb[6] == 8'h01 && rb[8] == 8'h01;
  for (i = 9; i < 36; i++) if (rb[i] != 8'h00) ok = 0;
  chk(ok, "ALGORITHMS: Length 36, DMTF, Raw Bit Stream Only, no asymmetric / hash / PQC selection");
  neg_algs();
  chk(rl == 36 && rb[1] == 8'h63, "identical NEGOTIATE_ALGORITHMS retry: ALGORITHMS again");
  neg_algs(8'h01, 36);
  chk(is_err(8'h14, 8'h04), "non-identical NEGOTIATE_ALGORITHMS: UnexpectedRequest");
  get_caps(64, 64);
  chk(is_err(8'h14, 8'h04), "GET_CAPABILITIES after ALGORITHMS: UnexpectedRequest");
  // GET_MEASUREMENTS
  get_meas(8'h00, 0, 64'h1122334455667788);
  chk(rl == 50 && rb[1] == 8'h60 && rb[2] == 8'd3 && rb[3] == 8'h00 && rb[4] == 8'h00 && rb[5] == 8'h00,
      "operation 0: 3 indices in Param1, no blocks, 50 bytes");
  chk(nonce_ok(8), "Nonce: 32 bytes from the Responder's generator");
  chk(rb[40] == 8'h00 && rb[41] == 8'h00 && rb[42] == 8'h88 && rb[49] == 8'h11, "OpaqueDataLength 0, Context echoed");
  get_meas(8'h01, 0, 64'hAB);
  chk(rl == 61 && rb[4] == 8'd1 && rb[5] == 8'd11 && rb[8] == 8'd1 && rb[9] == 8'h01 && rb[10] == 8'd7 && rb[12] == 8'h80 &&
      rb[13] == 8'd4 && rb[15] == 8'h12 && rb[18] == 8'h78, "block 1: DMTF, raw immutable ROM, 4 bytes 12 34 56 78");
  chk(nonce_ok(19), "the Nonce advances per MEASUREMENTS");
  get_meas(8'h03);
  chk(rl == 59 && rb[8] == 8'd3 && rb[12] == 8'h86 && rb[15] == 8'h04 && rb[16] == 8'h01, "block 3: raw firmware version 04 01");
  chk(nonce_ok(17), "Nonce after block 3");
  get_meas(8'h02);
  chk(rl == 8 && rb[1] == 8'h7F && rb[2] == 8'h0D && rb[4] == 8'd65 && rb[5] == 8'h00,
      "block 2 needs 65 bytes > MaxSPDMmsgSize 64: ResponseTooLarge, ActualSize 65");
  get_meas(8'hFF);
  chk(rl == 8 && rb[2] == 8'h0D && rb[4] == 8'd85, "all blocks: 85 bytes, ResponseTooLarge");
  get_meas(8'h04);
  chk(is_err(8'h14, 8'h01), "index 4 does not exist: InvalidRequest");
  get_meas(8'h01, 8'h01);
  chk(is_err(8'h14, 8'h01), "SignatureRequested from a MEAS_CAP = 01b Responder: InvalidRequest");
  get_meas(8'h01, 8'h02);
  chk(rl == 61 && rb[12] == 8'h80, "RawBitStreamRequested: raw block as before");
  chk(nonce_ok(19), "Nonce");
  get_meas(8'h01, 0, 0, 11);
  chk(is_err(8'h14, 8'h01), "11-byte GET_MEASUREMENTS: InvalidRequest");
  // other requests
  ml = 0; b(8'h14); b(8'h81); b(8'h00); b(8'h00); xfer();
  chk(is_err(8'h14, 8'h07, 8'h81), "GET_DIGESTS: UnsupportedRequest naming 0x81");
  ml = 0; b(8'h14); b(8'h60); b(8'h00); b(8'h00); xfer();
  chk(is_err(8'h14, 8'h07, 8'h60), "a response code sent as a request: UnsupportedRequest");
  ml = 0; b(8'h14); b(8'hFF); b(8'h00); b(8'h00); xfer();
  chk(is_err(8'h14, 8'h04), "RESPOND_IF_READY with nothing pending: UnexpectedRequest");
  ml = 0; b(8'h14); b(8'hE0); for (i = 2; i < 65; i++) b(8'h00); xfer();
  chk(is_err(8'h14, 8'h0E), "65-byte request > 64: RequestTooLarge");
  ml = 0; b(8'h14); b(8'h81); for (i = 2; i < 64; i++) b(8'h00); xfer();
  chk(is_err(8'h14, 8'h07, 8'h81), "64-byte request: not too large (UnsupportedRequest for its code)");
  ml = 0; b(8'h14); xfer();
  chk(rl == 0, "1-byte message: silently discarded");
  // a request while the Responder is still answering
  get_meas(8'h03);
  chk(nonce_ok(17), "Nonce");
  ml = 0; b(8'h14); b(8'hE0); b(8'h00); b(8'h03); for (i = 0; i < 8; i++) b(8'h00);
  rl = 0; rdone = 0; nerr = 0;
  for (i = 0; i < ml; i++) begin @(negedge clk); req_valid = 1'b1; req_data = m[i]; req_last = (i == ml - 1); end
  @(negedge clk); req_valid = 1'b1; req_data = 8'h14; req_last = 1'b0;
  @(negedge clk); req_valid = 1'b1; req_data = 8'h84; req_last = 1'b1;
  @(negedge clk); req_valid = 1'b0; req_last = 1'b0;
  repeat (70) @(negedge clk);
  chk(nerr == 2 && nresp > 0 && rl == 59, "bytes during a response: dropped (err), the response is whole");
  chk(nonce_ok(17), "Nonce");
  // restart
  get_version();
  get_meas(8'h01);
  chk(is_err(8'h14, 8'h04), "GET_VERSION clears the connection: GET_MEASUREMENTS is unexpected");
  get_caps(128, 128);
  neg_algs();
  get_meas(8'hFF, 0, 64'hC0FFEE);
  chk(rl == 85 && rb[4] == 8'd3 && rb[5] == 8'd35 && rb[8] == 8'd1 && rb[19] == 8'd2 && rb[34] == 8'd3,
      "MaxSPDMmsgSize 128: all 3 blocks (35-byte record, 85 bytes)");
  chk(nonce_ok(43) && rb[77] == 8'hEE && rb[78] == 8'hFF && rb[79] == 8'hC0, "Nonce and Context after the record");
  get_version();
  get_caps(61, 61);
  neg_algs();
  get_meas(8'h01);
  chk(rl == 61 && rb[1] == 8'h60, "a 61-byte MEASUREMENTS fits MaxSPDMmsgSize 61 exactly");
  chk(nonce_ok(19), "Nonce");
  get_meas(8'h02);
  chk(rl == 8 && rb[2] == 8'h0D && rb[4] == 8'd65, "65 bytes do not");
  get_version();
  get_caps(256, 1024, 1);
  chk(rl == 20 && rb[1] == 8'h61, "CHUNK_CAP Requester: MaxSPDMmsgSize may exceed DataTransferSize");
  neg_algs(8'h00);
  chk(rl == 36 && rb[6] == 8'h00 && rb[8] == 8'h00, "no DMTF offered: no measurement specification or hash selected");
  get_meas(8'h00);
  chk(is_err(8'h14, 8'h04), "no measurement specification: GET_MEASUREMENTS unexpected");

  if (fails == 0) $display("FUNC_PASS checks=%0d", checks);
  else            $display("FUNC_FAIL checks=%0d fails=%0d", checks, fails);
  $finish;
end

initial begin
  #3000000;
  $display("FUNC_FAIL timeout");
  $finish;
end
""",
)
