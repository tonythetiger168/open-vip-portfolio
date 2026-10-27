#!/usr/bin/env python3
# Copyright 2026 VIP Portfolio Contributors
# SPDX-License-Identifier: Apache-2.0
"""gen_uvm_smoke_doc.py -- write docs/UVM_SMOKE.md from uvm_smoke_report.csv
(tools/run_uvm_tests.py --smoke, full run)."""
import os, csv, re, collections

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "uvm_smoke_report.csv")
OUT = os.path.join(ROOT, "docs", "UVM_SMOKE.md")

MEANING = [
    ("PASS", "建置成功、test 跑到結束（時間 > 0），沒有 UVM_ERROR / UVM_FATAL，VIP 自己的 checker 也沒有 warning"),
    ("WARN", "建置成功、跑完、沒有 UVM_ERROR / UVM_FATAL，但 VIP 自己的 checker / SVA 發出 `UVM_WARNING`"),
    ("FAIL", "建置成功，但執行時有 UVM_ERROR / UVM_FATAL、逾時，或在時間 0 就結束（test 沒有送出任何流量）"),
    ("ERROR", "Verilator 無法建置（語法、LRM 違規或 Verilator 不支援的寫法）"),
    ("NONE", "沒有 UVM test（RTL IP 類 VIP，只有 directed testbench）"),
]


def short(detail):
    d = detail.replace(ROOT + os.sep, "")
    d = re.sub(r"build/vips/[^/]+/", "", d)
    d = re.sub(r"\s+", " ", d)
    return d.replace("|", "\\|")[:220]


def main():
    rows = list(csv.DictReader(open(SRC)))
    cnt = collections.Counter(r["result"] for r in rows)
    ran = [r for r in rows if r["result"] != "NONE"]
    out = ["# 手寫 UVM 環境在 Verilator 上的首次執行（--smoke）", "",
           "本文件由 `tools/gen_uvm_smoke_doc.py` 依 `uvm_smoke_report.csv` 產生"
           "（`python3 tools/run_uvm_tests.py --smoke`，全部 VIP 約需數小時）。", "",
           "`tools/run_uvm_tests.py` 的正式 suite（5 個 RAL VIP、29 個產生式 agent）以外，其餘 VIP 的 "
           "UVM 環境（driver / monitor / scoreboard / checker / covergroup）之前只做過 pyslang "
           "elaboration，從未被模擬器執行。`--smoke` 把 VIP 的全部 `.sv` 以 elab_scan 的順序"
           "（package 排在 import 它的檔案之前）、呼叫 `run_test()` 的 module 為 top 建置，"
           "執行 base test 之後第一個衍生 test。沒有 pass 標記可等，所以 PASS 只代表環境能建置、"
           "跑完 sequence 且沒有任何錯誤回報，**不代表** scoreboard 做了有意義的比對。", "",
           "| 結果 | 意義 | VIP 數 |", "|---|---|---|"]
    for k, m in MEANING:
        out.append("| %s | %s | %d |" % (k, m, cnt.get(k, 0)))
    out += ["", "共 %d 個 VIP，其中 %d 個有 UVM test。" % (len(rows), len(ran)), "",
            "## 逐 VIP 結果", "", "| VIP | Test | 結果 | 第一個問題 |", "|---|---|---|---|"]
    order = {k: i for i, (k, _) in enumerate(MEANING)}
    for r in sorted(ran, key=lambda r: (order.get(r["result"], 9), r["vip"].lower())):
        out.append("| %s | `%s` | %s | %s |" % (r["vip"], r["test"], r["result"], short(r["detail"])))
    none = sorted(r["vip"] for r in rows if r["result"] == "NONE")
    if none:
        out += ["", "沒有 UVM test：" + "、".join(none) + "。"]
    open(OUT, "w").write("\n".join(out) + "\n")
    print("wrote", OUT)


if __name__ == "__main__":
    main()
