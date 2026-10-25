# DDR5 command/data agent (tb/top_tb.sv ddr5_model: 4 banks x 8k x 128b,
# read data four pipeline stages after the RD command).
from _lib import dram_spec

SPEC = dram_spec("DDR5-VIP", "ddr5", "DDR5", 128, 5, [("bit [1:0]", "bank", "bank")])
# SVA: rd_valid follows a RD command by the read latency (five clocks); the
# original check ($fell(cs_n) || $past(rd_valid, 4)) fails on every isolated read
SPEC["patches"] = {"ddr5/sva/ddr5_compliance_checker.sv": [(
    "rd_valid |-> $fell(cs_n) || $past(rd_valid, 4))",
    "rd_valid |-> $past(!cs_n && act_n && addr[0], 5))")]}
