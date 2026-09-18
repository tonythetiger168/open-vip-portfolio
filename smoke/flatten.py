#!/usr/bin/env python3
"""Flatten interface-port DUT modules for Icarus Verilog smoke testing.

For each VIP under vips/<X>-VIP/:
  * locate DUT modules (top_tb.sv / tb_top.sv / *_model.sv, excluding top_tb)
  * if a module port is an interface (optionally with modport), parse the
    interface signal declarations and rewrite the module into a flattened
    copy with plain input/output/inout ports.
  * emit smoke/<VIP>/dut_<module>.sv + manifest.json entries.
Unreliable cases are marked SKIP with a reason.
"""
import os, re, sys, json, time, collections

ROOT = "/mnt/agents/output/work_v174"
VIPS = os.path.join(ROOT, "vips")
SMOKE = os.path.join(ROOT, "smoke")

def read_retry(p, tries=5):
    for i in range(tries):
        try:
            with open(p, errors="ignore") as f:
                return f.read()
        except (BlockingIOError, OSError):
            time.sleep(0.5)
    raise IOError("read failed: %s" % p)

def write_retry(p, data, tries=5):
    for i in range(tries):
        try:
            os.makedirs(os.path.dirname(p), exist_ok=True)
            with open(p, "w") as f:
                f.write(data)
            return
        except (BlockingIOError, OSError):
            time.sleep(0.5)
    raise IOError("write failed: %s" % p)

MOD_RE = re.compile(r'\bmodule\s+([A-Za-z_]\w*)')

def strip_comments(txt):
    txt = re.sub(r'/\*.*?\*/', '', txt, flags=re.S)
    txt = re.sub(r'//[^\n]*', '', txt)
    return txt

def find_modules(txt):
    """Return list of (name, start_idx_of_'module', end_idx_after_'endmodule')."""
    out = []
    for m in MOD_RE.finditer(txt):
        e = txt.find('endmodule', m.end())
        if e < 0:
            continue
        out.append((m.group(1), m.start(), e + len('endmodule')))
    return out

def split_top_commas(s):
    """Split s on commas at paren depth 0."""
    parts, depth, cur = [], 0, []
    for ch in s:
        if ch in '([':
            depth += 1
        elif ch in ')]':
            depth -= 1
        if ch == ',' and depth == 0:
            parts.append(''.join(cur)); cur = []
        else:
            cur.append(ch)
    if cur:
        parts.append(''.join(cur))
    return [p.strip() for p in parts if p.strip()]

def parse_module_portlist(seg):
    """Return (param_block_or_None, port_list_str) from module segment."""
    m = re.match(r'\s*module\s+\w+\s*', seg)
    i = m.end()
    params = None
    if seg[i:].lstrip().startswith('#'):
        i = seg.index('#', i) + 1
        while seg[i].isspace():
            i += 1
        if seg[i] == '(':
            depth = 0; j = i
            while j < len(seg):
                if seg[j] == '(': depth += 1
                elif seg[j] == ')':
                    depth -= 1
                    if depth == 0: break
                j += 1
            params = seg[i+1:j]
            i = j + 1
    while i < len(seg) and seg[i].isspace():
        i += 1
    if i >= len(seg) or seg[i] != '(':
        return params, None   # no port list
    depth = 0; j = i
    while j < len(seg):
        if seg[j] == '(': depth += 1
        elif seg[j] == ')':
            depth -= 1
            if depth == 0: break
        j += 1
    return params, seg[i+1:j]

# ---------------- interface parsing ----------------

BLOCK_RE = [
    (re.compile(r'\bmodport\b.*?\)\s*;', re.S), ''),
    (re.compile(r'\bclocking\b.*?\bendclocking\b', re.S), ''),
    (re.compile(r'\bcovergroup\b.*?\bendgroup\b', re.S), ''),
    (re.compile(r'\bproperty\b.*?\bendproperty\b', re.S), ''),
    (re.compile(r'\bsequence\b.*?\bendsequence\b', re.S), ''),
    (re.compile(r'\bfunction\b.*?\bendfunction\b', re.S), ''),
    (re.compile(r'\btask\b.*?\bendtask\b', re.S), ''),
]

DECL_RE = re.compile(r'^\s*(logic|bit|wire|reg|tri|int\s+unsigned|int|integer)\s*((?:\[[^\]]*\]\s*)*)([^;]+);', re.M)

def parse_interface(ifc_txt, ifc_name):
    """Return dict signal -> (kind, dims) plus list of interface input ports.
    None on failure."""
    m = re.search(r'\binterface\s+' + re.escape(ifc_name) + r'\b', ifc_txt)
    if not m:
        return None
    e = ifc_txt.find('endinterface', m.end())
    if e < 0:
        return None
    body = ifc_txt[m.start():e]
    # interface parameters (for width substitution)
    params = {}
    pm = re.match(r'\s*interface\s+\w+\s*#\s*\(', body)
    if pm:
        i = body.index('(', pm.end() - 1)
        depth = 0; j = i
        while j < len(body):
            if body[j] == '(': depth += 1
            elif body[j] == ')':
                depth -= 1
                if depth == 0: break
            j += 1
        for prm in split_top_commas(body[i+1:j]):
            pmm = re.search(r'(\w+)\s*=\s*([^=]+)$', prm.strip())
            if pmm:
                params[pmm.group(1)] = pmm.group(2).strip()
    # interface header ports (usually clocks/resets as input logic)
    _, plist = parse_module_portlist(body.replace('interface', 'module', 1))
    hdr_sigs = {}
    if plist:
        for p in split_top_commas(plist):
            mm = re.match(r'(input|output|inout)\s+(logic|bit|wire|reg)?\s*((?:\[[^\]]*\]\s*)*)(\w+)', p)
            if mm:
                hdr_sigs[mm.group(4)] = (mm.group(1), (mm.group(3) or '').strip())
    for rx, rep in BLOCK_RE:
        body = rx.sub(rep, body)
    sigs = dict(hdr_sigs)
    for dm in DECL_RE.finditer(body):
        kind, dims, names = dm.group(1), (dm.group(2) or '').strip(), dm.group(3)
        # skip declarations that still contain suspicious tokens
        if '=' in names.split('//')[0] and re.search(r'=\s*\{', names):
            continue
        base_kind = 'logic'
        if kind.startswith('int') or kind == 'integer':
            dims = dims or '[31:0]'
        for nm in split_top_commas(names):
            nm = nm.split('=')[0].strip()
            mm = re.match(r'^(\w+)\s*((?:\[[^\]]*\]\s*)*)$', nm)
            if not mm:
                continue  # complex decl: ignore unless referenced
            undim = mm.group(2).strip()
            if undim:
                # unpacked array -> record as ARRAY::sig with (packed dims, undim)
                sigs['ARRAY::' + mm.group(1)] = (base_kind, dims, undim)
            else:
                sigs[mm.group(1)] = (base_kind, dims)
    # anything left that looks like a typed decl of an unknown type?
    left = re.sub(DECL_RE, '', body)
    left = re.sub(r'\b(interface|endinterface|parameter|localparam|import|assign|initial|always\w*|`\w+)\b[^;]*;', '', left)
    for lm in re.finditer(r'^\s*(\w+(?:::\w+)?)\s+((?:\[[^\]]*\]\s*)*)(\w+)\s*;', left, re.M):
        # enum/struct typed signal -> need width; try typedef lookup later
        sigs['TYPE::' + lm.group(3)] = (lm.group(1), (lm.group(2) or '').strip())
    return sigs, params

def subst_dims(dims, params):
    """Substitute interface parameter names into a dim string and fold."""
    if not dims:
        return dims
    def rep(mo):
        tok = mo.group(0)
        if tok in params:
            return '(%s)' % params[tok]
        return tok
    out = re.sub(r'\b[A-Za-z_]\w*\b', rep, dims)
    # fold simple arithmetic
    def fold(mo):
        try:
            return str(eval(mo.group(0), {}, {}))
        except Exception:
            return mo.group(0)
    out = re.sub(r'[\d()+\-*/ ]{3,}', fold, out)
    return out

def find_interface_file(vip_dir, ifc_name):
    cands = []
    for dirpath, dirs, files in os.walk(vip_dir):
        for fn in files:
            if fn.endswith('.sv'):
                cands.append(os.path.join(dirpath, fn))
    cands.sort(key=lambda p: (0 if p.endswith('_if.sv') else 1, len(p)))
    for p in cands:
        txt = read_retry(p)
        if re.search(r'\binterface\s+' + re.escape(ifc_name) + r'\b', txt):
            return p, txt
    return None, None

def find_typedef_width(vip_dir, type_name):
    """Search for `typedef enum logic [N:M] {...} type_name` in VIP tree."""
    rx = re.compile(r'typedef\s+enum\s+(logic|bit|reg|int|integer)\s*(\[[^\]]*\])?\s*\{[^}]*\}\s*' + re.escape(type_name) + r'\s*;', re.S)
    for dirpath, dirs, files in os.walk(vip_dir):
        for fn in files:
            if not fn.endswith('.sv'):
                continue
            p = os.path.join(dirpath, fn)
            txt = read_retry(p)
            m = rx.search(txt)
            if m:
                if m.group(1) in ('int', 'integer'):
                    return '[31:0]'
                return m.group(2) or ''
    return None

# ---------------- DUT flattening ----------------

ANSI_PORT_RE = re.compile(r'^(input|output|inout)\b\s*(?:(logic|bit|wire|reg|tri|int|integer|genvar|\w+(?:::\w+)?)\b\s*)?((?:\[[^\]]*\]\s*)*)([\w]+)\s*((?:\[[^\]]*\]\s*)*)$')

def dim_size(dims):
    """'[a:b]' -> size (int) or None."""
    m = re.match(r'\[\s*([^:]+)\s*:\s*([^\]]+)\]', dims or '')
    if not m:
        return 1 if not dims else None
    try:
        return abs(eval(m.group(1), {}, {}) - eval(m.group(2), {}, {})) + 1
    except Exception:
        return None

def rewrite_array_refs(body, inst, sig, new, dims, undim):
    """Flatten unpacked array refs inst.sig[idx][h:l] into packed part-selects.
    Returns new body or None if an unsafe pattern remains."""
    w = dim_size(dims)
    nm = re.match(r'\[\s*(\d+)\s*\]', undim or '')
    n = int(nm.group(1)) if nm else dim_size(undim)
    if w is None or n is None:
        return None
    # foreach (inst.sig[i])  ->  for (int i=0;i<n;i++)
    body = re.sub(r'foreach\s*\(\s*' + re.escape(inst) + r'\.' + re.escape(sig) + r'\s*\[\s*(\w+)\s*\]\s*\)',
                  r'for (int \1=0;\1<%d;\1++)' % n, body)
    pat = re.escape(inst) + r'\.' + re.escape(sig)
    # inst.sig[i][h:l]
    body = re.sub(pat + r'\s*\[([^\]]+)\]\s*\[\s*(\d+)\s*:\s*(\d+)\s*\]',
                  lambda m: '%s[(%s)*%d+%s +: %d]' % (new, m.group(1), w, m.group(3),
                                                     int(m.group(2)) - int(m.group(3)) + 1), body)
    # inst.sig[i][b]
    body = re.sub(pat + r'\s*\[([^\]]+)\]\s*\[\s*(\d+)\s*\]',
                  lambda m: '%s[(%s)*%d+%s]' % (new, m.group(1), w, m.group(2)), body)
    # inst.sig[i]
    body = re.sub(pat + r'\s*\[([^\]]+)\]',
                  lambda m: '%s[(%s)*%d +: %d]' % (new, m.group(1), w, w), body)
    # whole-array ref
    body = re.sub(pat + r'\b', new, body)
    return body
IFC_PORT_RE = re.compile(r'^(\w+)(?:\s*\.\s*(\w+))?\s+(\w+)$')

def flatten_module(vip_dir, mod_name, seg):
    """Return (flattened_source, ports_meta, skip_reason)."""
    params, plist = parse_module_portlist(seg)
    if plist is None:
        return None, None, "no ANSI port list"
    raw_ports = split_top_commas(plist)
    body_start = seg.index(');', seg.index(plist[:20])) if plist else seg.index(';')
    body = seg[body_start:]
    ports_meta = []          # list of dicts {dir,type,dims,name}
    rewrites = []            # (inst, sig) -> new name
    flat_ifc_ports = []
    for rp in raw_ports:
        am = ANSI_PORT_RE.match(rp)
        if am:
            d, ty, dims, nm, un = am.groups()
            if un.strip():
                return None, None, "unpacked array port %s" % nm
            ty = ty or 'logic'
            dims = (dims or '').strip()
            if ty not in ('logic', 'bit', 'wire', 'reg', 'tri', 'int', 'integer', 'genvar'):
                w = find_typedef_width(vip_dir, ty.split('::')[-1])
                if w is None:
                    return None, None, "port %s of unknown type %s" % (nm, ty)
                ty, dims = 'logic', w
            ports_meta.append(dict(dir=d, type=ty, dims=dims, name=nm))
            continue
        im = IFC_PORT_RE.match(rp)
        if im and not re.match(r'^(input|output|inout)\b', rp):
            ifc_type, mp, inst = im.groups()
            ifc_path, ifc_txt = find_interface_file(vip_dir, ifc_type)
            if ifc_txt is None:
                return None, None, "interface %s not found" % ifc_type
            sigs, iparams = parse_interface(strip_comments(ifc_txt), ifc_type)
            if sigs is None:
                return None, None, "interface %s parse unreliable" % ifc_type
            flat_ifc_ports.append((inst, sigs, iparams))
            continue
        return None, None, "unrecognized port: %r" % rp[:60]

    # whole-interface pass-through (submodule instantiation) -> unreliable
    for inst, sigs, iparams in flat_ifc_ports:
        if re.search(r'[,(]\s*' + re.escape(inst) + r'\s*[,)]', body):
            return None, None, "interface %s passed through to submodule" % inst

    # direction inference + resolution of TYPE::/ARRAY:: signals
    for inst, sigs, iparams in flat_ifc_ports:
        for sig, info in sigs.items():
            kind, dims = info[0], info[1]
            dims = subst_dims(dims, iparams)
            real_sig = sig.replace('TYPE::', '').replace('ARRAY::', '')
            ref = re.escape(inst) + r'\.' + re.escape(real_sig) + r'\b'
            if not re.search(ref, body):
                continue  # unreferenced -> no port needed
            new = inst + '_' + real_sig
            driven = bool(re.search(r'assign\s+' + ref + r'(\[[^\]]*\])?\s*=', body)) or \
                     bool(re.search(r'(?<![<>=!])' + ref + r'(\[[^\]]*\])?\s*<=', body)) or \
                     bool(re.search(r'(?<![<>=!:])' + ref + r'(\[[^\]]*\])?\s*=[^=]', body))
            zdrive = bool(re.search(r'assign\s+' + ref + r"[^;]*'[a-zA-Z]*[zZ]", body)) or \
                     bool(re.search(r'(?<![<>=!])' + ref + r"[^;]*'[a-zA-Z]*[zZ]\s*;", body))
            if sig.startswith('TYPE::'):
                w = find_typedef_width(vip_dir, kind.split('::')[-1])
                if w is None:
                    return None, None, "enum-typed ifc signal %s (type %s), width unknown" % (real_sig, kind)
                dims, kind = w, 'logic'
            if sig.startswith('ARRAY::'):
                undim = subst_dims(info[2], iparams)
                nm1 = re.match(r'\[\s*(\d+)\s*\]', undim or '')
                w = dim_size(dims)
                n = int(nm1.group(1)) if nm1 else dim_size(undim)
                if w is None or n is None or w * n > 8192:
                    return None, None, "array ifc signal %s not flattenable" % real_sig
                nb = rewrite_array_refs(body, inst, real_sig, new, dims, undim)
                if nb is None:
                    return None, None, "array ifc signal %s rewrite failed" % real_sig
                body = nb
                dims = '[%d:0]' % (w * n - 1)
            if zdrive:
                d = 'inout'
            elif driven:
                d = 'output'
            else:
                d = 'input'
            ports_meta.append(dict(dir=d, type='logic', dims=dims, name=new, orig=inst + '.' + real_sig))
            rewrites.append((inst, real_sig, new))

    # rewrite body references (longest signal names first)
    new_body = body
    for inst, sig, new in sorted(rewrites, key=lambda t: -len(t[1])):
        new_body = re.sub(r'\b' + re.escape(inst) + r'\.' + re.escape(sig) + r'\b', new, new_body)
    # any leftover inst. references?
    for inst, sigs, iparams in flat_ifc_ports:
        leftover = re.findall(r'\b' + re.escape(inst) + r'\.(\w+)', new_body)
        if leftover:
            return None, None, "unresolved ifc refs: %s" % sorted(set(leftover))[:5]

    hdr = "module %s (\n" % mod_name
    plines = []
    for pm in ports_meta:
        dims = (" " + pm['dims']) if pm['dims'] else ""
        ty = ' wire' if pm['dir'] == 'inout' else ' logic'
        if pm['type'] in ('int', 'integer'):
            ty = ' int'
        plines.append("  %s%s%s %s" % (pm['dir'], ty, dims, pm['name']))
    hdr += ",\n".join(plines) + "\n);\n"
    new_seg = hdr + new_body[new_body.index(';') + 1:]
    # Icarus rejects `localparam int unsigned` etc.; identical semantics here
    new_seg = re.sub(r'\bint\s+unsigned\b', 'int', new_seg)
    new_seg = re.sub(r'\blongint\s+unsigned\b', 'longint', new_seg)
    return new_seg, ports_meta, None

# ---------------- discovery ----------------

def vip_tb_files(vip_dir):
    cands = []
    for dirpath, dirs, files in os.walk(vip_dir):
        for fn in files:
            if fn in ("top_tb.sv", "tb_top.sv") or fn.endswith("_model.sv"):
                cands.append(os.path.join(dirpath, fn))
    return sorted(cands)

def process_vip(vip_name):
    vip_dir = os.path.join(VIPS, vip_name)
    outdir = os.path.join(SMOKE, vip_name)
    entries = []
    seen = set()
    tbs = vip_tb_files(vip_dir)
    if not tbs:
        return [dict(module=None, status="SKIP", reason="no tb/model file found")]
    for p in tbs:
        txt = read_retry(p)
        clean = strip_comments(txt)
        for name, s, e in find_modules(clean):
            if name in ("top_tb", "tb_top"):
                continue
            if name in seen:
                continue
            seen.add(name)
            seg = clean[s:e]
            src_rel = os.path.relpath(p, ROOT)
            flat, meta, why = flatten_module(vip_dir, name, seg)
            if flat is None:
                entries.append(dict(module=name, status="SKIP", reason=why, source=src_rel))
            else:
                out = os.path.join(outdir, "dut_%s.sv" % name)
                stub = ("`ifndef uvm_info\n"
                        "`define uvm_info(ID,MSG,VB) $display(\"[INFO] %s\", MSG);\n"
                        "`define uvm_warning(ID,MSG) $display(\"[WARN] %s\", MSG);\n"
                        "`define uvm_error(ID,MSG) $display(\"[ERROR] %s\", MSG);\n"
                        "`define uvm_fatal(ID,MSG) $display(\"[FATAL] %s\", MSG);\n"
                        "`endif\n")
                write_retry(out, "// flattened from %s (module %s)\n%s%s\n" % (src_rel, name, stub, flat))
                entries.append(dict(module=name, status="FLAT", file=out,
                                    ports=meta, source=src_rel))
    if not entries:
        entries.append(dict(module=None, status="SKIP", reason="no DUT module found"))
    write_retry(os.path.join(outdir, "manifest.json"), json.dumps(entries, indent=1))
    return entries

if __name__ == "__main__":
    names = sys.argv[1:] or sorted(d for d in os.listdir(VIPS) if os.path.isdir(os.path.join(VIPS, d)))
    for v in names:
        ents = process_vip(v)
        st = collections.Counter(e['status'] for e in ents)
        print("%-24s %s" % (v, dict(st)))
