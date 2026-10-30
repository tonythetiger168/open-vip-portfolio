#!/usr/bin/env python3
# Copyright 2026 VIP Portfolio Contributors
# SPDX-License-Identifier: Apache-2.0
"""sync_xchk_models.py [--check DIR] [VIP ...] -- ship the independent
protocol models of ipcheck/ inside the matching VIP zips.

Each VIP below gets an ``xchk/`` directory: the cross-check testbench (the
protocol model written from the specification), the shared APB requester
when the bench uses it, and a README with the run command against an
open-ip-portfolio checkout. ipcheck/ stays the master copy: rerun this after
changing a bench. The zip is unpacked to a temporary tree, its old xchk/ is
replaced, and tools/pack_vips.sh repacks it.

--check DIR additionally runs every shipped bench from the unpacked VIP tree
against the open-ip-portfolio checkout in DIR, with the command its README
gives.
"""
import os, re, sys, shutil, zipfile, tempfile, argparse, subprocess

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
IPCHK = os.path.join(ROOT, "ipcheck")

# VIP -> (bench, extra ipcheck files, open-ip rtl files, defines, model, specification)
APB = ["apb_bfm.svh"]
MODELS = {
    "UART-VIP": ("uart_xchk_tb.sv", APB, ["UART_top.sv", "UART_apb.sv"], [],
                 "an 8N1 line receiver timing every edge and a line driver at -2.5 .. +2.5 % baud",
                 "the UART character format (start, 8 data bits LSB first, stop)"),
    "SPI-VIP": ("spi_xchk_tb.sv", APB, ["SPI_top.sv", "SPI_apb.sv"], [],
                "a mode-0 SPI controller (MSB first, MISO setup before each SCLK rise)",
                "SPI mode 0 (CPOL = 0, CPHA = 0)"),
    "I2C-VIP": ("i2c_xchk_tb.sv", APB, ["I2C_top.sv", "I2C_apb.sv"], [],
                "an I2C controller on an open-drain bus with a monitor for SDA changes while SCL is high",
                "NXP UM10204, the I2C-bus specification"),
    "GPIO-UVM-VIP": ("gpio_xchk_tb.sv", APB, ["GPIO_top.sv", "GPIO_apb.sv"], [],
                     "a board model driving or floating each pin, every pin checked as 0 / 1 / Z",
                     "the register map and pin rules of open-ip docs/ip/GPIO.md"),
    "PWM-UVM-VIP": ("pwm_xchk_tb.sv", APB, ["PWM_top.sv", "PWM_apb.sv"], [],
                    "the waveform computed from the documented PERIOD / DUTY rule, compared clock by clock",
                    "the PWM rule of open-ip docs/ip/PWM.md"),
    "I2S-VIP": ("i2s_xchk_tb.sv", APB, ["I2S_top.sv", "I2S_apb.sv"], [],
                "an I2S bus master (WS on the BCLK falling edge, MSB one BCLK after it)",
                "the Philips I2S bus specification"),
    "SD-VIP": ("sd_xchk_tb.sv", APB, ["SD_top.sv", "SD_apb.sv"], [],
               "an SD memory card: CRC7 / CRC16, R1 / R2 / R3 / R6 / R7, identification, injected card faults "
               "(add -DSC for a standard-capacity card)",
               "the SD Physical Layer Simplified Specification"),
    "eMMC-VIP": ("emmc_xchk_tb.sv", APB, ["eMMC_top.sv", "eMMC_apb.sv"], [],
                 "an e*MMC device: R1 / R2 / R3, device states, sector addresses, CRC16 data, CRC status and busy, "
                 "injected device faults",
                 "JEDEC JESD84 (e*MMC 5.1)"),
    "USB-VIP": ("usb_xchk_tb.sv", APB, ["USB_top.sv", "USB_apb.sv"], [],
                "a USB 2.0 full-speed host: NRZI, bit stuffing, CRC5 / CRC16, a line receiver timing every "
                "J / K / SE0 interval, chapter 9 enumeration, toggles, STALL, CRC and stuffing faults",
                "the USB 2.0 specification, chapters 7, 8 and 9"),
    "DDR-VIP": ("ddr_xchk_tb.sv", ["ddr_pin_mon.sv"], ["DDR4_Lite_top.sv"], [],
                "ddr_pin_mon.sv on the DRAM pins: the JESD79-4 command truth table, timing rules, burst "
                "latency, data against a shadow array, refresh intervals",
                "JEDEC JESD79-4 (DDR4)"),
    "lpddr5x-VIP": ("ddr_xchk_tb.sv", ["ddr_pin_mon.sv"], ["LPDDR5X_Lite_top.sv"], ["LPDDR"],
                    "ddr_pin_mon.sv on the DRAM pins: command rules, per-bank refresh, the two FSP sets, "
                    "WCK only through writes, data against a shadow array",
                    "the JESD79-4 pin rules as the IP documents them for its LPDDR5X slice"),
}

def top_of(bench):
    return re.search(r"^module\s+(\w+)", open(os.path.join(IPCHK, bench)).read(), re.M).group(1)

def cmd_of(vip):
    bench, extra, rtl, defs, _, _ = MODELS[vip]
    srcs = [f"$OIP/rtl/{r}" for r in rtl] + [f"xchk/{e}" for e in extra if e.endswith(".sv")] + [f"xchk/{bench}"]
    d = "".join(f" -D{x}" for x in defs)
    return f"iverilog -g2012{d} -I xchk -s {top_of(bench)} -o xchk.vvp {' '.join(srcs)} && vvp -n xchk.vvp"

def readme(vip):
    bench, extra, rtl, defs, model, spec = MODELS[vip]
    ip = rtl[0].replace("_top.sv", "")
    return f"""# Independent cross-check model (`xchk/`)

`{bench}` checks the open-ip-portfolio `{ip}` RTL ({', '.join('`rtl/' + r + '`' for r in rtl)})
against {model}. The model is written from {spec}, not from the RTL, so it
gives a second opinion next to the RTL's own testbench. It is the bench of
`ipcheck/{bench}` in open-vip-portfolio (see `ipcheck/README.md` there for
the full list of checks, the planted faults it catches and the notes it
reports).

Run from the VIP root with Icarus Verilog 12 (Verilator 5.052 with
`--binary --timing` also works):

```
OIP=/path/to/open-ip-portfolio
{cmd_of(vip)}
```

Pass: a line `XCHK_PASS checks=N`. Any `[FAIL]` line fails the run;
`[NOTE]` lines report differences from the specification that do not
change the result. `-DSEED=<n>` changes the random stimulus.
"""

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", metavar="OPEN_IP_DIR")
    ap.add_argument("vips", nargs="*")
    a = ap.parse_args()
    vips = a.vips or list(MODELS)
    tmp = tempfile.mkdtemp(prefix="xchk_")
    bad = 0
    try:
        for v in vips:
            bench, extra, *_ = MODELS[v]
            zp = os.path.join(ROOT, "vips", v + ".zip")
            with zipfile.ZipFile(zp) as z:
                z.extractall(tmp)
            d = os.path.join(tmp, v, "xchk")
            shutil.rmtree(d, ignore_errors=True)
            os.makedirs(d)
            for f in [bench] + extra:
                shutil.copy(os.path.join(IPCHK, f), d)
            open(os.path.join(d, "README.md"), "w").write(readme(v))
            subprocess.run(["bash", os.path.join(ROOT, "tools", "pack_vips.sh"), v], check=True,
                           env=dict(os.environ, VIPS_DIR=tmp))
            if a.check:
                c = cmd_of(v).replace("$OIP", os.path.abspath(a.check))
                p = subprocess.run(c, shell=True, cwd=os.path.join(tmp, v), capture_output=True, text=True,
                                   timeout=1800)
                m = re.search(r"XCHK_(PASS|FAIL)[^\n]*", p.stdout)
                res = m.group(0) if m else "XCHK_ERROR " + (p.stdout + p.stderr).strip().splitlines()[-1][:120]
                print(f"{v:14s} {res}")
                bad += not res.startswith("XCHK_PASS")
                for f in ("xchk.vvp",):
                    try: os.remove(os.path.join(tmp, v, f))
                    except OSError: pass
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    return 1 if bad else 0

if __name__ == "__main__":
    sys.exit(main())
