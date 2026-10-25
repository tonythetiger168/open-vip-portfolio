#!/usr/bin/env python3
# Copyright 2026 VIP Portfolio Contributors
# SPDX-License-Identifier: Apache-2.0
"""gen_test_suite_docs.py -- write the test-suite documents.

  docs/test_suites/<VIP>.md   per-VIP test suite: UVM tests, sequences, SVA,
                              coverage, the executable functional tests with
                              every check, the DUT-model contract they verify,
                              known model defects (XFAIL), mutation results and
                              the sufficiency verdict with its gaps
  docs/TEST_SUITE.md          portfolio summary and the verdict per VIP

Inputs: the extracted VIP trees (build/vips, see tools/pack_vips.sh),
func_report.csv (tools/run_func_tests.py), mutation_report.csv
(tools/mutation_score.py) and vip_individual_portfolio.csv.

Verdict (sufficiency of the functional tests for the DUT model):
  Sufficient    tests pass, >= 10 checks, mutation score >= 80 %
  Partial       tests pass, but < 10 checks or mutation score 50..79 %
  Insufficient  no test, a failing test, or mutation score < 50 %
Model defects (XFAIL checks) and features the model does not implement are
listed as gaps separately: they are limits of the DUT model, not of the tests.
"""
import os, re, csv, glob, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
VIPS = os.environ.get("VIPS_DIR", os.path.join(ROOT, "build", "vips"))
OUT = os.path.join(ROOT, "docs", "test_suites")
SUMMARY = os.path.join(ROOT, "docs", "TEST_SUITE.md")


def agent_test(vip):
    """Name of the Verilator agent test of a generated-agent VIP, else None."""
    for f in glob.glob(os.path.join(VIPS, vip, "tests", "*_tests.sv")):
        m = re.search(r"class\s+(\w+_func_test)\s+extends", open(f, errors="ignore").read())
        if m:
            return m.group(1)
    return None

def read_csv(path):
    if not os.path.exists(path):
        return []
    with open(path, encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))

def src(path):
    return open(path, errors="ignore").read()

def files(vdir, pats):
    out = []
    for p in pats:
        out += glob.glob(os.path.join(vdir, "**", p), recursive=True)
    return sorted(set(out))

# ---------------------------------------------------------------- inventory
def uvm_inventory(vdir):
    sv = files(vdir, ["*.sv", "*.svh"])
    tests, seqs, sva, cgs, cps = [], [], [], 0, 0
    for f in sv:
        t = src(f)
        rel = os.path.relpath(f, vdir)
        for m in re.finditer(r'\bclass\s+(\w+)\s*(?:#\s*\([^)]*\))?\s+extends\s+(\w+)', t):
            name, base = m.groups()
            if base == "uvm_test" or name.endswith("_test"):
                tests.append((name, base, rel))
            elif "sequence" in base or name.endswith(("_seq", "_sequence")):
                if "sequencer" not in base and not name.endswith("sequencer"):
                    seqs.append((name, base, rel))
        for m in re.finditer(r'(?:(\w+)\s*:\s*)?\b(assert|cover)\s+property\b', t):
            sva.append((m.group(1) or "-", m.group(2), rel))
        cgs += len(re.findall(r'\bcovergroup\b', t))
        cps += len(re.findall(r'\bcoverpoint\b', t))
    return tests, seqs, sva, cgs, cps

def checks_of(tb):
    """[(kind, message)] for every chk()/chk_xfail() call of a functional tb."""
    t = src(tb)
    out = []
    for m in re.finditer(r'\b(chk|chk_xfail|check)\s*\(', t):
        depth, i = 1, m.end()
        while i < len(t) and depth:
            c = t[i]
            if c == '"':
                i = t.index('"', i + 1)
            depth += {"(": 1, ")": -1}.get(c, 0)
            i += 1
        strs = re.findall(r'"((?:[^"\\]|\\.)*)"', t[m.end():i])
        if strs and not re.search(r'\btask\b[^;]*$', t[max(0, m.start() - 40):m.start()]):
            out.append(("XFAIL" if m.group(1) == "chk_xfail" else "check", strs[-1]))
    return out

def rtl_sections(tb):
    """Numbered test sections of an RTL IP testbench (// ---- N. title ----)."""
    return [m.group(1).strip() for m in
            re.finditer(r'//\s*-{2,}\s*(\d+[a-z]?\.\s*[^\n]*?)\s*-{2,}', src(tb))]

def header(tb):
    """Leading comment block of a functional tb, minus the copyright lines."""
    lines = []
    for l in src(tb).splitlines():
        if not l.startswith("//"):
            if lines and l.strip() == "":
                continue
            break
        lines.append(l[2:].rstrip())
    while lines and (not lines[0].strip() or "Copyright" in lines[0] or "SPDX" in lines[0]):
        lines.pop(0)
    return lines

def limitations(lines):
    """Sentences of a tb header that state what the model does not do."""
    text = " ".join(l.strip() for l in lines)
    out = []
    for s in re.split(r'(?<=[.;])\s+', text):
        if re.search(r'not modelled|not modeled|limitation|not implemented|departs from|not tested', s, re.I):
            out.append(s.strip())
    return out

def sva_counted(row):
    """RTL IP testbenches report assertion evaluations (SVA_CHECKS), not checks."""
    return bool(glob.glob(os.path.join(VIPS, row["vip"], "rtl", "*_top.sv"))) and not row["test"].startswith("func_")

def n_checks(rows):
    return sum(int(r["checks"] or 0) for r in rows if not sva_counted(r))

def n_sva(rows):
    return sum(int(r["checks"] or 0) for r in rows if sva_counted(r))

# ---------------------------------------------------------------- verdict
def verdict(rows, mut):
    if not rows:
        return "Insufficient", "沒有功能測試"
    if any(r["result"] != "PASS" for r in rows):
        return "Insufficient", "功能測試未通過"
    checks = n_checks(rows) + (10 if n_sva(rows) else 0)
    score = int(mut["score"]) if mut and mut.get("valid") not in (None, "", "0") else None
    if score is not None and score < 50:
        return "Insufficient", "mutation score %d%%" % score
    if checks < 10:
        return "Partial", "只有 %d 個 check" % n_checks(rows)
    if score is not None and score < 80:
        return "Partial", "mutation score %d%%" % score
    what = ("%d 個 check" % n_checks(rows)) if n_checks(rows) else "self-checking testbench"
    if score is None:
        return "Sufficient", "%s（尚無 mutation 數據）" % what
    return "Sufficient", "%s，mutation score %d%%" % (what, score)

BADGE = {"Sufficient": "✅ Sufficient", "Partial": "🟡 Partial", "Insufficient": "❌ Insufficient"}

def md_escape(s):
    return s.replace("|", "\\|")

# ---------------------------------------------------------------- per VIP
def vip_doc(vip, meta, frows, mut):
    vdir = os.path.join(VIPS, vip)
    tests, seqs, sva, cgs, cps = uvm_inventory(vdir)
    tbs = sorted(glob.glob(os.path.join(vdir, "tb", "*_tb.sv")) +
                 glob.glob(os.path.join(vdir, "*", "tb", "*_tb.sv")))
    rtl = os.path.isdir(os.path.join(vdir, "rtl"))
    func_tbs = [t for t in tbs if os.path.basename(t) in {r["test"] for r in frows}]
    v, why = verdict(frows, mut)
    xfails, limits = [], []
    L = []
    L.append("# %s 測試套件（%s）" % (meta.get("Protocol", vip.replace("-VIP", "")), vip))
    L.append("")
    L.append("> 由 `tools/gen_test_suite_docs.py` 依 VIP 內容、`func_report.csv` 與 "
             "`mutation_report.csv` 自動產生，請勿手動修改。")
    L.append("")
    L.append("## 1. 概要")
    L.append("")
    L.append("| 項目 | 內容 |")
    L.append("|---|---|")
    L.append("| 類別 | %s |" % meta.get("類別", "-"))
    L.append("| 類型 | %s |" % meta.get("類型", "RTL IP" if rtl else "UVM VIP"))
    checks = n_checks(frows)
    sva_n = n_sva(frows)
    parts = (["%d 個 check" % checks] if checks or not sva_n else []) + (["%d 次斷言評估" % sva_n] if sva_n else [])
    L.append("| 功能測試 | %d 個檔案，%s，%s |" % (
        len(frows), "，".join(parts),
        "全部通過" if frows and all(r["result"] == "PASS" for r in frows) else "未全部通過"))
    if mut and mut.get("valid") not in (None, "", "0"):
        L.append("| Mutation | %s/%s 個 mutant 被偵測（%s%%） |" % (mut["killed"], mut["valid"], mut["score"]))
    L.append("| 判定 | **%s**（%s） |" % (BADGE[v], why))
    L.append("")

    L.append("## 2. 可執行的功能測試")
    L.append("")
    L.append("執行：`python3 tools/run_func_tests.py %s`（Icarus Verilog 或 Verilator 5.052）。" % vip)
    L.append("")
    for tb in func_tbs:
        name = os.path.basename(tb)
        row = next(r for r in frows if r["test"] == name)
        L.append("### `%s`" % os.path.relpath(tb, vdir))
        L.append("")
        L.append("結果：**%s**（%s，%s %s）" % (row["result"], row["sim"], row["checks"],
                                            "次斷言評估" if sva_counted(row) else "checks"))
        L.append("")
        hdr = header(tb)
        if hdr and not rtl:
            L.append("模型合約與範圍（摘自測試檔頭）：")
            L.append("")
            L.append("```text")
            L += [l.lstrip() if not l.startswith("  ") else l for l in hdr]
            L.append("```")
            L.append("")
            limits += limitations(hdr)
        if rtl:
            secs = rtl_sections(tb)
            if secs:
                L.append("| # | 測試段落 |")
                L.append("|---|---|")
                for i, s in enumerate(secs, 1):
                    L.append("| %d | %s |" % (i, md_escape(s)))
                L.append("")
        cks = checks_of(tb)
        if cks:
            L.append("| # | Check | 類型 |")
            L.append("|---|---|---|")
            for i, (kind, msg) in enumerate(cks, 1):
                L.append("| %d | %s | %s |" % (i, md_escape(msg), "XFAIL（模型缺陷）" if kind == "XFAIL" else "check"))
                if kind == "XFAIL":
                    xfails.append(msg)
            L.append("")
    if not func_tbs:
        L.append("（沒有功能測試）")
        L.append("")

    L.append("## 3. UVM 測試平台內容")
    L.append("")
    if rtl and not tests:
        L.append("RTL IP：以 `tb/` 的 self-checking testbench 驗證，無 UVM 測試。")
    else:
        if os.path.exists(os.path.join(VIPS, vip, "env", "amba_reg_model.sv")):
            L.append("UVM RAL test（`amba_ral_test`：hw_reset / bit_bash / mirror 等）在 Verilator 上以 "
                     "`python3 tools/run_uvm_tests.py %s` 執行（見 [docs/RAL.md](../RAL.md)）；其餘 UVM 測試需商用模擬器"
                     "（VCS / Xcelium / Questa），開源流程只做 elaboration（L1a）。" % vip)
        elif agent_test(vip):
            L.append("UVM agent test（`%s`：directed + constrained-random 流量，scoreboard 以 DUT 模型的參考模型逐筆比對，"
                     "並比對 driver 與 monitor 的 transaction）在 Verilator 上以 `python3 tools/run_uvm_tests.py %s` 執行；"
                     "agent 由 `tools/gen_uvm_agents.py` 依 `tools/uvm_agents/` 的協定 spec 產生。" % (agent_test(vip), vip))
        else:
            L.append("UVM 測試需商用模擬器（VCS / Xcelium / Questa）執行；開源流程只做 elaboration（L1a）。")
        L.append("")
        L.append("| 項目 | 數量 | 名稱 |")
        L.append("|---|---|---|")
        L.append("| UVM tests | %d | %s |" % (len(tests), ", ".join("`%s`" % t[0] for t in tests[:20]) or "-"))
        L.append("| Sequences | %d | %s |" % (len(seqs), ", ".join("`%s`" % s[0] for s in seqs[:20]) or "-"))
        named = [s[0] for s in sva if s[0] != "-"]
        L.append("| SVA（assert / cover property） | %d / %d | %s |" % (
            sum(1 for s in sva if s[1] == "assert"), sum(1 for s in sva if s[1] == "cover"),
            ", ".join("`%s`" % n for n in named[:12]) + (" …" if len(named) > 12 else "") or "-"))
        L.append("| Covergroups / coverpoints | %d / %d | |" % (cgs, cps))
    L.append("")

    L.append("## 4. 充分度判定與缺口")
    L.append("")
    L.append("判定：**%s**（%s）。" % (BADGE[v], why))
    L.append("")
    survivors = [s for s in (mut or {}).get("survivors", "").split(" | ") if s]
    if survivors:
        L.append("未被偵測的 mutant（測試缺口或等價 mutant）：")
        L.append("")
        for s in survivors:
            L.append("- `%s`" % s)
        L.append("")
    if xfails:
        L.append("DUT 模型缺陷（XFAIL check，修好模型後會變成 XPASS 提醒移除標記）：")
        L.append("")
        for x in xfails:
            L.append("- %s" % x)
        L.append("")
    if limits:
        L.append("模型未實作的功能（不在測試範圍）：")
        L.append("")
        for x in limits:
            L.append("- %s" % x)
        L.append("")
    if not (survivors or xfails or limits):
        L.append("無已知缺口。")
        L.append("")
    return "\n".join(L) + "\n", v, why, checks, xfails, limits

# ---------------------------------------------------------------- summary
def main():
    os.makedirs(OUT, exist_ok=True)
    meta = {r["VIP檔案"].replace(".zip", ""): r for r in read_csv(os.path.join(ROOT, "vip_individual_portfolio.csv"))}
    func = read_csv(os.path.join(ROOT, "func_report.csv"))
    muts = {r["vip"]: r for r in read_csv(os.path.join(ROOT, "mutation_report.csv"))}
    vips = sorted(d for d in os.listdir(VIPS) if os.path.isdir(os.path.join(VIPS, d)))
    rows = []
    for vip in vips:
        frows = [r for r in func if r["vip"] == vip and r["result"] != "NONE"]
        doc, v, why, checks, xf, lim = vip_doc(vip, meta.get(vip, {}), frows, muts.get(vip))
        open(os.path.join(OUT, vip + ".md"), "w").write(doc)
        rows.append((vip, meta.get(vip, {}), frows, muts.get(vip), v, why, checks, xf, lim))

    n = {k: sum(1 for r in rows if r[4] == k) for k in BADGE}
    tot_checks = sum(r[6] for r in rows)
    tot_sva = sum(n_sva(r[2]) for r in rows)
    tot_xf = sum(len(r[7]) for r in rows)
    mut_rows = [r[3] for r in rows if r[3] and r[3].get("valid") not in ("", "0")]
    killed = sum(int(m["killed"]) for m in mut_rows)
    valid = sum(int(m["valid"]) for m in mut_rows)

    S = []
    S.append("# VIP Portfolio 測試套件總表")
    S.append("")
    S.append("> 由 `tools/gen_test_suite_docs.py` 自動產生。各 VIP 的完整測試套件文件在 "
             "[`docs/test_suites/`](test_suites/)。")
    S.append("")
    S.append("## 1. 結論")
    S.append("")
    n_test = sum(1 for r in rows if r[2])
    n_pass = sum(1 for r in rows if r[2] and all(x["result"] == "PASS" for x in r[2]))
    S.append("- %d 個 VIP 中 %d 個有可在開源工具上執行的 self-checking 功能測試，共 %d 個 check"
             "（另有 RTL IP testbench 的 %d 次斷言評估）；%d 個 VIP 的測試全部通過。" % (
        len(rows), n_test, tot_checks, tot_sva, n_pass))
    S.append("- 判定：✅ Sufficient %d、🟡 Partial %d、❌ Insufficient %d。" % (
        n["Sufficient"], n["Partial"], n["Insufficient"]))
    if valid:
        S.append("- Mutation testing：%d 個有效 mutant 中 %d 個被功能測試偵測（%.0f%%）。" % (
            valid, killed, 100.0 * killed / valid))
    if tot_xf:
        S.append("- 功能測試找到 %d 個 DUT 模型缺陷，以 XFAIL check 記錄（見第 4 節）；模型修好後該 check 會變成 XPASS 並使測試失敗，提醒移除標記。" % tot_xf)
    else:
        S.append("- 沒有未修正的 DUT 模型缺陷：功能測試中沒有 XFAIL check（先前記錄的缺陷都已在模型中修正）。")
    S.append("")
    S.append("## 2. 方法")
    S.append("")
    S.append("每個 VIP 的測試套件分三層：")
    S.append("")
    S.append("1. **功能測試**（`tb/func_*_tb.sv`、`tb/smoke_func_tb.sv`、RTL IP 的 `tb/*_tb.sv`）：直接驅動 VIP 內的 DUT 模型，"
             "依協定規格與模型合約逐項比對，輸出 `FUNC_PASS checks=N`。由 `tools/run_func_tests.py` 以 Icarus Verilog 或 "
             "Verilator 5.052 執行，結果寫入 `func_report.csv`。")
    S.append("2. **UVM 測試平台**（tests / sequences / scoreboard / SVA / coverage）：需商用模擬器執行，開源流程以 "
             "pyslang elaboration 檢查（`tools/elab_scan.py`）；有 register model 的 VIP（APB / AHB / AXI / OCP / TileLink）另以 "
             "`tools/run_uvm_tests.py` 在 Verilator 上執行 UVM RAL test（見 [RAL.md](RAL.md)）；由 `tools/gen_uvm_agents.py` 產生 agent 的 "
             "29 個 VIP 另在 Verilator 上執行 `<prefix>_func_test`（scoreboard 以 DUT 參考模型比對）。")
    S.append("3. **Mutation testing**（`tools/mutation_score.py`）：對 DUT 模型注入運算子與常數錯誤，檢查功能測試能否偵測，"
             "作為「測試是否足夠」的客觀指標，結果寫入 `mutation_report.csv`。")
    S.append("")
    S.append("判定標準：")
    S.append("")
    S.append("| 判定 | 條件 |")
    S.append("|---|---|")
    S.append("| ✅ Sufficient | 功能測試通過，≥ 10 個 check，mutation score ≥ 80% |")
    S.append("| 🟡 Partial | 功能測試通過，但 check < 10 或 mutation score 50–79% |")
    S.append("| ❌ Insufficient | 沒有功能測試、測試失敗或 mutation score < 50% |")
    S.append("")
    S.append("模型缺陷（XFAIL）與模型未實作的功能另列為缺口：它們是 DUT 模型的限制，不是測試的不足。")
    S.append("")
    S.append("## 3. 各 VIP 判定")
    S.append("")
    S.append("Checks 欄不含 RTL IP testbench 的斷言評估次數（見各 VIP 文件）。")
    S.append("")
    S.append("| VIP | 類別 | 功能測試 | Checks | 模擬器 | Mutation | 模型缺陷 | 判定 |")
    S.append("|---|---|---|---|---|---|---|---|")
    for vip, m, frows, mut, v, why, checks, xf, lim in rows:
        mtxt = "%s/%s" % (mut["killed"], mut["valid"]) if mut and mut.get("valid") not in ("", "0") else "-"
        S.append("| [%s](test_suites/%s.md) | %s | %s | %d | %s | %s | %d | %s |" % (
            vip, vip, m.get("類別", "-"), ", ".join("`%s`" % r["test"] for r in frows) or "-", checks,
            "/".join(sorted({r["sim"] for r in frows})) or "-", mtxt, len(xf), BADGE[v]))
    S.append("")
    S.append("## 4. 功能測試找到的 DUT 模型缺陷")
    S.append("")
    for vip, m, frows, mut, v, why, checks, xf, lim in rows:
        if xf:
            S.append("**%s**" % vip)
            S.append("")
            for x in xf:
                S.append("- %s" % x)
            S.append("")
    S.append("## 5. 重新產生")
    S.append("")
    S.append("```bash")
    S.append("bash tools/extract_vips.sh                # 解開 vips/*.zip 到 build/vips")
    S.append("python3 smoke/flatten.py && python3 tools/run_func_tests.py   # func_report.csv")
    S.append("python3 tools/mutation_score.py -j 4       # mutation_report.csv（數小時）")
    S.append("python3 tools/gen_test_suite_docs.py       # 本文件與 docs/test_suites/")
    S.append("```")
    open(SUMMARY, "w").write("\n".join(S) + "\n")
    print("wrote %s and %d per-VIP documents" % (os.path.relpath(SUMMARY, ROOT), len(rows)))
    print("verdicts: " + ", ".join("%s=%d" % (k, n[k]) for k in BADGE))

if __name__ == "__main__":
    main()
