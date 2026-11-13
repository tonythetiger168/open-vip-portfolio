# 平台 APB UVM 執行資產與相容性跟進

日期：2026-11-01，15:41 Asia/Taipei。這是 shared UVM 計畫的有界執行起點，不是完整 TV／STB／IPCAM SoC、RAL、DMA 或六類 coverage closure。實際建置／執行狀態以本輪 `reports/platform_uvm*` 結果為準；沒有成功 marker、完整 UVM summary 與非零 wire traffic 不記模擬 PASS。

|本輪 gate|實際結果|
|---|---|
|Windows 原生 pyslang12.1.0 嚴格語法／語義前端|FRONTEND_PASS，嚴格 error=0；非零diagnostics與warning保留，沒有抑制錯誤|
|UVM simulation／208tx／wire replay／negative checker|BLOCKED，未執行；不得當作UVM runtime PASS|
|Verilator5.032＋兩個官方UVM版本|皆在第三方type_id解析處BLOCKED_BUILD；原始失敗log保留|
|隔離Verilator5.052工具建置|default make已停止；後續opt-only啟動遇WSL/Service/0x8007274c，尚未完成|
|coverage政策／UVM日誌分類器|19＋7 synthetic tests通過；不是coverage／UVM simulation證據|

## 已落地資產

`ipcheck/platform/uvm/` 包含 interface、UVM sequence item、active APB driver、passive monitor、analysis port／imp、獨立 memory scoreboard、sequencer/env/test 與 RTL test top。test top 接現有 `platform_apb_slice` 的真實 RTL，沒有把 memory target 換成 TLM/stub；測試 driver 仍不是 CPU RTL。

scoreboard只依 monitor 在 APB `PSEL && PENABLE && PREADY` 時採得的 wire completion 更新，並依 reset event 清空 reference memory；不使用 driver response 或 DUT memory array 當 golden。獨立 address/alias／partial-write error policy 與資料比對分開查核。driver在負緣改值、monitor在正緣採樣，避免同緣刺激競爭。

sequence：8筆定向＋200筆有界生成，每 seed 預期208 transactions；固定seeds 1／7／42。合法與預期錯誤case混合，含fast／slow alias、hole、misalignment、reserved range與partial write。這是**真實 UVM sequence 中的程序式有界生成**，未宣稱已驗SystemVerilog declarative constraint solver、完整virtual sequence或functional covergroup。

runner設計為seed7重播比對208筆accepted-wire-event trace，不把Verilator walltime／效能尾訊息當作重播資料。`+CORRUPT_MONITOR_ONCE`翻轉第一筆read observation，要求passive scoreboard確實報錯；它是checker負向測試，不是DUT RTL mutation。這些是尚待實際UVM執行的驗收條件；先前native campaign的partial-write DUT mutant證據分開保留。

## 官方來源與工具

UVM只接受未修改的官方公開checkout，HEAD須為固定commit：

|官方版本|commit|本輪初始Verilator5.032結果|
|---|---|---|
|[2020.3.1](https://github.com/accellera-official/uvm-core/releases/tag/2020.3.1)|78c06547a2a0a29b3dc9dcafae62b75b2ff61544|BLOCKED_BUILD：uvm_phase_hopper::type_id解析失敗|
|[2020-2.0](https://github.com/accellera-official/uvm-core/releases/tag/2020-2.0)|39dfb0077ae25d69d1e66bf7d6a56861e244150f|BLOCKED_BUILD：同類type_id解析失敗|

沒有修改第三方UVM原始碼繞過錯誤。為核對repo基準工具，在工作目錄準備官方Verilator v5.052（commit ea338be98e1e838d3518809ce8899f85a009963c），未覆寫系統5.032。初次default make同時建debug/opt，已停止自己啟動的該build，下一步改用`make -C src -j2 opt`；此opt-only啟動遇到WSL/Service/0x8007274c，工具建置未完成。沒有重啟共用WSL或停止其他工作。

Windows原生前端使用公開PyPI wheel，固定pyslang12.1.0／nanobind-backend1.0.0，僅安裝在work目錄。重現依賴見`requirements-elab.txt`。嚴格前端初次抓到自定義`check`與UVM父類虛方法簽章衝突，已改名`check_expected`後error=0，before/after原始診斷均保存。這證明靜態class/RTL語義可檢查，不證明factory runtime連線／sequence已執行。

```sh
python ipcheck/platform/uvm/elaborate_uvm.py --ip-dir ../open-ip-portfolio --uvm-core /path/to/pinned/uvm-core --pyslang-root /path/to/pyslang --evidence-dir reports/platform_uvm_frontend
```

`integration/platform/uvm_sources.json`鎖定10份RTL／UVM程式blob與SHA256；兩個runner都在前端／模擬建置前核對，來源改變需更新baseline與重驗。

執行方式（Linux；完整IP checkout，或明確的upstream APB source override）：

```sh
python3 ipcheck/platform/uvm/run_uvm_slice.py \
  --ip-dir ../open-ip-portfolio \
  --uvm-core /path/to/pinned/uvm-core \
  --verilator /path/to/isolated/verilator \
  --evidence-dir reports/platform_uvm_5052
```

runner記錄source／verification SHA256、UVM commit、實際tool version、filelist／flags、build command與raw logs；不同runtime／tool／source set不可merge。compile使用`--timing --assert`與`UVM_NO_DPI`；沒有coverage instrumentation DB，因此不能由此報六類百分比。`classify_run`要求208筆非零traffic、正確seed、完整零UVM_ERROR/UVM_FATAL summary、無錯誤event與成功exit；7項synthetic分類器測試已驗證缺summary、錯seed、無traffic、非零exit與隱藏錯誤不會誤PASS。

## Coverage gate 修正

`coverage/check_export.py`新加：run必須明確passed、沒有timeout、pending transactions=0、完整零UVM error/fatal、illegal-bin hits=0；baseline point IDs不可重複；toggle每個bit都需rise/fall兩向raw points；所有functional raw bins都需合法且traceable，不能用waiver隱藏非法bin。

19個policy self-tests通過。已用相同新測試回跑前一版commit 7fb318a：舊版exit1、修正版exit0，保留`coverage_gate_before.log`／`coverage_gate_after.log`。這是合成政策資料的before/after regression，不是產品coverage證據，不能把測試中的all-hit input當成100%。

完整SoC top/filelist、RAL register map／frontdoor、AXI responder、stream/host peers、DMA／ownership／QoS／active-reset/drain、完整CRV constraints、六類工具DB exporter仍需後續完成。功能bins與SVA非vacuous witness尚無完整實測；產品 closure仍OPEN/BLOCKED，ETA未知。
