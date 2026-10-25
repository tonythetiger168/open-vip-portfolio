# LPDDR6 command/data agent (tb/top_tb.sv lpddr6_model: 4 banks x 8k x 64b,
# read data six pipeline stages after the RD command; self_ref freezes the
# device and drops outstanding reads).
from _lib import dram_spec

SPEC = dram_spec("LPDDR6-VIP", "lpddr6", "LPDDR6", 64, 7, [("bit [1:0]", "bank", "bank")], sref=True)
