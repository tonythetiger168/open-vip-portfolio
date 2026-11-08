#!/usr/bin/env bash
# SPDX-License-Identifier: Apache-2.0
# Self-tests of the device models against the IPs they face, from
# open-ip-portfolio (OPEN_IP_RTL, default ../../../open-ip-portfolio/rtl,
# i.e. a sibling checkout of this repository). Verilator 5.
set -euo pipefail
cd "$(dirname "$0")"
RTL=${OPEN_IP_RTL:-../../../open-ip-portfolio/rtl}
[ -d "$RTL" ] || { echo "open-ip-portfolio rtl not found at $RTL (set OPEN_IP_RTL)"; exit 2; }
rc=0
run() {   # tb ip-file
  local tb=$1 ip=$2
  rm -rf "obj_$tb"
  if ! verilator --binary --timing -Wno-fatal -Wno-lint -Wno-style --top-module "$tb" -Mdir "obj_$tb" \
       src/*.sv "$RTL/$ip" "tests/$tb.sv" -o tb > "build_$tb.log" 2>&1; then
    tail -20 "build_$tb.log"; rc=1; return
  fi
  "./obj_$tb/tb" > "sim_$tb.log" 2>&1 || true
  grep -h 'FAIL\|PASS' "sim_$tb.log"
  grep -q '^FUNC_PASS' "sim_$tb.log" || rc=1
}
for t in ${*:-csi2_tx gmii_phy i2s_codec}; do
  case $t in
    csi2_tx)   run csi2_tx_tb   CSI_2_top.sv ;;
    gmii_phy)  run gmii_phy_tb  Ethernet_top.sv ;;
    i2s_codec) run i2s_codec_tb I2S_top.sv ;;
  esac
done
exit $rc
