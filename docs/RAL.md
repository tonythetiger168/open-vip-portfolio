# UVM RAL（register model）

本文件記錄 135 個 VIP 的 UVM RAL（`uvm_reg`）掃描結果、目前已加入 register model 的 VIP、
測試方法與結果，以及下一批候選。

## 1. 掃描結果（2026-10-24）

- 加入前 135 個 VIP **沒有任何** `uvm_reg` / `uvm_reg_block` / `uvm_reg_adapter` /
  `uvm_reg_predictor`；暫存器只存在於各 `tb/top_tb.sv` 的 DUT 模型（register bank 或
  word memory），UVM 環境無法以暫存器層級存取或檢查它們。
- 本次為 **APB-VIP、AHB-VIP、AXI-VIP** 加入 register model、adapter、predictor 與 RAL test，
  三者都在 Verilator 5.052 + uvm-core 2020.3.1 上通過（見第 3 節）。這也是 repo 中第一次真正
  執行 UVM test（之前 UVM 部分只做 pyslang elaboration）。

## 2. 架構

| 元件 | 檔案 | 說明 |
|---|---|---|
| Register model | `env/amba_reg_model.sv` | 依 `tb/top_tb.sv` 的 `amba_dut` 建模：欄位、access（RW）、reset 值、address map |
| Adapter | `vip/base/amba_reg_adapter.svh` | `uvm_reg_bus_op` ↔ 單筆 `amba_seq_item`；`protocol` / `bus_bytes` 由 env 設定 |
| Predictor | `amba_env`：`uvm_reg_predictor #(amba_seq_item)` | explicit prediction（`set_auto_predict(0)`），由 monitor 餵資料 |
| RAL test | `tests/amba_tests.sv`：`amba_ral_test` | 見下表 |
| Runner | `tools/run_uvm_tests.py` | Verilator 建置並執行，輸出 `UVM_PASS/FAIL` 與 `uvm_report.csv` |

各 VIP 的 address map：

| VIP | 匯流排 | Map | 內容 |
|---|---|---|---|
| APB-VIP | APB4，32-bit | `apb_map`，4 bytes | `REG0..REG59` @ 0x00–0xEC（zero wait）、`REG60..REG63` @ 0xF0–0xFC（2 wait states）、`ERR_PROBE` @ 0xEE000000（PSLVERR） |
| AHB-VIP | AHB5，64-bit | `ahb_map`，8 bytes | `REG0..REG7` @ 0x00–0x38、`MEM` 1016×64 @ 0x40–0x1FF8、`ERR_PROBE` @ 0xEE000000（HRESP=ERROR） |
| AXI-VIP | AXI4，64-bit | `axi_map`，8 bytes | `REG0..REG7` @ 0x00–0x38、`MEM` 504×64 @ 0x40–0xFF8、`ERR_PROBE` @ 0xEE000000（SLVERR） |

所有暫存器為單一 RW 欄位、reset 0（DUT 的 register bank / memory 開機為 0）。`ERR_PROBE`
設定 `NO_REG_TESTS`，不參與內建 sequence，只用來確認錯誤回應會以 `UVM_NOT_OK` 回到 RAL。
DUT 只解碼部分位址位元，更高位址會 alias，model 只映射一份。

`amba_ral_test` 內容：

1. `uvm_reg_hw_reset_seq`：每個暫存器讀到 reset 值
2. `uvm_reg_bit_bash_seq`：每個 RW 位元寫 0/1 並讀回
3. `uvm_mem_walk_seq`（AHB / AXI）：整個 `MEM` walking write/read
4. 每個暫存器 random write + `mirror(UVM_CHECK)` + read；AHB / AXI 另做 32 次 random `MEM` round trip
5. `ERR_PROBE` 的 write 與 read 都必須回 `UVM_NOT_OK`

通過條件（`tools/run_uvm_tests.py`）：模擬正常結束、`RAL_PASS checks=<n>`、沒有
`UVM_ERROR`/`UVM_FATAL`，而且 VIP 自身（protocol checker / SVA）沒有任何 `UVM_WARNING`；
合法的暫存器流量不應觸發任何協定檢查。

## 3. 結果

```
$ PATH=/opt/verilator-5.052/bin:$PATH python3 tools/run_uvm_tests.py
UVM_PASS AHB-VIP/amba_ral_test [checks=1586]
UVM_PASS APB-VIP/amba_ral_test [checks=2242]
UVM_PASS AXI-VIP/amba_ral_test [checks=1074]
```

每個 VIP 建置約 3–4 分鐘（uvm-core 每次重新編譯），模擬數秒。

### 3.1 RAL 第一次執行就抓到的問題（已修正）

| VIP | 問題 | 修正 |
|---|---|---|
| AHB-VIP | DUT 模型寫入用整個 byte address 當 index（`mem[ap_addr]`），讀取用 `HADDR[12:3]`，寫入的位址讀回別的 word；bit-bash 與 mem-walk 大量失敗 | 寫入改用 `mem[waddr]`（與讀取同 index）；功能測試原本以 XFAIL 記錄此缺陷，現改為一般 check |
| AHB-VIP | BUSY transfer 被當成有效傳輸 | address phase 只接受 NONSEQ/SEQ（`htrans[1]`） |
| APB-VIP | monitor 把連續傳輸合併成 burst，item 晚一個 clock 才送出；predictor 用晚到的 read 結果蓋掉下一筆 write 的 mirror，bit-bash 4032 個錯誤 | monitor 新增 `beat_ap`，每筆傳輸在完成的 clock edge 送出單筆 item，predictor 接 `beat_ap` |
| APB-VIP | L1/L2 SVA（`PSEL \|-> ##1 PENABLE`、`PSEL \|-> $stable(PADDR)`、PENABLE 只能一拍…）在每筆合法傳輸結束、換位址與 wait state 時誤報，一次 run 17,431 個 warning | 改成 APB 規格的 SETUP→ACCESS、ACCESS 期間穩定 |
| AXI-VIP | `WVALID && WLAST \|-> $past(WVALID)` 與 `AWLEN == $countones(WSTRB)` 在每筆單 beat write 誤報（各 2,072 次）；`$rose(AWVALID) \|-> AWVALID throughout AWREADY[->1]` 在 Verilator 上也每筆都失敗（寫法本身應成立，較可能是 Verilator 對 `throughout` + goto 的支援問題） | 改為以 beat counter 檢查 WLAST 落在第 AWLEN+1 beat；AWVALID 改為等價的 `(AWVALID && !AWREADY) \|=> AWVALID` |
| AMBA 三個 VIP | `amba_txn.delay` 是無 constraint 的 `rand int`，driver 執行 `repeat (t.delay)`，random sequence 等於永遠跑不完（任何模擬器都一樣） | 加 `constraint c_delay { delay inside {[0:3]}; }` |
| APB / AXI | tests 內有重複的 class 定義（`amba_apb_test`、`amba_axi_test` 各兩個），任何模擬器都無法編譯 | 第二個分別改名為 `amba_apb_err_test`、`amba_axi_burst_test` |

### 3.2 RAL test 的偵錯能力（DUT mutation）

對 DUT 模型手動注入 6 個暫存器層級錯誤，`amba_ral_test` 必須失敗：

| Mutant | VIP | 注入的錯誤 | RAL test 結果 |
|---|---|---|---|
| m1 | APB | PSLVERR 永遠為 0 | FAIL：`ERR_PROBE write did not return UVM_NOT_OK` |
| m2 | APB | 寫入時 bit 20 卡 1 | FAIL：bit_bash 264 個錯誤 |
| m3 | APB | `REG17` reset 值 0x100 | FAIL：hw_reset `REG17` 讀值不符 |
| m4 | AHB | 寫入用 byte address 當 index（修正前的模型） | FAIL：bit_bash / mem_walk 1958 個錯誤 |
| m5 | AXI | 讀取位址少一個 bit（上半部 alias 到下半部） | FAIL：mem_walk 272 個錯誤 |
| m6 | AXI | BRESP 永遠 OKAY（錯誤區不回 SLVERR） | FAIL：`ERR_PROBE write did not return UVM_NOT_OK` |

6/6 被偵測。

## 4. 已知限制

- Verilator 的 constraint solver（z3）無法處理 sequence 對巢狀 `rand` 物件的 inline constraint
  （`item.randomize() with { txn.len == ...; }` 加上 `data.size() == len`），所以既有的 random
  sequence 在 Verilator 上 randomize 失敗；RAL test 不使用 randomize，不受影響。其餘 UVM test
  仍需商用模擬器。
- Adapter 不支援 byte enable：三個 driver 都固定送出全部 byte lane（PSTRB/WSTRB 全 1）。
- 沒有 backdoor（`hdl_path`）：Verilator 不支援 `uvm_hdl_*` DPI，因此不跑需要 backdoor 的
  `uvm_reg_access_seq` / `uvm_mem_access_seq`；改以 frontdoor write + mirror 檢查。

## 5. 下一批候選

| 狀態 | VIP | 原因 |
|---|---|---|
| 可直接加 RAL | OCP-VIP、TileLink-VIP | driver 會把 read data 寫回 item，DUT 模型有 memory/register |
| 需先確認 driver 讀回 | I2C、I3C、SPMI、RFFE、SoundWire、AVSBus、MDIO-VIP、SWD、JTAG、CSE、DBI | DUT 模型有 register map，driver 為 bit-level，需確認 read data 回填 item 與 monitor 完成時機 |
| 需先重寫 agent | Avalon_MM-UVM、Wishbone-UVM、MDIO-UVM、PWM-UVM、WTB-UVM、SDIO-UVM、GPIO-UVM 等 29 個 | monitor 每個 clock 都送 item（`if (1'b1)`）、driver 只驅動一拍不看握手也不讀回資料、scoreboard 只比對 tag；RAL 無法建立在這種 agent 上 |
