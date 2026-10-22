#!/usr/bin/env bash
# Copyright 2026 VIP Portfolio Contributors
# SPDX-License-Identifier: Apache-2.0
# Install the open-source toolchain used by the L1 gates and functional tests:
#   * Icarus Verilog (distro package)       -> smoke/run_smoke.sh, tools/run_func_tests.py
#   * Verilator v5.052 (built from source)  -> tools/run_func_tests.py fallback for
#                                              DUT models Icarus cannot parse
#   * pyslang                               -> tools/elab_scan.py
#   * Accellera uvm-core                    -> tools/elab_scan.py ($UVM_CORE)
# Usage: bash tools/install_tools.sh
# Env:   VERILATOR_VERSION (default v5.052), VERILATOR_PREFIX (default /opt/verilator-<ver>),
#        PYSLANG_SPEC (default "pyslang==12.0.0"), UVM_CORE_DIR (default <repo>/uvm-core)
# Prints the PATH entry to add for Verilator. Needs sudo for apt and the prefix.
set -euo pipefail
REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VER="${VERILATOR_VERSION:-v5.052}"
PREFIX="${VERILATOR_PREFIX:-/opt/verilator-${VER#v}}"
PYSLANG_SPEC="${PYSLANG_SPEC:-pyslang==12.0.0}"
UVM_DIR="${UVM_CORE_DIR:-$REPO/uvm-core}"
SUDO=""; [ "$(id -u)" -eq 0 ] || SUDO="sudo"

$SUDO apt-get update -qq
$SUDO apt-get install -y -qq iverilog git autoconf flex bison help2man libfl-dev \
    make g++ perl python3 python3-pip ccache >/dev/null

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
  || git clone -q --depth 1 https://github.com/accellera-official/uvm-core.git "$UVM_DIR"
iverilog -V 2>&1 | head -1
echo "export PATH=$PREFIX/bin:\$PATH UVM_CORE=$UVM_DIR/src"
