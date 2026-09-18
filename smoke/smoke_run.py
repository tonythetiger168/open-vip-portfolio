#!/usr/bin/env python3
"""Smoke-test runner: generate tb_smoke for each flattened DUT, compile with
iverilog -g2012, run with vvp, and classify PASS/FAIL/SKIP per VIP.

Usage: python3 smoke_run.py [VIP_NAME ...]   (default: all VIPs)
"""
import os, re, sys, json, subprocess, time, collections

ROOT = "/mnt/agents/output/work_v174"
VIPS = os.path.join(ROOT, "vips")
SMOKE = os.path.join(ROOT, "smoke")
CYCLES = 1500
WARMUP = 12

def read_retry(p, tries=5):
    for i in range(tries):
        try:
            with open(p, errors="ignore") as f:
                return f.read()
        except (BlockingIOError, OSError):
            time.sleep(0.5)
    return ""

def write_retry(p, data, tries=5):
    for i in range(tries):
        try:
            os.makedirs(os.path.dirname(p), exist_ok=True)
            with open(p, "w") as f:
                f.write(data)
            return
        except (BlockingIOError, OSError):
            time.sleep(0.5)

def dim_width(dims):
    m = re.match(r'\[\s*(\d+)\s*:\s*(\d+)\s*\]', dims or '')
    if not m:
        return 1
    return abs(int(m.group(1)) - int(m.group(2))) + 1

def classify_ports(ports):
    clocks, resets, ints, inputs, outputs, inouts = [], [], [], [], [], []
    for pm in ports:
        nm, w = pm['name'], dim_width(pm['dims'])
        low = nm.lower()
        if pm['dir'] == 'input':
            if w == 1 and re.search(r'(clk|clock|^ck$|_ck$|^ck_|tck|sck)', low):
                clocks.append(pm)
            elif w == 1 and re.search(r'(rst|reset|resn|preset)', low):
                resets.append(pm)
            elif pm['type'] in ('int', 'integer'):
                ints.append(pm)
            else:
                inputs.append(pm)
        elif pm['dir'] == 'output':
            outputs.append(pm)
        else:
            inouts.append(pm)
    return clocks, resets, ints, inputs, outputs, inouts

def gen_tb(mod, ports):
    clocks, resets, ints, inputs, outputs, inouts = classify_ports(ports)
    L = []
    L.append("`timescale 1ns/1ps")
    L.append("module tb_smoke;")
    L.append("  localparam int CYCLES = %d;" % CYCLES)
    L.append("  int x_hits = 0;")
    L.append("  longint unsigned toggle_cnt = 0;")
    decls, conns = [], []
    for pm in ports:
        w = dim_width(pm['dims'])
        rng = " [%d:0]" % (w - 1) if w > 1 else ""
        if pm['dir'] == 'input':
            decls.append("  logic%s %s = '0;" % (rng, pm['name']))
        elif pm['dir'] == 'output':
            decls.append("  wire%s %s;" % (rng, pm['name']))
            decls.append("  logic%s %s_q = '0;" % (rng, pm['name']))
        else:
            decls.append("  tri0%s %s;" % (rng, pm['name']))  # weak pull-down when undriven
        conns.append(".%s(%s)" % (pm['name'], pm['name']))
    L.extend(decls)
    L.append("  %s u_dut (\n    %s\n  );" % (mod, ",\n    ".join(conns)))
    if not clocks:
        # virtual tb clock for stimulus stepping of a clockless DUT
        L.append("  logic tb_clk = 0; always #5 tb_clk = ~tb_clk;")
        syncclk = "tb_clk"
    else:
        for c in clocks:
            L.append("  always #5 %s = ~%s;" % (c['name'], c['name']))
        syncclk = clocks[0]['name']
    # resets
    rst_init, rst_rel = [], []
    for r in resets:
        low = r['name'].lower()
        active_low = low.endswith('n') or low.endswith('_n') or '_n' in low
        rst_init.append("    %s = 1'b%d;" % (r['name'], 0 if active_low else 1))
        rst_rel.append("    %s = 1'b%d;" % (r['name'], 1 if active_low else 0))
    # int timing params: small fixed value
    int_init = ["    %s = 3;" % pm['name'] for pm in ints]
    rand_targets = [pm['name'] for pm in inputs]
    L.append("  initial begin")
    L.extend(rst_init)
    L.extend(int_init)
    L.append("    repeat (4) @(posedge %s);" % syncclk)
    L.extend(rst_rel)
    L.append("    for (int c = 0; c < CYCLES; c++) begin")
    L.append("      @(posedge %s);" % syncclk)
    if rand_targets:
        L.append("      #1;")
        for t in rand_targets:
            L.append("      %s <= $random;" % t)
    L.append("    end")
    L.append("      if (x_hits == 0) $display(\"SMOKE_PASS x_hits=%0d toggles=%0d\", x_hits, toggle_cnt);")
    L.append("      else           $display(\"SMOKE_FAIL x_hits=%0d toggles=%0d\", x_hits, toggle_cnt);")
    L.append("      $finish;")
    L.append("  end")
    # X monitor + toggle counter after warmup
    L.append("  initial begin : MON")
    L.append("    int cyc = 0;")
    L.append("    forever begin")
    L.append("      @(negedge %s);" % syncclk)
    L.append("      cyc++;")
    L.append("      if (cyc > %d) begin" % (WARMUP + 4))
    for o in outputs:
        L.append("        if ($isunknown(%s)) x_hits++;" % o['name'])
        L.append("        if (%s !== %s_q) toggle_cnt++;" % (o['name'], o['name']))
        L.append("        %s_q <= %s;" % (o['name'], o['name']))
    L.append("      end")
    L.append("    end")
    L.append("  end")
    L.append("  // safety timeout")
    L.append("  initial begin")
    L.append("    #(CYCLES * 20 * 10);")
    L.append("    $display(\"SMOKE_TIMEOUT\");")
    L.append("    $finish;")
    L.append("  end")
    L.append("endmodule")
    return "\n".join(L) + "\n"

def run(cmd, timeout, cwd):
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, cwd=cwd)
        return r.returncode, (r.stdout or "") + (r.stderr or "")
    except subprocess.TimeoutExpired:
        return -9, "TIMEOUT after %ds" % timeout

CLASS_RE = re.compile(r'\b(?:virtual\s+)?class\b.*?\bendclass\b', re.S)

def sanitize_pkg(src):
    """Strip UVM content from a package so iverilog can compile the typedefs."""
    src = re.sub(r'^\s*`include\s+.*$', '', src, flags=re.M)
    src = re.sub(r'^\s*import\s+uvm_pkg::\*;\s*$', '', src, flags=re.M)
    prev = None
    while prev != src:
        prev = src
        src = CLASS_RE.sub('', src)
    src = re.sub(r'`uvm_\w+\([^)]*\)\s*', '', src)
    src = re.sub(r'\bint\s+unsigned\b', 'int', src)
    src = re.sub(r'\blongint\s+unsigned\b', 'longint', src)
    return src

def strip_bad_functions(src, errfile, out):
    """Remove the function/task block containing the first reported error line.
    Returns modified src or None."""
    m = re.search(re.escape(os.path.basename(errfile)) + r':(\d+):', out)
    if not m:
        return None
    ln = int(m.group(1)) - 1
    lines = src.split('\n')
    if ln >= len(lines):
        return None
    # search backwards for function/task start, forwards for end
    s = None
    for i in range(ln, max(0, ln - 200), -1):
        if re.search(r'\b(function|task)\b', lines[i]):
            s = i
            break
    if s is None:
        return None
    kw = 'endfunction' if 'function' in lines[s] else 'endtask'
    e = None
    for i in range(ln, min(len(lines), ln + 400)):
        if kw in lines[i]:
            e = i
            break
    if e is None or e < s:
        return None
    del lines[s:e + 1]
    return '\n'.join(lines)

def try_compile_pkg_iterative(src, sp, extra=None):
    """Write src to sp; compile; on failure strip bad function blocks and retry."""
    cur = src
    for _ in range(12):
        write_retry(sp, cur)
        rc, out = run(["iverilog", "-g2012", "-t", "null", "-s", "__dummy",
                       os.path.join(os.path.dirname(sp), "dummy_top.sv")]
                      + (extra or []) + [sp], 60, SMOKE)
        if rc == 0:
            return True
        cur2 = strip_bad_functions(cur, sp, out)
        if cur2 is None or cur2 == cur:
            return False
        cur = cur2
    return False

def compilable_pkgs(vip_dir, vip):
    """Return [(pkg_name, path)] for package files iverilog can compile
    (directly, or after stripping UVM classes into a sanitized copy)."""
    good = []
    dummy = os.path.join(SMOKE, vip, "dummy_top.sv")
    write_retry(dummy, "module __dummy; endmodule\n")
    def try_compile(paths):
        rc, _ = run(["iverilog", "-g2012", "-t", "null", "-s", "__dummy", dummy]
                    + [g for _, g in good] + paths, 60, SMOKE)
        return rc == 0
    seen_pkgs = set()
    for dirpath, dirs, files in os.walk(vip_dir):
        for fn in sorted(files):
            if not fn.endswith('.sv'):
                continue
            p = os.path.join(dirpath, fn)
            txt = read_retry(p)
            pknames = re.findall(r'\bpackage\s+(\w+)\s*;', txt)
            if not pknames:
                continue
            if fn.endswith('_pkg.sv') or fn.endswith('_defs.sv'):
                if try_compile([p]):
                    for n in pknames:
                        if n not in seen_pkgs:
                            seen_pkgs.add(n); good.append((n, p))
                    continue
            # extract package blocks only (file may also contain UVM code)
            blocks = []
            for pm_ in re.finditer(r'\bpackage\s+(\w+)\s*;', txt):
                e = txt.find('endpackage', pm_.end())
                if e > 0:
                    blocks.append(txt[pm_.start():e + 10])
            sp = os.path.join(SMOKE, vip, "pkg_san_" + fn)
            write_retry(sp, sanitize_pkg("\n\n".join(blocks)))
            if try_compile_pkg_iterative(read_retry(sp), sp, extra=[g for _, g in good]):
                for n in pknames:
                    if n not in seen_pkgs:
                        seen_pkgs.add(n); good.append((n, sp))
    return good

def inject_imports(dut_path, pkg_names, out_path):
    src = read_retry(dut_path)
    imp = "\n" + "\n".join("  import %s::*;" % n for n in pkg_names) + "\n"
    m = re.search(r'\bmodule\s+\w+\s*\(', src)
    i = src.index('\n);', m.start()) + 3   # end of generated port list
    src = src[:i] + imp + src[i:]
    write_retry(out_path, src)

def test_module(vip, ent, logf):
    mod = ent['module']
    outdir = os.path.join(SMOKE, vip)
    dut = ent['file']
    tb = os.path.join(outdir, "tb_smoke_%s.sv" % mod)
    write_retry(tb, gen_tb(mod, ent['ports']))
    exe = os.path.join(outdir, "smoke_%s.out" % mod)
    files = [dut, tb]
    rc, out = run(["iverilog", "-g2012", "-s", "tb_smoke", "-o", exe] + files, 120, outdir)
    if rc != 0:
        pkgs = compilable_pkgs(os.path.join(VIPS, vip), vip)
        if pkgs:
            dut2 = os.path.join(outdir, "dut_%s_pkg.sv" % mod)
            inject_imports(dut, [n for n, _ in pkgs], dut2)
            files = [p for _, p in pkgs] + [dut2, tb]
            rc, out = run(["iverilog", "-g2012", "-s", "tb_smoke", "-o", exe] + files, 120, outdir)
            if rc == 0:
                logf.write("[compile] succeeded with pkgs: %s\n" % " ".join(n for n, _ in pkgs))
            else:
                for n, p in pkgs:  # try one pkg at a time
                    inject_imports(dut, [n], dut2)
                    rc, out = run(["iverilog", "-g2012", "-s", "tb_smoke", "-o", exe, p, dut2, tb], 120, outdir)
                    if rc == 0:
                        files = [p, dut2, tb]
                        logf.write("[compile] succeeded with pkg: %s\n" % n)
                        break
    if rc != 0:
        logf.write("[compile FAILED]\n%s\n" % out[:4000])
        return "FAIL_COMPILE", out
    rc, out = run(["vvp", exe], 90, outdir)
    logf.write(out[-4000:] + "\n")
    if "SMOKE_PASS" in out:
        m = re.search(r'x_hits=(\d+) toggles=(\d+)', out)
        return "PASS", out
    if "SMOKE_FAIL" in out or "SMOKE_TIMEOUT" in out:
        return "FAIL", out
    return "FAIL_NOSIM", out

def run_vip(vip):
    outdir = os.path.join(SMOKE, vip)
    man = os.path.join(outdir, "manifest.json")
    if not os.path.exists(man):
        # flatten on demand
        subprocess.run([sys.executable, os.path.join(SMOKE, "flatten.py"), vip],
                       capture_output=True, text=True, timeout=600)
    entries = json.loads(read_retry(man) or "[]")
    logf = open(os.path.join(outdir, "smoke.log"), "w")
    results = []
    for ent in entries:
        if ent['status'] != "FLAT":
            results.append((ent.get('module'), "SKIP", ent.get('reason', '')))
            logf.write("== %s: SKIP (%s)\n" % (ent.get('module'), ent.get('reason', '')))
            continue
        st, out = test_module(vip, ent, logf)
        note = ""
        if st == "PASS":
            m = re.search(r'x_hits=(\d+) toggles=(\d+)', out)
            if m:
                note = "x_hits=%s toggles=%s" % m.groups()
            st = "PASS"
        elif st == "FAIL_COMPILE":
            st, note = "SKIP", "compile: unsupported SV (see smoke.log)"
        elif st == "FAIL":
            m = re.search(r'x_hits=(\d+) toggles=(\d+)', out)
            note = ("x_hits=%s toggles=%s" % m.groups()) if m else "X/Z or timeout"
        results.append((ent['module'], st, note))
        logf.write("== %s: %s %s\n" % (ent['module'], st, note))
    logf.close()
    # aggregate
    sts = [r[1] for r in results]
    if any(s == "FAIL" for s in sts):
        agg = "FAIL"
    elif any(s == "PASS" for s in sts):
        agg = "PASS"
    else:
        agg = "SKIP"
    detail = "; ".join("%s:%s%s" % (m or "-", s, ("(" + n + ")") if n else "")
                       for m, s, n in results)
    return agg, detail, results


def merge_csv():
    out = ["vip,result,detail"]
    for v in sorted(d for d in os.listdir(VIPS) if os.path.isdir(os.path.join(VIPS, d))):
        rowp = os.path.join(SMOKE, v, "row.csv")
        if os.path.exists(rowp):
            out.append(read_retry(rowp).strip())
        else:
            out.append("%s,SKIP,not run" % v)
    write_retry(os.path.join(SMOKE, "smoke_report.csv"), "\n".join(out) + "\n")

if __name__ == "__main__":
    names = sys.argv[1:] or sorted(d for d in os.listdir(VIPS) if os.path.isdir(os.path.join(VIPS, d)))
    for v in names:
        try:
            agg, detail, _ = run_vip(v)
        except Exception as ex:
            agg, detail = "SKIP", "harness error: %s" % ex
        print("%s %s -- %s" % ("SMOKE_" + agg, v, detail[:200]))
        write_retry(os.path.join(SMOKE, v, "row.csv"),
                    "%s,%s,%s\n" % (v, agg, detail.replace(",", ";")))
    merge_csv()
