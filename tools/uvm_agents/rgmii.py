# RGMII agent (tb/top_tb.sv rgmii_model: single-edge model of the DDR bus,
# rxd/rx_ctl looped back onto txd/tx_ctl one clock later; one nibble per
# clock, low nibble first).
from _lib import eth_spec

SPEC = eth_spec("RGMII-UVM-VIP", "rgmii", "RGMII", 4, ("rxd", "rx_ctl"), ("txd", "tx_ctl"))
