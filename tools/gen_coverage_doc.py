#!/usr/bin/env python3
# Copyright 2026 VIP Portfolio Contributors
# SPDX-License-Identifier: Apache-2.0
"""gen_coverage_doc.py -- write docs/COVERAGE.md from coverage_report.csv
(tools/coverage.py): the portfolio coverage summary, the per-VIP table, the
VIPs below the line-coverage goal with the source lines never reached, and
the unhit covergroup bins of the VIPs whose UVM tests run on Verilator.
"""
import os, csv, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REPORT = os.path.join(ROOT, "coverage_report.csv")
OUT = os.path.join(ROOT, "docs", "COVERAGE.md")
LINE_GOAL = 90.0
# reviewed causes of the tests flagged in the report detail
CAUSES = {
    "DigRF-VIP": "DUT model 在兩個 always_ff 都寫 `vif_err`（Verilator MULTIDRIVEN），"
                 "結果取決於排程順序；coverage 建置改變了順序，CRC 錯誤脈衝被另一個 process 清掉。"
                 "這是 model 缺陷，一般建置下測試通過。",
    "HSI-VIP": "與 DigRF-VIP 同一個 MIPI DUT model，原因相同（`vif_err` 雙重驅動）。",
    "SPI-VIP": "測試要比對 MISO 是否為 `1'bz`，Verilator 不支援 top-level tri-state，只能在 Icarus 上跑，"
               "因此量不到 coverage。",
}
METRICS = [("line", "Line / branch"), ("toggle", "Toggle"), ("expr", "Expression"),
           ("assert", "Cover (SVA)"), ("func", "Functional (covergroup)")]

def num(r, k):
    return int(r[k] or 0)

def cell(r, m):
    t = num(r, m + "_total")
    return "%s%% (%d/%d)" % (r[m + "_pct"], num(r, m + "_hit"), t) if t else "-"

def agg(rows, m):
    h = sum(num(r, m + "_hit") for r in rows)
    t = sum(num(r, m + "_total") for r in rows)
    return h, t, (100.0 * h / t if t else 0.0)

def main():
    if not os.path.exists(REPORT):
        print("ERROR: %s not found, run tools/coverage.py first" % REPORT, file=sys.stderr)
        return 1
    with open(REPORT) as f:
        rows = list(csv.DictReader(f))
    measured = [r for r in rows if num(r, "line_total")]
    low = sorted((r for r in measured if float(r["line_pct"]) < LINE_GOAL), key=lambda r: float(r["line_pct"]))
    full = [r for r in measured if float(r["line_pct"]) == 100.0]
    flagged = [r for r in rows if r["detail"]]
    func = [r for r in rows if num(r, "func_total")]

    L = ["# VIP Portfolio Coverage 報告", ""]
    L.append("> 由 `tools/gen_coverage_doc.py` 依 `coverage_report.csv`（`tools/coverage.py`，"
             "Verilator 5.052 `--coverage`）自動產生，請勿手動修改。")
    L += ["", "## 1. 結論", ""]
    L.append("- %d 個 VIP 中 %d 個量到 code coverage（%d 個功能測試中 %d 個在 Verilator 上帶 coverage 執行）。" % (
        len(rows), len(measured), sum(num(r, "tests") for r in rows), sum(num(r, "covered_tests") for r in rows)))
    for m, label in METRICS[:3]:
        h, t, p = agg(measured, m)
        L.append("- %s coverage（全部 DUT model 合計）：%.1f%%（%d/%d）。" % (label, p, h, t))
    L.append("- Line coverage 100%% 的 VIP %d 個，≥ %.0f%% 的 %d 個，低於 %.0f%% 的 %d 個（見第 4 節）。" % (
        len(full), LINE_GOAL, len(measured) - len(low), LINE_GOAL, len(low)))
    if func:
        h, t, p = agg(func, "func")
        L.append("- Functional coverage（covergroup bins，%s 的 UVM RAL test）：%.1f%%（%d/%d），"
                 "其餘 UVM 環境的 covergroup 需商用模擬器（見第 2 節）。" % (
                     " / ".join(r["vip"] for r in func), p, h, t))
    L += ["", "## 2. 方法", ""]
    L.append("`tools/coverage.py` 把每個功能測試（`tools/run_func_tests.py` 的同一組測試與編譯組合）"
             "加上 `--coverage-line --coverage-toggle --coverage-expr --coverage-user` 重新以 Verilator "
             "建置並執行，再依 VIP 合併各測試的 `coverage.dat`。只計算被測的程式碼：UVM VIP 為 "
             "`smoke/<VIP>/dut_*.sv`（flatten 後的 DUT model），RTL IP 為 `rtl/*.sv`；testbench 與 "
             "package 不計。同一個 coverage point 在任一測試、任一 instance 被觸發即算命中。")
    L += ["", "| 指標 | 意義 |", "|---|---|",
          "| Line / branch | 每個 statement block 與每個 if/case 分支是否執行過 |",
          "| Toggle | 每個 signal 的每個 bit 是否都出現過 0→1 與 1→0 |",
          "| Expression | 多項條件式中每一項的組合是否都出現過（類似 FEC / condition coverage） |",
          "| Cover (SVA) | `cover property` / `cover` 是否觸發過（只有部分 model 有） |",
          "| Functional | covergroup 的 bins 命中數（`v_covergroup`） |", ""]
    L.append("限制：")
    L.append("- Toggle 包含寬資料匯流排的高位元與測試中固定不動的 sideband / 其他協定的 tie-off，"
             "所以普遍低於 line coverage，是參考值而非目標。")
    L.append("- Functional coverage 只在 UVM 測試能在 Verilator 上跑的 VIP 量測（APB / AHB / AXI 的 "
             "`amba_ral_test`、OCP 的 `ocp_ral_test`、TileLink 的 `tilelink_ral_test`，見 [RAL.md](RAL.md)）；AMBA VIP 共用 APB/AHB/AXI checker，只計算該 VIP "
             "協定與共用 interface 的 covergroup。其他 VIP 的 covergroup 在 UVM monitor / coverage "
             "collector 裡，需用各 VIP 的 `scripts/coverage.mk`（VCS / Xcelium / Questa）量測。")
    L.append("- 只能在 Icarus 上跑的測試（例如要比對 `1'bz` 的 tri-state 檢查）量不到 coverage；"
             "在 coverage 建置下結果不同的測試仍計入其 coverage，兩者都列在第 5 節。")
    L += ["", "## 3. 各 VIP Coverage", ""]
    L.append("| VIP | 測試 | " + " | ".join(l for _, l in METRICS) + " |")
    L.append("|---|---|" + "---|" * len(METRICS))
    for r in rows:
        L.append("| [%s](test_suites/%s.md) | %s/%s | %s |" % (
            r["vip"], r["vip"], r["covered_tests"], r["tests"], " | ".join(cell(r, m) for m, _ in METRICS)))
    L += ["", "## 4. Line coverage 低於 %.0f%% 的 VIP" % LINE_GOAL, ""]
    if low:
        L.append("未執行到的行號可對照 `build/cov/<VIP>/annotated/`（`%000000` 開頭的行）。"
                 "大多是 model 的錯誤處理、未被測試觸發的協定模式，或已知 model 缺陷（XFAIL，"
                 "見 [TEST_SUITE.md](TEST_SUITE.md) 第 4 節）擋住後段流程。")
        L += ["", "| VIP | Line | 未執行到的行 |", "|---|---|---|"]
        for r in low:
            L.append("| %s | %s%% | %s |" % (r["vip"], r["line_pct"], r["line_missed"].replace("|", "\\|")[:400]))
    else:
        L.append("無。")
    if func:
        L += ["", "### Functional coverage 未命中的 bins", "",
              "| VIP | Functional | 未命中 bins（covergroup.coverpoint(數量)） |", "|---|---|---|"]
        for r in func:
            L.append("| %s | %s | %s |" % (r["vip"], cell(r, "func"), r["func_missed"] or "-"))
    L += ["", "## 5. 備註", ""]
    if flagged:
        for r in flagged:
            L.append("- **%s**：%s%s" % (r["vip"], (CAUSES[r["vip"]] + "<br>") if r["vip"] in CAUSES else "",
                                          r["detail"].replace("|", "\\|")))
    else:
        L.append("無。")
    L += ["", "## 6. 重跑", "", "```bash",
          "bash tools/install_tools.sh && export PATH=/opt/verilator-5.052/bin:$PATH",
          "bash tools/extract_vips.sh",
          "python3 tools/coverage.py -j 2        # coverage_report.csv, build/cov/<VIP>/",
          "python3 tools/coverage.py APB-VIP     # 單一 VIP",
          "python3 tools/gen_coverage_doc.py     # docs/COVERAGE.md", "```", ""]
    with open(OUT, "w") as f:
        f.write("\n".join(L))
    print("wrote %s (%d VIPs)" % (os.path.relpath(OUT, ROOT), len(rows)))
    return 0

if __name__ == "__main__":
    sys.exit(main())
