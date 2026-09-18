#!/usr/bin/env bash
# Icarus Verilog smoke test for VIP functional DUT models.
# Usage:
#   bash run_smoke.sh            -> run all 87 VIPs
#   bash run_smoke.sh <VIP_DIR>  -> run one VIP (dir name e.g. AHB-VIP, or full path)
# Prints SMOKE_PASS / SMOKE_FAIL / SMOKE_SKIP per VIP; details in <VIP>/smoke.log,
# summary in smoke_report.csv.
set -u
SMOKE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VIPS_DIR="$(dirname "$SMOKE_DIR")/vips"

run_one() {
  local v="$1"
  python3 "$SMOKE_DIR/flatten.py" "$v" >/dev/null 2>&1
  python3 "$SMOKE_DIR/smoke_run.py" "$v"
}

if [ $# -ge 1 ]; then
  v="$(basename "$1")"
  [ -d "$VIPS_DIR/$v" ] || { echo "SMOKE_SKIP $v -- no such VIP dir"; exit 1; }
  run_one "$v"
  python3 - "$SMOKE_DIR" <<'PY'
import sys, importlib.util
spec = importlib.util.spec_from_file_location("sr", sys.argv[1] + "/smoke_run.py")
sr = importlib.util.module_from_spec(spec); spec.loader.exec_module(sr)
sr.merge_csv()
PY
else
  ls -d "$VIPS_DIR"/*-VIP | xargs -n1 basename | xargs -P 3 -I{} bash -c \
    'python3 "'"$SMOKE_DIR"'/flatten.py" "$0" >/dev/null 2>&1; python3 "'"$SMOKE_DIR"'/smoke_run.py" "$0"' {}
  python3 - "$SMOKE_DIR" <<'PY'
import sys, importlib.util
spec = importlib.util.spec_from_file_location("sr", sys.argv[1] + "/smoke_run.py")
sr = importlib.util.module_from_spec(spec); spec.loader.exec_module(sr)
sr.merge_csv()
PY
fi
