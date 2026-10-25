# GMII MAC transmit agent (tb/top_tb.sv gmii_model: txd/tx_en/tx_er looped
# back onto rxd/rx_dv/rx_er one clock later).
from _lib import eth_spec

SPEC = eth_spec("GMII-UVM-VIP", "gmii", "GMII", 8, ("txd", "tx_en"), ("rxd", "rx_dv"), er=("tx_er", "rx_er"))
