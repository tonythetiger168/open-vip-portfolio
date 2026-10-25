# EtherCAT slave port (tb/top_tb.sv ethercat_model: MII receive nibbles
# forwarded to the transmit side one clock later, idle nibble 5 outside a
# frame, pd_status registered onto pd_out).
from _lib import eth_spec

SPEC = eth_spec("EtherCAT-VIP", "ethercat", "EtherCAT", 4, ("mii_rxd", "mii_rx_dv"), ("mii_txd", "mii_tx_en"),
                er=("mii_rx_er", "mii_tx_er"))
SPEC["fields"] += [("bit [15:0]", "pd_status", "req"), ("bit [15:0]", "pd_out", "rsp")]
SPEC["drv_idle"] += " vif.drv_cb.pd_status <= '0;"
SPEC["drv_item"] = SPEC["drv_item"].replace("@(vif.drv_cb);\n", "@(vif.drv_cb);\nvif.drv_cb.pd_status <= t.pd_status;\n", 1)
SPEC["mon_run"] = SPEC["mon_run"].replace("frame(l0, t, 0);", "frame(l0, t, 0);\n        t.pd_status = vif.mon_cb.pd_status;") \
                                 .replace("frame(l1, t, 1);", "frame(l1, t, 1);\n        t.pd_out = vif.mon_cb.pd_out;")
SPEC["predict"] += "\nt.pd_out = t.pd_status;   // process data image mirrored"
# EtherCAT frames: EtherType 0x88A4
SPEC["tr_functions"] = SPEC["tr_functions"].replace("build_frame(plen, seed, 16'(plen));   // IEEE 802.3 length field",
                                                    "build_frame(plen, seed, 16'h88A4);    // EtherCAT EtherType")
SPEC["checks"] += """
if (t.bytes.size() > 13 && {t.bytes[12], t.bytes[13]} != 16'h88A4) fail(t, "EtherType is not 0x88A4");"""
SPEC["coverage"] += "\ncp_pd  : coverpoint tr.pd_status { bins zero = {0}; bins ones = {16'hFFFF}; bins other = default; }"
