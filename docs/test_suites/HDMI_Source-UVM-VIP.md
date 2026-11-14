# HDMI source (TMDS, InfoFrames) 測試套件（HDMI_Source-UVM-VIP）

> 由 `tools/gen_test_suite_docs.py` 依 VIP 內容、`func_report.csv` 與 `mutation_report.csv` 自動產生，請勿手動修改。

## 1. 概要

| 項目 | 內容 |
|---|---|
| 類別 | Video |
| 類型 | UVM VIP |
| 功能測試 | 1 個檔案，12 個 check，全部通過 |
| Mutation | 25/25 個 mutant 被偵測（100%） |
| 判定 | **✅ Sufficient**（12 個 check，mutation score 100%） |

## 2. 可執行的功能測試

執行：`python3 tools/run_func_tests.py HDMI_Source-UVM-VIP`（Icarus Verilog 或 Verilator 5.054）。

### `tb/smoke_func_tb.sv`

結果：**PASS**（iverilog，12 checks）

模型合約與範圍（摘自測試檔頭）：

```text
Functional smoke testbench (HDMI source DUT model)
```

| # | Check | 類型 |
|---|---|---|
| 1 | hpd low and no output in reset | check |
| 2 | hpd high after reset | check |
| 3 | no capture before a VSYNC rising edge | check |
| 4 | frame report: 16 lines, no errors | check |
| 5 | every pixel decoded, one frame start, a line start per line | check |
| 6 | AVI InfoFrame: header, subpackets, ECC ok | check |
| 7 | header ECC bit flipped | check |
| 8 | subpacket 2 data bit flipped | check |
| 9 | short line and a line without guard band | check |
| 10 | DVI mode: no guard bands | check |
| 11 | guard-band-like characters in a video period are pixels (%0d) | check |
| 12 | line / frame start only with a pixel | check |

## 3. UVM 測試平台內容

UVM agent test（`hdmisrc_func_test`：directed + constrained-random 流量，scoreboard 以 DUT 模型的參考模型逐筆比對，並比對 driver 與 monitor 的 transaction）在 Verilator 上以 `python3 tools/run_uvm_tests.py HDMI_Source-UVM-VIP` 執行；agent 由 `tools/gen_uvm_agents.py` 依 `tools/uvm_agents/` 的協定 spec 產生。

| 項目 | 數量 | 名稱 |
|---|---|---|
| UVM tests | 2 | `hdmisrc_base_test`, `hdmisrc_func_test` |
| Sequences | 3 | `hdmisrc_base_sequence`, `hdmisrc_directed_sequence`, `hdmisrc_transaction` |
| SVA（assert / cover property） | 5 / 3 | - |
| Covergroups / coverpoints | 1 / 5 | |

## 4. 充分度判定與缺口

判定：**✅ Sufficient**（12 個 check，mutation score 100%）。

無已知缺口。

