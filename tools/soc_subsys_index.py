#!/usr/bin/env python3
# Copyright 2026 VIP Portfolio Contributors
# SPDX-License-Identifier: Apache-2.0
"""soc_subsys_index.py -- list the SoC subsystem VIPs in
vip_individual_portfolio.csv and in the README "SoC Subsystems" section.

Run after tools/gen_soc_subsys_vips.py --pack. Rows and the section are
replaced in place, so a rerun only refreshes sizes and line counts; the
README / CSV totals are recounted from the CSV.
"""
import csv, io, os, re, sys, zipfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CSV = os.path.join(ROOT, "vip_individual_portfolio.csv")
README = os.path.join(ROOT, "README.md")
VERSION, DATE, FAMILY = "v1.12.0", "2026-11-08", "soc-subsys-uvm"
CATEGORY = "SoC Subsystem"
URL = "https://github.com/tonythetiger168/open-vip-portfolio/blob/main/vips/"

# VIP -> (protocol column, open-ip IP)
VIPS = [
    ("AXI4_Manager_Port-UVM-VIP", "AXI4 manager port kit (shared by every subsystem VIP)", "all AXI4-manager IPs"),
    ("CPU_Cluster-UVM-VIP", "CPU cluster memory traffic (AXI4 manager)", "CPU_Cluster"),
    ("GPU-UVM-VIP", "GPU 2D / blit engine (AXI4 manager)", "GPU"),
    ("NPU-UVM-VIP", "NPU convolution engine (AXI4 manager)", "NPU"),
    ("ISP-UVM-VIP", "Camera ISP: sensor input, black level, gain (AXI4 manager)", "ISP"),
    ("Video_Codec-UVM-VIP", "Video codec DPCM encode / decode (AXI4 manager)", "Video_Codec"),
    ("Display_Controller-UVM-VIP", "Display controller scan-out, CRC, underruns (AXI4 manager)", "Display_Controller"),
    ("Audio_DSP-UVM-VIP", "Audio DSP gain / mix / clip (AXI4 manager)", "Audio_DSP"),
    ("Modem-UVM-VIP", "Modem baseband scrambler + CRC-32 (AXI4 manager)", "Modem"),
    ("Sensor_Hub-UVM-VIP", "Always-on sensor hub decimator (AXI4 manager)", "Sensor_Hub"),
    ("SMMU-UVM-VIP", "SMMU / IOMMU translation, TLB, faults (AXI4 subordinate + manager)", "SMMU"),
    ("DMA-UVM-VIP", "System DMA, 4 channels (AXI4 manager)", "DMA"),
    ("Interrupt_Controller-UVM-VIP", "Interrupt controller, priority claim, event log (AXI4 manager)", "Interrupt_Controller"),
    ("Timer_WDT-UVM-VIP", "Timer / watchdog with timestamp ring (AXI4 manager)", "Timer_WDT"),
]


def zip_stats(path):
    files = lines = 0
    with zipfile.ZipFile(path) as z:
        for n in z.namelist():
            if n.endswith((".sv", ".svh", ".v")):
                files += 1
                lines += z.read(n).decode("utf-8", "replace").count("\n")
    return files, lines


def main():
    raw = open(CSV, encoding="utf-8-sig", newline="").read()
    eol = "\r\n" if "\r\n" in raw else "\n"
    rows = list(csv.reader(io.StringIO(raw)))
    head, body = rows[0], [r for r in rows[1:] if r and r[6] != FAMILY]
    names = [v for v, _, _ in VIPS]
    for v, proto, ip in VIPS:
        z = os.path.join(ROOT, "vips", v + ".zip")
        if not os.path.exists(z):
            sys.exit(f"missing vips/{v}.zip: run tools/gen_soc_subsys_vips.py --all --pack first")
        files, lines = zip_stats(z)
        size = f"{max(1, round(os.path.getsize(z) / 1024))}KB"
        # SVA / cover property / covergroup columns: these VIPs use procedural
        # interface checkers and counter coverage (Verilator), so 0 / 0 / 0;
        # checker files: axim_if.sv and ssv_apb_if.sv
        body.append(["", CATEGORY, proto, "UVM VIP", v + ".zip", size, FAMILY, str(files), str(lines),
                     "0", "0", "0", "2", VERSION, DATE, "✅", "PASS(functional)", URL + v + ".zip",
                     "Apache-2.0", ip])
    for i, r in enumerate(body, 1):
        r[0] = str(i)
    out = io.StringIO()
    w = csv.writer(out, lineterminator=eol)
    w.writerow(head)
    w.writerows(body)
    open(CSV, "w", encoding="utf-8-sig", newline="").write(out.getvalue())
    n = len(body)

    # ---- README
    rd = open(README, encoding="utf-8").read()
    sec = [f"### {CATEGORY} ({len(VIPS)})", "",
           "Phone SoC subsystem VIPs for the AXI4-manager IPs of open-ip-portfolio. Each zip is",
           "standalone: APB4 agent + generated RAL, AXI4 subordinate / monitor / coverage (the",
           "manager-port kit), reference-model scoreboards, an RTL snapshot, `tb/top_tb.sv`,",
           "`sim/<ip>.f` and `sim/testlist.txt` for Verilator + uvm-core. See",
           "[docs/SOC_SUBSYS.md](docs/SOC_SUBSYS.md).", "",
           "| Protocol | Type | File | Size |", "|----------|------|------|------|"]
    for r in body:
        if r[6] == FAMILY:
            sec.append(f"| {r[2]} | UVM VIP | `{r[4]}` | {r[5]} |")
    sec = "\n".join(sec) + "\n"
    rd = re.sub(r"### " + re.escape(CATEGORY) + r" \(\d+\)\n.*?(?=\n### |\n---)", "", rd, flags=re.S)
    # after the last protocol table: before the first "---" rule that
    # follows the tables (SoC Bench Libraries or Repository Structure)
    rd = re.sub(r"\n---\n\n## (SoC Bench Libraries|Repository Structure)",
                lambda m: "\n" + sec + m.group(0), rd, count=1)
    rd = re.sub(r"\n\n\n+", "\n\n", rd)
    rd = re.sub(r"badge/VIPs-\d+-", f"badge/VIPs-{n}-", rd)
    rd = re.sub(r"\*\*\d+ UVM VIPs\*\*", f"**{n} UVM VIPs**", rd)
    rd = re.sub(r"collection of \*\*\d+ individual", f"collection of **{n} individual", rd)
    rd = re.sub(r"machine-readable index \(\d+ entries\)", f"machine-readable index ({n} entries)", rd)
    rd = re.sub(r"# \d+ individual VIP zip files", f"# {n} individual VIP zip files", rd)
    open(README, "w", encoding="utf-8").write(rd)
    print(f"CSV: {n} rows ({len(VIPS)} SoC subsystem); README section refreshed")


if __name__ == "__main__":
    main()
