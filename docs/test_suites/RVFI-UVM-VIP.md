# RVFI (RISC-V Formal Interface, RV32I) 測試套件（RVFI-UVM-VIP）

> 由 `tools/gen_test_suite_docs.py` 依 VIP 內容、`func_report.csv` 與 `mutation_report.csv` 自動產生，請勿手動修改。

## 1. 概要

| 項目 | 內容 |
|---|---|
| 類別 | Debug |
| 類型 | UVM VIP |
| 功能測試 | 1 個檔案，59 個 check，全部通過 |
| Mutation | 23/29 個 mutant 被偵測（79%） |
| 判定 | **🟡 Partial**（mutation score 79%） |

## 2. 可執行的功能測試

執行：`python3 tools/run_func_tests.py RVFI-UVM-VIP`（Icarus Verilog 或 Verilator 5.052）。

### `tb/smoke_func_tb.sv`

結果：**PASS**（iverilog，59 checks）

模型合約與範圍（摘自測試檔頭）：

```text
Functional smoke testbench (RVFI DUT model)
```

| # | Check | 類型 |
|---|---|---|
| 1 | no fetch, data request or retirement in reset | check |
| 2 | program retired (%0d records) | check |
| 3 | lui | check |
| 4 | addi reads x1 | check |
| 5 | addi -1 | check |
| 6 | sw | check |
| 7 | lw | check |
| 8 | lb lane 1 | check |
| 9 | lbu lane 3 | check |
| 10 | lh upper half | check |
| 11 | sb lane 1 | check |
| 12 | lb sign-extends | check |
| 13 | lbu zero-extends | check |
| 14 | lh sign-extends | check |
| 15 | sh upper half | check |
| 16 | lw after sb / sh | check |
| 17 | sub | check |
| 18 | beq taken | check |
| 19 | bne not taken | check |
| 20 | slt -1 < 0 | check |
| 21 | sltu 0xFFFFFFFF < 0 false | check |
| 22 | srai | check |
| 23 | srli | check |
| 24 | slli | check |
| 25 | xori -1 | check |
| 26 | auipc | check |
| 27 | jal | check |
| 28 | jalr | check |
| 29 | blt taken | check |
| 30 | bgeu taken | check |
| 31 | add to x0: no rd | check |
| 32 | or | check |
| 33 | misaligned lw traps | check |
| 34 | handler: intr on its first instruction | check |
| 35 | handler returns | check |
| 36 | ecall traps | check |
| 37 | illegal instruction traps | check |
| 38 | jal to a misaligned target traps, no link | check |
| 39 | misaligned sw traps, no write | check |
| 40 | ebreak traps | check |
| 41 | handler counted six traps | check |
| 42 | memory unchanged by the trapped store | check |
| 43 | x1 unchanged by the trapped jal | check |
| 44 | slli with shamt bit 5 traps | check |
| 45 | fence: no-op | check |
| 46 | bge 0 >= -1 taken | check |
| 47 | sra by x1[4:0] | check |
| 48 | taken branch to a misaligned target traps | check |
| 49 | and | check |
| 50 | jalr to a misaligned target traps, no link | check |
| 51 | jalr with funct3 1 traps | check |
| 52 | branch with funct3 2 traps | check |
| 53 | load with funct3 3 traps | check |
| 54 | lw off a base register reports rs1 | check |
| 55 | jalr clears bit 0 of the target | check |
| 56 | jal x0, 0 loops | check |
| 57 | halt 0, mode M, ixl 32 on every record | check |
| 58 | never a fetch and a data request together | check |
| 59 | data memory after the stores | check |

## 3. UVM 測試平台內容

UVM agent test（`rvfi_func_test`：directed + constrained-random 流量，scoreboard 以 DUT 模型的參考模型逐筆比對，並比對 driver 與 monitor 的 transaction）在 Verilator 上以 `python3 tools/run_uvm_tests.py RVFI-UVM-VIP` 執行；agent 由 `tools/gen_uvm_agents.py` 依 `tools/uvm_agents/` 的協定 spec 產生。

| 項目 | 數量 | 名稱 |
|---|---|---|
| UVM tests | 2 | `rvfi_base_test`, `rvfi_func_test` |
| Sequences | 3 | `rvfi_base_sequence`, `rvfi_directed_sequence`, `rvfi_transaction` |
| SVA（assert / cover property） | 4 / 2 | - |
| Covergroups / coverpoints | 1 / 7 | |

## 4. 充分度判定與缺口

判定：**🟡 Partial**（mutation score 79%）。

未被偵測的 mutant（測試缺口或等價 mutant）：

- `dut_rvfi_model.sv:62 1'b0 inverted [l_rd <= '0; l_f3 <= '0; l_off <= '0; l_ld <= 1'b0;]`
- `dut_rvfi_model.sv:84 20 -> 21 [ii = {{20{i[31]}}, i[31:20]};]`
- `dut_rvfi_model.sv:123 1'b1 inverted [if (f3 > 3'd2) trap = 1'b1;]`
- `dut_rvfi_model.sv:127 0 -> 1 [for (int k = 0; k < 4; k++) if (!m[k]) wd[8*k +: 8] = 8'h00;]`
- `dut_rvfi_model.sv:152 < -> <= in condition [3'd3: r = (a < b) ? 32'd1 : 32'd0;]`
- `dut_rvfi_model.sv:195 24 -> 25 [3'd0: r = {{24{sh[7]}}, sh[7:0]};]`

