#!/usr/bin/env bash
# Copyright 2026 VIP Portfolio Contributors
# SPDX-License-Identifier: Apache-2.0
# Install the open-source toolchain used by the L1 gates and functional tests:
#   * Icarus Verilog 13.0 (built from source, tag v13_0)
#                                           -> smoke/run_smoke.sh, tools/run_func_tests.py
#   * Verilator v5.054 (built from source)  -> tools/run_func_tests.py fallback for
#                                              DUT models Icarus cannot parse, and
#                                              tools/run_uvm_tests.py (UVM / RAL)
#   * z3 (distro package)                   -> Verilator constraint solver (randomize)
#   * pyslang                               -> tools/elab_scan.py
#   * Accellera uvm-core                    -> tools/elab_scan.py ($UVM_CORE)
# Usage: bash tools/install_tools.sh
# Env:   VERILATOR_VERSION (default v5.054), VERILATOR_PREFIX (default /opt/verilator-<ver>),
#        IVERILOG_TAG (default v13_0), IVERILOG_PREFIX (default /opt/iverilog-<tag>),
#        PYSLANG_SPEC (default "pyslang==12.0.0"), UVM_CORE_DIR (default <repo>/uvm-core),
#        UVM_CORE_TAG (default 2020.3.1)
# Prints the PATH entry to add for Verilator and Icarus. Needs sudo for apt and the prefix.
set -euo pipefail
REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VER="${VERILATOR_VERSION:-v5.054}"
PREFIX="${VERILATOR_PREFIX:-/opt/verilator-${VER#v}}"
IV_TAG="${IVERILOG_TAG:-v13_0}"
IV_PREFIX="${IVERILOG_PREFIX:-/opt/iverilog-${IV_TAG#v}}"
PYSLANG_SPEC="${PYSLANG_SPEC:-pyslang==12.0.0}"
UVM_DIR="${UVM_CORE_DIR:-$REPO/uvm-core}"
# pinned so gate results do not move with uvm-core's default branch
UVM_TAG="${UVM_CORE_TAG:-2020.3.1}"
SUDO=""; [ "$(id -u)" -eq 0 ] || SUDO="sudo"

$SUDO apt-get update -qq
$SUDO apt-get install -y -qq git autoconf flex bison gperf help2man libfl-dev \
    make g++ perl python3 python3-pip ccache z3 >/dev/null

if [ ! -x "$IV_PREFIX/bin/iverilog" ]; then
  src="$(mktemp -d)"
  git clone -q --depth 1 --branch "$IV_TAG" https://github.com/steveicarus/iverilog.git "$src"
  (cd "$src" && sh autoconf.sh >/dev/null 2>&1 && ./configure --prefix="$IV_PREFIX" >/dev/null \
     && make -j"$(nproc)" >/dev/null && $SUDO make install >/dev/null)
  rm -rf "$src"
fi

if [ ! -x "$PREFIX/bin/verilator" ]; then
  src="$(mktemp -d)"
  git clone -q --depth 1 --branch "$VER" https://github.com/verilator/verilator.git "$src"
  (cd "$src" && autoconf && ./configure --prefix="$PREFIX" >/dev/null \
     && make -j"$(nproc)" >/dev/null && $SUDO make install >/dev/null)
  rm -rf "$src"
fi
"$PREFIX/bin/verilator" --version

python3 -m pip install -q "$PYSLANG_SPEC" 2>/dev/null \
  || python3 -m pip install -q --break-system-packages "$PYSLANG_SPEC"
python3 -c "import pyslang; print('pyslang', pyslang.__version__)"

[ -f "$UVM_DIR/src/uvm_pkg.sv" ] \
  || git clone -q --depth 1 --branch "$UVM_TAG" https://github.com/accellera-official/uvm-core.git "$UVM_DIR"
# no "| head": with pipefail, iverilog dying of SIGPIPE made the script exit 141
"$IV_PREFIX/bin/iverilog" -V 2>&1 | sed -n 1p
echo "export PATH=$PREFIX/bin:$IV_PREFIX/bin:\$PATH UVM_CORE=$UVM_DIR/src"
