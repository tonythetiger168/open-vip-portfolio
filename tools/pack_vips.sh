#!/usr/bin/env bash
# Copyright 2026 VIP Portfolio Contributors
# SPDX-License-Identifier: Apache-2.0
# Repack edited VIP source trees back into vips/<VIP>.zip (inverse of
# tools/extract_vips.sh). Only the named VIPs are repacked.
# Usage:
#   bash tools/pack_vips.sh <VIP> [<VIP>...]   (dirs read from $VIPS_DIR, default build/vips)
# Entries are sorted and stored without extra attributes (-X) so a repack of an
# unchanged tree only differs in timestamps.
set -euo pipefail
REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SRC="${VIPS_DIR:-$REPO/build/vips}"
[ $# -gt 0 ] || { echo "usage: $0 <VIP>..." >&2; exit 1; }
for v in "$@"; do
  v="$(basename "$v")"
  [ -d "$SRC/$v" ] || { echo "ERROR: $SRC/$v not found" >&2; exit 1; }
  out="$REPO/vips/$v.zip"
  rm -f "$out"
  (cd "$SRC" && find "$v" -type f \
      ! -name '*.vvp' ! -name 'simv' ! -name '*.vcd' ! -path '*/obj_dir/*' \
      | LC_ALL=C sort | zip -q -X -@ "$out")
  echo "packed $v -> vips/$v.zip ($(unzip -Z1 "$out" | wc -l) entries)"
done
