# HBM3E command/data agent (tb/top_tb.sv hbm3e_model: 4 stacks x 2 pseudo
# channels x 8k x 256b, read data three pipeline stages after the RD command).
from _lib import dram_spec

SPEC = dram_spec("HBM3E-VIP", "hbm3e", "HBM3E", 256, 4,
                 [("bit [1:0]", "stack", "stack"), ("bit", "pchan", "pchan")])
