#!/usr/bin/env python3
# Copyright 2026 VIP Portfolio Contributors
# SPDX-License-Identifier: Apache-2.0
"""run_ip_crosscheck.py [--ip-dir DIR] [--sim iverilog|verilator] [IP ...] --
check open-ip-portfolio RTL against references that do not come from it.

The RTL in open-ip-portfolio is verified there by its own testbenches; this
runner adds a second, independent opinion for the IPs on its TV / STB /
IP-camera plan (CSI-2, Ethernet, HDMI, Crypto, peripherals, DDR). Expected values never come
from the RTL under test:

  * crypto  SHA-256 and HMAC-SHA-256 digests from Python ``hashlib`` (FIPS
            180-4 / RFC 2104), plus the FIPS 180-4 examples and RFC 4231
            test cases 1, 2 and 6 as fixed anchors.
  * eth     IEEE 802.3 frames whose FCS comes from ``zlib.crc32``; MAC
            behaviour (padding, filter, length / CRC / PHY errors, PAUSE)
            from an independent Python model of the documented rules.
  * csi2    CSI-2 packets built here: ECC from the CSI-2 parity equations,
            CRC-16 from a bitwise implementation anchored to the catalogue
            check value (CRC-16/MCRF4XX "123456789" = 0x6F91) and to the two
            checksum examples of the CSI-2 specification.
  * hdmi    a TMDS sink written from the DVI 1.0 / HDMI 1.4 rules decodes
            the serial output (ipcheck/hdmi_xchk_tb.sv); the expected AVI and
            SPD InfoFrames, their checksums and BCH ECC bytes come from this
            script.
  * uart, spi, i2c, gpio, pwm
            the APB wrappers through the register map of docs/ip/<IP>.md,
            with line / bus models written from the protocol rules: an 8N1
            receiver and driver at the nominal baud (+-2.5 %), a mode-0 SPI
            controller, an I2C controller on an open-drain bus with a monitor
            for SDA changes while SCL is high, a GPIO board model, and the
            PWM waveform computed from the documented rule.
  * ddr4, lpddr5x
            DDR4_Lite_top / LPDDR5X_Lite_top through their front-end, with
            ipcheck/ddr_pin_mon.sv on the DRAM pins: the JESD79-4 command
            truth table, the timing rules, burst latency and data against a
            shadow array, refresh intervals. ``[NOTE]`` lines report pin
            encodings that differ from JESD79-4 without changing the data.

Before any RTL runs, the Python references check themselves against the
fixed public vectors (``REF_SELFTEST``) and the SystemVerilog reference
package ``ipcheck/ref/xchk_ref_pkg.sv`` (also shipped in the CSI_2, Ethernet,
HDMI and Security VIPs) is checked against the same vectors
(``ipcheck/ref_selftest_tb.sv``).

The open-ip-portfolio checkout comes from --ip-dir, $OPEN_IP_DIR, or
../open-ip-portfolio next to this repo. Vectors and logs go to
build/ipcheck/<ip>/. Output: ``XCHK_PASS|XCHK_FAIL|XCHK_ERROR <ip> -- detail``
per IP and ``ipcheck_report.csv`` (ip,result,checks,detail).
"""
import os, re, sys, csv, zlib, hmac, random, hashlib, argparse, subprocess, shutil

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
IPCHK = os.path.join(ROOT, "ipcheck")
WORK = os.path.join(ROOT, "build", "ipcheck")
REPORT = os.path.join(ROOT, "ipcheck_report.csv")

# ip -> (open-ip rtl/ files, testbench, other ipcheck/ files)
IPS = {
    "crypto":  (["Crypto___Security_Engine_top.sv"], "crypto_xchk_tb.sv", []),
    "eth":     (["Ethernet_top.sv"], "eth_xchk_tb.sv", []),
    "csi2":    (["CSI_2_top.sv"], "csi2_xchk_tb.sv", []),
    "hdmi":    (["HDMI_2_1_top.sv"], "hdmi_xchk_tb.sv", []),
    "uart":    (["UART_top.sv", "UART_apb.sv"], "uart_xchk_tb.sv", []),
    "spi":     (["SPI_top.sv", "SPI_apb.sv"], "spi_xchk_tb.sv", []),
    "i2c":     (["I2C_top.sv", "I2C_apb.sv"], "i2c_xchk_tb.sv", []),
    "gpio":    (["GPIO_top.sv", "GPIO_apb.sv"], "gpio_xchk_tb.sv", []),
    "pwm":     (["PWM_top.sv", "PWM_apb.sv"], "pwm_xchk_tb.sv", []),
    "ddr4":    (["DDR4_Lite_top.sv"], "ddr_xchk_tb.sv", ["ddr_pin_mon.sv"]),
    "lpddr5x": (["LPDDR5X_Lite_top.sv"], "ddr_xchk_tb.sv", ["ddr_pin_mon.sv"]),
}

# ----------------------------------------------------------------------------
# independent references
# ----------------------------------------------------------------------------
def crc16_csi2(data):
    """CRC-16/MCRF4XX: poly 0x1021 reflected (0x8408), init 0xFFFF, no xorout."""
    c = 0xFFFF
    for b in data:
        c ^= b
        for _ in range(8):
            c = (c >> 1) ^ 0x8408 if c & 1 else c >> 1
    return c

# CSI-2 ECC: parity bit -> data bits it covers (P6 = P7 = 0)
CSI2_P = [
    [0, 1, 2, 4, 5, 7, 10, 11, 13, 16, 20, 21, 22, 23],
    [0, 1, 3, 4, 6, 8, 10, 12, 14, 17, 20, 21, 22, 23],
    [0, 2, 3, 5, 6, 9, 11, 12, 15, 18, 20, 21, 22],
    [1, 2, 3, 7, 8, 9, 13, 14, 15, 19, 20, 21, 23],
    [4, 5, 6, 7, 8, 9, 16, 17, 18, 19, 20, 22, 23],
    [10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 21, 22, 23],
]
def csi2_ecc(d24):
    return sum((sum((d24 >> b) & 1 for b in bits) & 1) << p for p, bits in enumerate(CSI2_P))

def hdmi_bch(bits):
    """HDMI packet ECC: BCH with G(x) = 1 + x^6 + x^7 + x^8, bits LSB first."""
    e = 0
    for b in bits:
        fb = (e ^ b) & 1
        e >>= 1
        if fb:
            e ^= 0x83
    return e

def bits_lsb(bs):
    return [(b >> i) & 1 for b in bs for i in range(8)]

def REF_SELFTEST():
    """Each reference against fixed public values; returns a list of failures."""
    bad = []
    def chk(ok, what):
        if not ok:
            bad.append(what)
    chk(hashlib.sha256(b"abc").hexdigest().startswith("ba7816bf8f01cfea"), "SHA-256 'abc'")
    chk(hashlib.sha256(b"").hexdigest().startswith("e3b0c44298fc1c14"), "SHA-256 ''")
    chk(hmac.new(b"\x0b" * 20, b"Hi There", hashlib.sha256).hexdigest().startswith("b0344c61d8db3853"),
        "RFC 4231 TC1")
    chk(zlib.crc32(b"123456789") == 0xCBF43926, "CRC-32 check value")
    chk(crc16_csi2(b"123456789") == 0x6F91, "CRC-16/MCRF4XX check value")
    # CSI-2 specification checksum examples (24-byte payloads)
    ex1 = bytes.fromhex("FF000002B9DCF372BBD4B85AC875C27C81F805DFFF000001")
    ex2 = bytes.fromhex("FF0000001EF01EC74F8278C582E08C70D23C78E9FF000001")
    chk(crc16_csi2(ex1) == 0x00F0, "CSI-2 CRC example 1")
    chk(crc16_csi2(ex2) == 0xE569, "CSI-2 CRC example 2")
    # CSI-2 ECC: SEC-DED structure (distinct, odd-weight >= 3 data syndromes)
    syn = [csi2_ecc(1 << i) for i in range(24)]
    chk(len(set(syn)) == 24 and all(bin(s).count("1") in (3, 5) for s in syn), "CSI-2 ECC SEC-DED")
    return bad

# ----------------------------------------------------------------------------
# vector writers
# ----------------------------------------------------------------------------
def write_hex(path, vals, width=2):
    with open(path, "w") as f:
        for v in vals:
            f.write("%0*X\n" % (width, v))

def gen_crypto(d, rng):
    """records: mode, len, msg[64], key[64], digest[32]"""
    recs = []
    def add(mode, msg, key=b""):
        if mode and len(key) > 64:
            key = hashlib.sha256(key).digest()           # RFC 2104: hash long keys first
        dg = hmac.new(key, msg, hashlib.sha256).digest() if mode else hashlib.sha256(msg).digest()
        recs.append([mode, len(msg)] + list(msg.ljust(64, b"\0")) + list(key.ljust(64, b"\0")) + list(dg))
    add(0, b"abc")
    add(0, b"")
    add(0, b"abcdbcdecdefdefgefghfghighijhijkijkljklmklmnlmnomnopnopq")
    add(1, b"Hi There", b"\x0b" * 20)                                   # RFC 4231 TC1
    add(1, b"what do ya want for nothing?", b"Jefe")                    # TC2
    add(1, b"Test Using Larger Than Block-Size Key - Hash Key First", b"\xaa" * 131)   # TC6
    for n in [1, 54, 55, 56, 57, 63, 64] + [rng.randrange(65) for _ in range(12)]:
        add(0, bytes(rng.randrange(256) for _ in range(n)))
    for n in [0, 55, 56, 64] + [rng.randrange(65) for _ in range(8)]:
        k = bytes(rng.randrange(256) for _ in range(rng.choice([1, 16, 32, 63, 64])))
        add(1, bytes(rng.randrange(256) for _ in range(n)), k)
    write_hex(os.path.join(d, "vec.hex"), [b for r in recs for b in r])
    return {"NVEC": len(recs)}

def gen_eth(d, rng):
    mac = bytes.fromhex("020000A1B2C3")
    def frame(da, et, plen, payload=None):
        sa = bytes.fromhex("02DEADBEEF01")
        pl = payload if payload is not None else bytes(rng.randrange(256) for _ in range(plen))
        return da + sa + et.to_bytes(2, "big") + pl
    def wire(fr, bad_crc=False):
        body = fr.ljust(60, b"\0")
        fcs = zlib.crc32(body) ^ (0xFFFFFFFF if bad_crc else 0)
        return b"\x55" * 7 + b"\xD5" + body + fcs.to_bytes(4, "little")
    # ---------------- transmit: host frame -> wire bytes
    tx_frames = [frame(mac, 0x0800, n) for n in (46, 10, 0, 47, 100, 1500)]
    tx_frames.append(frame(b"\xff" * 6, 0x8100, 1504))       # VLAN-sized
    tx_in, tx_rec, tx_exp = [], [], []
    for fr in tx_frames:
        w = wire(fr)
        tx_in += list(fr)
        tx_exp += list(w)
        tx_rec += [len(fr) >> 8, len(fr) & 255, len(w) >> 8, len(w) & 255]
    write_hex(os.path.join(d, "tx_in.hex"), tx_in)
    write_hex(os.path.join(d, "tx_exp.hex"), tx_exp)
    write_hex(os.path.join(d, "tx_rec.hex"), tx_rec)
    # ---------------- receive: wire bytes -> host bytes + status
    # stim entries (3 hex digits): 0x100 | byte = dv, 0x200 = er, 0x000 idle,
    # 0x400 = check the frame just sent, 0x7FF end
    rx_stim, rx_rec, rx_exp = [], [], []
    def rx(fr, bad_crc=False, er_at=-1, raw=None, promisc=None):
        w = raw if raw is not None else wire(fr, bad_crc)
        for i, b in enumerate(w):
            rx_stim.append(0x100 | b | (0x200 if i == er_at else 0))
        rx_stim.extend([0] * 14)
        rx_stim.append(0x400)
        # expected behaviour of the documented MAC (independent model)
        if raw is not None:                      # bad preamble / fragment: nothing delivered
            rx_rec.extend([0, 0, 0, 0])
            return
        n = len(w) - 8
        da = w[8:14]
        acc = da == mac or da == b"\xff" * 6 or da == bytes.fromhex("0180C2000001")
        etype = int.from_bytes(w[20:22], "big")
        crc_e = zlib.crc32(w[8:-4]) != int.from_bytes(w[-4:], "little")
        len_e = n < 64 or n > (1522 if etype == 0x8100 else 1518)
        pz = etype == 0x8808 and int.from_bytes(w[22:24], "big") == 1 and n >= 18
        stat = (pz << 3) | ((er_at >= 0) << 2) | (len_e << 1) | crc_e
        if acc:
            data = w[8:-4]
            rx_exp.extend(data)
            rx_rec.extend([1, stat, len(data) >> 8, len(data) & 255])
        else:
            rx_rec.extend([0, 0, 0, 0])
    rx(frame(mac, 0x0800, 46))                                   # minimum frame
    rx(frame(mac, 0x0800, 500))
    rx(frame(b"\xff" * 6, 0x0806, 28))                           # broadcast ARP (padded)
    rx(frame(bytes.fromhex("020000000099"), 0x0800, 64))         # other DA: filtered
    rx(frame(mac, 0x0800, 46), bad_crc=True)                     # FCS error
    rx(frame(mac, 0x0800, 200), er_at=40)                        # PHY error
    rx(frame(mac, 0x0800, 1500))                                 # maximum frame
    rx(frame(mac, 0x0800, 1501))                                 # too long
    rx(frame(mac, 0x8100, 1504))                                 # VLAN maximum (1522)
    rx(frame(mac, 0x8100, 1505))                                 # VLAN too long (1523)
    for n in (20, 59):                                           # runts: 38 and 63 bytes with FCS
        w = b"\x55" * 7 + b"\xD5" + mac + bytes(6) + b"\x08\x00" + bytes(rng.randrange(256) for _ in range(n - 14))
        w = w + zlib.crc32(w[8:]).to_bytes(4, "little")
        for b in w:
            rx_stim.append(0x100 | b)
        rx_stim.extend([0] * 14 + [0x400])
        rx_exp.extend(w[8:-4]); rx_rec.extend([1, 0x2, 0, n])
    rx(None, raw=b"\x55\x55\x55\x12\x34\x56")                   # bad preamble byte
    # PAUSE frame, quanta 3: holds the transmitter 3 x 64 byte times
    rx(frame(bytes.fromhex("0180C2000001"), 0x8808, 0, b"\x00\x01\x00\x03" + bytes(42)))
    rx_stim.append(0x7FF)
    write_hex(os.path.join(d, "rx_stim.hex"), rx_stim, 3)
    write_hex(os.path.join(d, "rx_exp.hex"), rx_exp or [0])
    write_hex(os.path.join(d, "rx_rec.hex"), rx_rec)
    return {"NTX": len(tx_frames), "NRX": len(rx_rec) // 4, "PAUSE_Q": 3}

def gen_csi2(d, rng):
    """stim nibbles: 0 idle, 2/3 = bit 0/1, 8 = checkpoint, F = end;
    expectation record (75 bytes) per checkpoint:
    frame_cnt[2] line_cnt[2] last_dt last_wc[2] err_flags irq lb_len[2] line[64]"""
    stim, exp = [], []
    st = dict(frame=0, line=0, dt=0, wc=0, err=0, irq=0, lb_len=0, buf=bytes(64))
    LINE = 512

    def hdr(di, wc):
        d24 = di | (wc << 8)
        return [di, wc & 255, wc >> 8, csi2_ecc(d24)]

    def burst(pkts, lead=None, trail=True, cut=None):
        """pkts: list of byte lists (each starts with its header); one sync per packet"""
        lead = rng.randrange(8) if lead is None else lead
        bits = [0] * lead
        for p in pkts:
            bits += bits_lsb([0xB8] + p)
        if trail:
            last = bits[-1]
            bits += [1 - last] * 6 + [rng.randrange(2) for _ in range(5)]   # EoT trailer
        if cut is not None:
            bits = bits[:cut]
        stim.extend(2 + b for b in bits)
        stim.extend([0] * 4)

    def checkpoint():
        stim.append(8)
        rec = [st["frame"] >> 8, st["frame"] & 255, st["line"] >> 8, st["line"] & 255, st["dt"],
               st["wc"] >> 8, st["wc"] & 255, st["err"], st["irq"], st["lb_len"] >> 8, st["lb_len"] & 255]
        exp.extend(rec + list(st["buf"].ljust(64, b"\0")[:64]))

    # model of a received packet per the CSI-2 rules the IP documents
    def short(dt, data, vc=0, flip=()):
        h = hdr((vc << 6) | dt, data)
        for f in flip:
            h[f // 8] ^= 1 << (f % 8)
        return h

    def accept_short(dt, data, vc=0, corrected=False):
        st["dt"] = (vc << 6) | dt
        st["wc"] = data
        st["irq"] = 0
        if dt == 0:
            st["frame"] += 1; st["line"] = 0; st["err"] = 8 if corrected else 0
        elif corrected:
            st["err"] |= 8

    def long_pkt(dt, payload, vc=0, bad_crc=False, flip=()):
        h = hdr((vc << 6) | dt, len(payload))
        for f in flip:
            h[f // 8] ^= 1 << (f % 8)
        c = crc16_csi2(payload) ^ (0x1234 if bad_crc else 0)
        return h + list(payload) + [c & 255, c >> 8]

    def accept_long(dt, payload, vc=0, bad_crc=False, corrected=False):
        st["dt"] = (vc << 6) | dt
        st["wc"] = len(payload)
        if corrected:
            st["err"] |= 8
        if bad_crc:
            st["irq"] = 1; st["err"] |= 1
        else:
            st["irq"] = 0; st["line"] += 1
            st["lb_len"] = min(len(payload), LINE)
            st["buf"] = bytes(payload[:64])

    def pay(n):
        return bytes(rng.randrange(256) for _ in range(n))

    # frame start, three RAW8 lines (DT 0x2A), frame end
    burst([short(0x00, 1)]); accept_short(0x00, 1); checkpoint()
    for n in (64, 37, 1):
        p = pay(n)
        burst([long_pkt(0x2A, p)]); accept_long(0x2A, p); checkpoint()
    burst([short(0x01, 1)]); accept_short(0x01, 1); checkpoint()
    # frame 2: virtual channel 2, line longer than the buffer, two packets per burst
    burst([short(0x00, 2, vc=2)]); accept_short(0x00, 2, vc=2); checkpoint()
    p = pay(600)
    burst([long_pkt(0x2B, p, vc=2)]); accept_long(0x2B, p, vc=2); checkpoint()
    p1, p2 = pay(20), pay(33)
    burst([long_pkt(0x2A, p1), long_pkt(0x2A, p2)]); accept_long(0x2A, p1); accept_long(0x2A, p2); checkpoint()
    # CRC error: line not counted, buffer keeps the last good line, irq
    p = pay(48)
    burst([long_pkt(0x2A, p, bad_crc=True)]); accept_long(0x2A, p, bad_crc=True); checkpoint()
    # single-bit header error in a data bit: corrected, the packet is used
    for bit in (0, 5, 13, 23):
        p = pay(16)
        burst([long_pkt(0x2A, p, flip=(bit,))]); accept_long(0x2A, p, corrected=True); checkpoint()
    # single-bit error in the ECC byte: data fine, flagged as corrected
    p = pay(16)
    burst([long_pkt(0x2A, p, flip=(26,))]); accept_long(0x2A, p, corrected=True); checkpoint()
    # double-bit header error: dropped, irq, ECC flag; registers unchanged
    p = pay(16)
    burst([long_pkt(0x2A, p, flip=(2, 9))]); st["irq"] = 1; st["err"] |= 2; checkpoint()
    # burst cut inside a packet
    p = pay(30)
    burst([long_pkt(0x2A, p)], lead=3, trail=False, cut=3 + 8 * (1 + 4 + 10))
    st["dt"] = 0x2A; st["wc"] = 30; st["err"] |= 4; checkpoint()
    # frame end, then a new frame start clears the flags; FS with a corrected error
    burst([short(0x01, 2, vc=2)]); accept_short(0x01, 2, vc=2); checkpoint()
    burst([short(0x00, 3, flip=(17,))]); accept_short(0x00, 3, corrected=True); checkpoint()
    # generic short packet (DT 0x08) reports its data field
    burst([short(0x08, 0xBEEF)]); accept_short(0x08, 0xBEEF); checkpoint()
    # zero-length long packet: CRC only (0xFFFF)
    burst([long_pkt(0x12, b"")]); accept_long(0x12, b""); checkpoint()
    stim.append(15)
    write_hex(os.path.join(d, "stim.hex"), stim, 1)
    write_hex(os.path.join(d, "exp.hex"), exp)
    return {"NCHK": len(exp) // 75}

def gen_hdmi(d, rng):
    """expected InfoFrame packets: per packet HB0..HB2, ECC, then 4 x (7 bytes + ECC)"""
    def packet(hb, pb):
        out = list(hb) + [hdmi_bch(bits_lsb(hb))]
        body = list(pb) + [0] * (28 - len(pb))
        for s in range(4):
            sb = body[7 * s: 7 * s + 7]
            out += sb + [hdmi_bch(bits_lsb(sb))]
        return out
    def infoframe(t, ver, pbytes):
        hb = [t, ver, len(pbytes)]
        cs = (-(sum(hb) + sum(pbytes))) & 255
        return packet(hb, [cs] + list(pbytes))
    # AVI InfoFrame v2 (CTA-861): RGB, active format present, 4:3, AFD = same as picture, VIC 1
    avi = infoframe(0x82, 0x02, [0x10, 0x18, 0x00, 0x01] + [0] * 9)
    # SPD InfoFrame: vendor "OpenIP", product "HDMI 2.1 TX Core", source 0 (unknown)
    spd = infoframe(0x83, 0x01, list(b"OpenIP".ljust(8, b"\0")) + list(b"HDMI 2.1 TX Core") + [0x00])
    write_hex(os.path.join(d, "pkt.hex"), avi + spd)
    return {}

def gen_seed(d, rng):
    """Peripheral and DDR benches carry their protocol models; only the seed varies."""
    return {"SEED": rng.randrange(1, 1 << 30)}

def gen_lpddr(d, rng):
    return dict(gen_seed(d, rng), LPDDR=1)

GEN = {"crypto": gen_crypto, "eth": gen_eth, "csi2": gen_csi2, "hdmi": gen_hdmi,
       "uart": gen_seed, "spi": gen_seed, "i2c": gen_seed, "gpio": gen_seed, "pwm": gen_seed,
       "ddr4": gen_seed, "lpddr5x": gen_lpddr}

# ----------------------------------------------------------------------------
# simulation
# ----------------------------------------------------------------------------
def sim(files, top, wd, defines, simulator, timeout=1800):
    defs = ["-D%s=%s" % kv for kv in defines.items()]
    if simulator == "verilator":
        cmd = ["verilator", "--binary", "--timing", "-Wno-fatal", "-Wno-lint", "-Wno-style",
               "-j", "4", "--Mdir", os.path.join(wd, "obj"), "--top-module", top, "-I" + IPCHK] + \
              ["+define+%s=%s" % kv for kv in defines.items()] + files
        p = subprocess.run(cmd, cwd=wd, capture_output=True, text=True, timeout=timeout)
        if p.returncode:
            return None, p.stdout + p.stderr
        p = subprocess.run([os.path.join(wd, "obj", "V" + top)], cwd=wd, capture_output=True,
                           text=True, timeout=timeout)
        return p.returncode, p.stdout + p.stderr
    out = os.path.join(wd, "sim.vvp")
    p = subprocess.run(["iverilog", "-g2012", "-I", IPCHK, "-o", out, "-s", top] + defs + files, cwd=wd,
                       capture_output=True, text=True, timeout=timeout)
    if p.returncode:
        return None, p.stdout + p.stderr
    p = subprocess.run(["vvp", "-n", out], cwd=wd, capture_output=True, text=True, timeout=timeout)
    return p.returncode, p.stdout + p.stderr

def result(log):
    m = re.search(r"XCHK_(PASS|FAIL) checks=(\d+)", log)
    if not m:
        return "XCHK_ERROR", 0, (log.strip().splitlines() or ["no result"])[-1][:200]
    fails = [l.strip() for l in log.splitlines() if "[FAIL]" in l]
    notes = [l.strip()[7:] for l in log.splitlines() if "[NOTE]" in l]
    det = " | ".join(fails[:4])
    if notes:
        det = (det + " | " if det else "") + "notes: " + " | ".join(notes)
    return "XCHK_" + m.group(1), int(m.group(2)), det

def main(argv):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("ips", nargs="*", default=list(IPS))
    ap.add_argument("--ip-dir", default=os.environ.get("OPEN_IP_DIR",
                    os.path.join(os.path.dirname(ROOT), "open-ip-portfolio")))
    ap.add_argument("--sim", default=None, choices=["iverilog", "verilator"])
    ap.add_argument("--seed", type=int, default=2026)
    a = ap.parse_args(argv)
    bad = REF_SELFTEST()
    if bad:
        print("XCHK_ERROR reference self-test -- " + ", ".join(bad))
        return 2
    print("REF_SELFTEST_PASS python references")
    simulator = a.sim or ("iverilog" if shutil.which("iverilog") else "verilator")
    rtl = os.path.join(a.ip_dir, "rtl")
    rows, rc = [], 0
    # SystemVerilog reference package against the same public vectors
    wd = os.path.join(WORK, "ref")
    os.makedirs(wd, exist_ok=True)
    code, log = sim([os.path.join(IPCHK, "ref", "xchk_ref_pkg.sv"), os.path.join(IPCHK, "ref_selftest_tb.sv")],
                    "ref_selftest_tb", wd, {}, simulator)
    r, n, det = result(log)
    print("%s ref_pkg -- checks=%d %s" % (r, n, det))
    rows.append(["ref_pkg", r, n, det])
    rc |= r != "XCHK_PASS"
    for ip in a.ips:
        srcs, tb, extra = IPS[ip]
        wd = os.path.join(WORK, ip)
        os.makedirs(wd, exist_ok=True)
        defs = GEN[ip](wd, random.Random(a.seed))
        duts = [os.path.join(rtl, f) for f in srcs]
        missing = [f for f in duts if not os.path.exists(f)]
        if missing:
            print("XCHK_ERROR %s -- %s not found (set --ip-dir or OPEN_IP_DIR)" % (ip, missing[0]))
            rows.append([ip, "XCHK_ERROR", 0, "rtl not found"]); rc = 1
            continue
        s = "verilator" if (ip == "hdmi" and shutil.which("verilator") and not a.sim) else simulator
        code, log = sim([os.path.join(IPCHK, "ref", "xchk_ref_pkg.sv")] + duts +
                        [os.path.join(IPCHK, f) for f in extra] + [os.path.join(IPCHK, tb)],
                        tb[:-3], wd, defs, s)
        open(os.path.join(wd, "sim.log"), "w").write(log)
        r, n, det = result(log)
        print("%s %s [%s] -- checks=%d %s" % (r, ip, s, n, det))
        rows.append([ip, r, n, det])
        rc |= r != "XCHK_PASS"
    with open(REPORT, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["ip", "result", "checks", "detail"])
        w.writerows(rows)
    return 1 if rc else 0

if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
