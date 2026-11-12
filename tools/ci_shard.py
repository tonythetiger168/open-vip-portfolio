#!/usr/bin/env python3
# Copyright 2026 VIP Portfolio Contributors
# SPDX-License-Identifier: Apache-2.0
"""ci_shard.py <vips|uvm> <index> <count> | <vips-all|uvm-all>

Print one name per line for a round-robin shard of the catalog.

``vips`` is every ``vips/*.zip`` stem (the elaboration / smoke / SVA /
functional / coverage set). ``uvm`` is every suite ``tools/run_uvm_tests.py``
runs when given no names. Shards are disjoint and their union is the full
set. An empty shard exits 1 so a bad shard count cannot silently drop work.
"""
import glob, os, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def vip_names():
    names = []
    for path in glob.glob(os.path.join(ROOT, "vips", "*.zip")):
        names.append(os.path.basename(path)[:-4])
    return sorted(names)


def uvm_names():
    sys.path.insert(0, os.path.join(ROOT, "tools"))
    import run_uvm_tests
    return sorted(run_uvm_tests.SUITES)


def shard(names, index, count):
    if count < 1 or index < 0 or index >= count:
        raise SystemExit("shard index %s out of range for count %s" % (index, count))
    return [name for i, name in enumerate(names) if i % count == index]


def main(argv):
    if not argv or argv[0] not in ("vips", "uvm", "vips-all", "uvm-all"):
        raise SystemExit("usage: ci_shard.py <vips|uvm> <index> <count> | <vips-all|uvm-all>")
    kind = argv[0]
    full = vip_names() if kind.startswith("vips") else uvm_names()
    if kind.endswith("-all"):
        picked = full
    else:
        if len(argv) != 3:
            raise SystemExit("usage: ci_shard.py %s <index> <count>" % kind)
        picked = shard(full, int(argv[1]), int(argv[2]))
        if not picked:
            raise SystemExit("empty %s shard %s/%s" % (kind, argv[1], argv[2]))
    print("\n".join(picked))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
