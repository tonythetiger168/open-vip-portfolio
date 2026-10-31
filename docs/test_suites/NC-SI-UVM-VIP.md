# NC-SI (DMTF DSP0222, RBT) 測試套件（NC-SI-UVM-VIP）

> 由 `tools/gen_test_suite_docs.py` 依 VIP 內容、`func_report.csv` 與 `mutation_report.csv` 自動產生，請勿手動修改。

## 1. 概要

| 項目 | 內容 |
|---|---|
| 類別 | Networking |
| 類型 | UVM VIP |
| 功能測試 | 1 個檔案，41 個 check，全部通過 |
| Mutation | 25/30 個 mutant 被偵測（83%） |
| 判定 | **✅ Sufficient**（41 個 check，mutation score 83%） |

## 2. 可執行的功能測試

執行：`python3 tools/run_func_tests.py NC-SI-UVM-VIP`（Icarus Verilog 或 Verilator 5.052）。

### `tb/smoke_func_tb.sv`

結果：**PASS**（iverilog，41 checks）

模型合約與範圍（摘自測試檔頭）：

```text
Functional smoke testbench (NCSI DUT model)
```

| # | Check | 類型 |
|---|---|---|
| 1 | CRS_DV low in reset | check |
| 2 | Get Version ID in the initial state: 1 / 1, MC ID echoed | check |
| 3 | response preamble and SFD (%0d dibits 01 before 11) | check |
| 4 | response %0d clocks after the command | check |
| 5 | Clear Initial State ch 0 | check |
| 6 | Get Version ID: 40 bytes, version F1 F1 F0 00, name, firmware, IDs | check |
| 7 | Get Version ID: every data byte | check |
| 8 | response DA and SA FF:FF:FF:FF:FF:FF | check |
| 9 | Get Link Status ch 0 disabled: 0x10 | check |
| 10 | Enable Channel ch 0 | check |
| 11 | Get Link Status ch 0 enabled: 0x11 | check |
| 12 | Enable Channel ch 1 in its initial state: 1 / 1 | check |
| 13 | Clear Initial State ch 1 | check |
| 14 | ch 1 cleared but disabled: 0x10 | check |
| 15 | Disable Channel ch 0 | check |
| 16 | ch 0 disabled again: 0x10 | check |
| 17 | ch 1 still enabled: 0x11 | check |
| 18 | Select Package to 0x1F | check |
| 19 | Deselect Package to 0x1F | check |
| 20 | Select Package to a channel: 1 / 2 | check |
| 21 | Enable Channel to 0x1F: 1 / 2 | check |
| 22 | unsupported command 0x50: 3 / 0x7FFF | check |
| 23 | unsupported command 0x0E to the package: 3 / 0x7FFF | check |
| 24 | Enable Channel with 4 payload bytes: 1 / 2 | check |
| 25 | Disable Channel with no payload: 1 / 2 | check |
| 26 | Reset Channel with 8 payload bytes: 1 / 2 | check |
| 27 | unpadded 66-byte command with a 28-byte payload: 1 / 2 | check |
| 28 | payload length past the frame: no response | check |
| 29 | zero checksum accepted | check |
| 30 | wrong checksum: no response | check |
| 31 | bad FCS: no response | check |
| 32 | header revision 2: no response | check |
| 33 | EtherType 0x0800: no response | check |
| 34 | package 1: no response | check |
| 35 | channel 2: no response | check |
| 36 | package 1 channel 0x1F: no response | check |
| 37 | a clean command after the drops (ch 0 enabled) | check |
| 38 | Reset Channel ch 0 | check |
| 39 | after Reset Channel: initialization required | check |
| 40 | Reset Channel left ch 0 disabled | check |
| 41 | ch 1 untouched by the reset of ch 0 | check |

## 3. UVM 測試平台內容

UVM agent test（`ncsi_func_test`：directed + constrained-random 流量，scoreboard 以 DUT 模型的參考模型逐筆比對，並比對 driver 與 monitor 的 transaction）在 Verilator 上以 `python3 tools/run_uvm_tests.py NC-SI-UVM-VIP` 執行；agent 由 `tools/gen_uvm_agents.py` 依 `tools/uvm_agents/` 的協定 spec 產生。

| 項目 | 數量 | 名稱 |
|---|---|---|
| UVM tests | 2 | `ncsi_base_test`, `ncsi_func_test` |
| Sequences | 3 | `ncsi_base_sequence`, `ncsi_directed_sequence`, `ncsi_transaction` |
| SVA（assert / cover property） | 3 / 2 | - |
| Covergroups / coverpoints | 1 / 5 | |

## 4. 充分度判定與缺口

判定：**✅ Sufficient**（41 個 check，mutation score 83%）。

未被偵測的 mutant（測試缺口或等價 mutant）：

- `dut_ncsi_model.sv:51 1'b0 inverted [nrb <= '0; sh <= '0; dib <= '0; sync <= 1'b0; tx_p <= 1'b0; ]`
- `dut_ncsi_model.sv:64 < -> <= in condition [if (nrb < 8'd128) rb[nrb[6:0]] <= {txd, sh[7:2]};]`
- `dut_ncsi_model.sv:79 128 -> 129 [for (int i = 0; i < 128; i++) if (i < n) c = crc32_byte(c, r]`
- `dut_ncsi_model.sv:117 7 -> 8 [for (int i = 0; i < 7; i++) f[i] = 8'h55;]`
- `dut_ncsi_model.sv:125 60 -> 61 [for (int i = 0; i < 60; i += 2) if (i < 20 + dl) s = s + {16]`

