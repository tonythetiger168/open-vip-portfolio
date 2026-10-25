#!/usr/bin/env python3
# Copyright 2026 VIP Portfolio Contributors
# SPDX-License-Identifier: Apache-2.0
"""fix_uvm_skeleton.py <vip_dir>... -- repair the v1.7.5/v1.8.0 generated UVM layer.

The 29 VIPs generated from the same template shipped a UVM layer that cannot
elaborate under UVM 1.2 / IEEE 1800.2:
  * components have no ``new(name, parent)`` constructor
  * the driver writes ``ap``/``item_cnt`` that are never declared, but the env
    connects ``agt.drv.ap`` to the scoreboard
  * the driver drives ``rst_n`` through ``drv_cb`` where it is an input
  * embedded covergroups are constructed in build_phase (must be in new())
  * ``uvm_do_with(req, 1 == 1)`` lacks the constraint braces
  * top_tb include guards built from display names (``800G Ethernet_TB_SV``,
    ``ACE-Lite_TB_SV``) are not identifiers
  * the SENT/UEC SVA checkers reference DUT-internal pipeline registers
The edits are idempotent; re-running on a fixed tree is a no-op.
"""
import re, sys, os, glob

CTOR = ("  function new(string name, uvm_component parent);\n"
        "    super.new(name, parent);\n{extra}"
        "  endfunction\n\n")

def add_ctor(src, cls_re, extra=""):
    m = re.search(r'(class\s+\w+\s+extends\s+' + cls_re + r'[^;]*;\s*\n\s*`uvm_component_utils\(\w+\)\n)', src)
    if not m:
        return src
    body_start = m.end()
    end = src.find('endclass', body_start)
    if re.search(r'function\s+new\s*\(', src[body_start:end]):
        return src
    # insert after the member declarations block (before first function/task)
    fm = re.search(r'\n(\s*)(function|task|covergroup)\b', src[body_start:end])
    pos = body_start + (fm.start() + 1 if fm else 0)
    if fm and fm.group(2) == 'covergroup':
        # constructor must come after the covergroup declaration
        cg_end = src.find('endgroup', pos)
        pos = src.find('\n', cg_end) + 1
        src = src[:pos] + '\n' + src[pos:]
        pos += 1
    return src[:pos] + CTOR.format(extra=extra) + src[pos:]

def fix_file(path, prefix):
    src = open(path).read()
    orig = src
    b = os.path.basename(path)
    if b.endswith('_driver.svh'):
        if not re.search(r'\bap\s*;', src):
            src = re.sub(r'(class\s+\w+_driver\s+extends\s+uvm_driver\s*#\((\w+)\);\s*\n\s*`uvm_component_utils\(\w+\)\n)',
                         lambda m: m.group(1) + "\n  uvm_analysis_port #(%s) ap;  // expected-item stream to scoreboard\n"
                         "  int unsigned item_cnt = 0;\n" % m.group(2), src, count=1)
        src = add_ctor(src, r'uvm_driver\s*#\(\w+\)', '    ap = new("ap", this);\n')
        # reset is owned by top_tb; the driver only waits for it
        src = re.sub(r'vif\.drv_cb\.rst_n\s*<=\s*1\'b0;\s*\n\s*repeat\s*\(\d+\)\s*@\(vif\.drv_cb\);\s*\n\s*vif\.drv_cb\.rst_n\s*<=\s*1\'b1;',
                     "wait (vif.rst_n === 1'b1);", src)
    elif b.endswith('_monitor.svh'):
        src = add_ctor(src, r'uvm_monitor')
    elif b.endswith('_agent.svh'):
        src = add_ctor(src, r'uvm_agent')
    elif b.endswith('_sequencer.svh'):
        src = add_ctor(src, r'uvm_sequencer\s*#\(\w+\)')
    elif b.endswith('_checker.svh'):
        src = add_ctor(src, r'uvm_component')
    elif b.endswith('_coverage.svh'):
        m = re.search(r'\n\s*(\w+_cg)\s*=\s*new\(\);\n', src)
        if m:
            cg = m.group(1)
            src = src.replace(m.group(0), '\n', 1)
            src = add_ctor(src, r'uvm_subscriber\s*#\(\w+\)', '    %s = new();\n' % cg)
        else:
            src = add_ctor(src, r'uvm_subscriber\s*#\(\w+\)')
    if b.endswith('_sequences.svh'):
        src = re.sub(r'`uvm_do_with\(req, 1 == 1\);?', '`uvm_do(req)', src)
    if b == 'top_tb.sv':
        # include guards generated from the display name ("ACE-Lite", "1-Wire",
        # "IEEE 1588 PTP") are not identifiers; derive them from the dir name
        guard = re.sub(r'\W', '_', os.path.basename(os.path.dirname(os.path.dirname(path)))).upper() + '_TB_SV'
        src = re.sub(r'^(`(?:ifndef|define))[ \t]+(?![A-Za-z_]\w*_TB_SV\s*$)[^\n]*_TB_SV[ \t]*$',
                     lambda m: m.group(1) + ' ' + guard, src, flags=re.M)
    if b == 'sent_compliance_checker.sv':
        # so_d is the DUT's 1-cycle delayed sens_out: a strobe follows a rising edge
        src = src.replace('$rose(nibble_valid) |-> $fell(so_d)',
                          '$rose(nibble_valid) |-> ($past(sens_out, 1) && !$past(sens_out, 2))')
    if b == 'uec_compliance_checker.sv':
        # v2/bad2 are DUT-internal; rx_valid is tx_valid delayed by 3 cycles,
        # and tx_ready is tied high, so the reset check applies to rx_valid
        src = src.replace('rx_valid |-> $past(v2, 2) || $past(bad2, 2) == 1\'b0', 'rx_valid |-> $past(tx_valid, 3)')
        src = src.replace("!rst_n |-> tx_ready == '0", "!rst_n |-> rx_valid == '0")
    if src != orig:
        open(path, 'w').write(src)
        return True
    return False

if __name__ == '__main__':
    for d in sys.argv[1:]:
        n = 0
        for f in sorted(glob.glob(os.path.join(d, '**', '*.sv*'), recursive=True)):
            n += fix_file(f, None)
        print('%s: %d file(s) fixed' % (os.path.basename(d.rstrip('/')), n))
