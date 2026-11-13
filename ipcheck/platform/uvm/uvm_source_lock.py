# SPDX-License-Identifier: Apache-2.0
"""Verify fixture RTL and UVM verification assets before frontend/simulator build."""
import hashlib
import json


def verify_pins(root, here, rtl):
    lock=json.loads((root/'integration/platform/uvm_sources.json').read_text(encoding='utf-8'))
    vip=here.parents[2]
    rtl_by_name={p.name:p for p in rtl}
    for pin in lock['sources']:
        actual=rtl_by_name[pin['path'].split('/')[-1]] if pin['repository']=='open-ip-portfolio' else vip/pin['path']
        if hashlib.sha256(actual.read_bytes()).hexdigest()!=pin['sha256']:
            raise RuntimeError('source differs from UVM lock: '+pin['path'])
    return lock['source_set_sha256']
