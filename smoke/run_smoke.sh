#!/usr/bin/env bash
# Icarus Verilog smoke test for VIP functional DUT models.
# Usage:
#   bash run_smoke.sh            -> run every extracted VIP
#   bash run_smoke.sh <VIP_DIR>  -> run one VIP (dir name e.g. AHB-VIP, or full path)
# VIPs are read from $VIPS_DIR (default <repo>/build/vips); populate it first with
# tools/extract_vips.sh. Exits non-zero if no VIP is found.
# Prints SMOKE_PASS / SMOKE_FAIL / SMOKE_SKIP per VIP; details in <VIP>/smoke.log,
# summary in smoke_report.csv.
set -u
shopt -s nullglob
SMOKE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
export VIPS_DIR="${VIPS_DIR:-$(dirname "$SMOKE_DIR")/build/vips}"

if [ ! -d "$VIPS_DIR" ]; then
  echo "ERROR: $VIPS_DIR not found; run tools/extract_vips.sh first" >&2
  exit 1
fi

merge_csv() {
  python3 - "$SMOKE_DIR" <<'PY'
import sys, importlib.util
spec = importlib.util.spec_from_file_location("sr", sys.argv[1] + "/smoke_run.py")
sr = importlib.util.module_from_spec(spec); spec.loader.exec_module(sr)
sr.merge_csv()
PY
}

if [ $# -ge 1 ]; then
  v="$(basename "$1")"
  [ -d "$VIPS_DIR/$v" ] || { echo "SMOKE_SKIP $v -- no such VIP dir"; exit 1; }
  python3 "$SMOKE_DIR/flatten.py" "$v" >/dev/null 2>&1
  python3 "$SMOKE_DIR/smoke_run.py" "$v"
else
  vips=("$VIPS_DIR"/*-VIP)
  if [ ${#vips[@]} -eq 0 ]; then
    echo "ERROR: no *-VIP directory under $VIPS_DIR; run tools/extract_vips.sh first" >&2
    exit 1
  fi
  echo "Running smoke on ${#vips[@]} VIPs from $VIPS_DIR"
  printf '%s\n' "${vips[@]}" | xargs -n1 basename | xargs -P 3 -I{} bash -c \
    'python3 "'"$SMOKE_DIR"'/flatten.py" "$0" >/dev/null 2>&1; python3 "'"$SMOKE_DIR"'/smoke_run.py" "$0"' {}
  merge_csv
fi
