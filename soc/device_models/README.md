# Device models for SoC benches (soc/device_models)

Plain SystemVerilog models of the device on the far side of an IP's pins, for
a SoC bench that has no UVM agent on those pins. Each one drives the IP's
input pins itself and checks or records what comes back. They are the
standalone counterparts of the CSI2_Sensor, GMII_PHY and I2S_Codec UVM VIPs,
whose DUT models stand in for the host IP and whose agents play the device.

| Model | Faces (open-ip-portfolio) | Drives | Watches |
|---|---|---|---|
| `csi2_tx_model` | `CSI_2_top` | `rx_valid`, `rx_bit` | nothing (`frames_sent`, `done`) |
| `gmii_phy_model` | `Ethernet_top` GMII | `grxd`, `grx_dv`, `grx_er` | `gtxd`, `gtx_en`, `gtx_er` |
| `i2s_codec_model` | `I2S_top` (slave) | `bclk`, `lrck`, `sdin` | `sdout` |

## csi2_tx_model

A camera sensor: `FRAMES` frames (0 = no limit) of FS, `LINES` long packets
of `WIDTH` bytes on virtual channel `VC` with data type `DT` (RAW8 0x2A by
default), and FE, one HS burst per packet: `LEAD` HS-zero bits, sync byte
0xB8, header with ECC, payload, CRC-16, `TRAIL` trailer bits, then `GAP`
clocks with `rx_valid` low. FS / FE carry the frame number (1, 2, ...).
Payload byte `j` of line `l` of frame `f` is
`8'(j) ^ 8'(l * 37) ^ 8'(f * 101)`, so a bench can check the line buffer or
the frame in memory. `en` holds it between bursts; `done` rises after the
last FE.

## gmii_phy_model

The link partner on a MAC's GMII, with a byte time of `DIV + 1` clocks (set
`DIV` to the MAC's `cfg_div`).

- It checks every frame the MAC sends (preamble, SFD, FCS, `gtx_er`):
  `rx_good`, `rx_bad`.
- It sends `GEN_N` frames after reset to `DST_MAC` from `PHY_MAC`, with a
  length field of `GEN_LEN` and payload byte `i` of frame `k` =
  `8'(i) ^ 8'(k * 29)`.
- With `ECHO` it sends each good frame back with DA and SA swapped and a new
  FCS. A SoC frame addressed to `PHY_MAC` therefore comes back to the SoC's
  own address, padded as the MAC sent it. A frame that arrives while the
  previous echo is still pending or going out is dropped and counted in
  `echo_drop`.
- `tx_frames` counts the frames it has sent.

## i2s_codec_model

An ADC + DAC codec that masters the I2S bus.

- `bclk` runs at `DIV` clocks per period. `I2S_top` needs `DIV` of 8 or more.
- `lrck` and `sdin` change on the falling edge, with Philips timing: the MSB
  comes one bclk after the `lrck` change. Words are `DW` bits in `SLOT`-bit
  slots.
- The ADC words of frame `n` are `i2s_codec_adc(n, ch)`, i.e. the low `DW`
  bits of `(n * 32'h10123) ^ (ch ? 32'hA55A : 32'h3C3C)`.
- `sdout` is captured on every rising edge. `dac_valid` pulses with
  `dac_left`, `dac_right` and `dac_frame` once a frame's right word is in.
- `lrck` idles high, so frame 0 starts with an `lrck` change that the slave
  can lock to.
- After `FRAMES` frames (0 = no limit), `bclk` stops high and `done` rises.

## Self-tests

`./run.sh [csi2_tx|gmii_phy|i2s_codec]` builds each model with the real IP
from a sibling open-ip-portfolio checkout (`OPEN_IP_RTL`, default
`../../../open-ip-portfolio/rtl`) under Verilator 5 (`--timing`). The tests
check:

- `csi2_tx`: `CSI_2_top`'s frame and line counts, error flags, FE header and
  line buffer contents. Two set-ups: RAW8 on VC 0 with 3 lines of 20 bytes;
  DT 0x2B on VC 1 with 300-byte lines, a 1-bit trailer and 2-clock gaps.
- `gmii_phy`: the originated frames as `Ethernet_top` receives them, SoC
  frames echoed back (including a short frame padded to 60 bytes), and the
  dropped back-to-back frame. Byte times are 2 and 5 clocks.
- `i2s_codec`: the DAC words `I2S_top` sends from its tx registers before
  and after they change, and the slave's rx registers against the ADC
  pattern frame by frame. Slots are 32 and 16 bits; bclk is clk / 8 and
  clk / 12.

Results: 11, 7 and 10 checks, all passing, against the open-ip-portfolio
`claude/project-thread-10n363` RTL.
