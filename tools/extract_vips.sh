#!/usr/bin/env bash
# Copyright 2026 VIP Portfolio Contributors
# SPDX-License-Identifier: Apache-2.0
# Extract every vips/*.zip into a work directory so CI and the smoke harness
# have real VIP source trees to scan (the repo only ships the zips).
# Usage:
#   bash tools/extract_vips.sh [DEST]   (default: $VIPS_DIR, else <repo>/build/vips)
# Prints VIP_COUNT=<n>; exits non-zero if no zip is found or any unzip fails.
set -euo pipefail
shopt -s nullglob
REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DEST="${1:-${VIPS_DIR:-$REPO/build/vips}}"

zips=("$REPO"/vips/*.zip)
if [ ${#zips[@]} -eq 0 ]; then
  echo "ERROR: no zip found under $REPO/vips" >&2
  exit 1
fi

rm -rf "$DEST"
mkdir -p "$DEST"
for z in "${zips[@]}"; do
  unzip -q -o "$z" -d "$DEST"
done

dirs=("$DEST"/*/)
echo "VIP_COUNT=${#dirs[@]} (from ${#zips[@]} zips) -> $DEST"
[ ${#dirs[@]} -gt 0 ]
