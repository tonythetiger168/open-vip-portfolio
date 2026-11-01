# TV／STB／IPCAM 平台 bus／host 逐項矩陣

2026-11-01 15:00 Asia/Taipei。盤點表 v0.2 是候選能力，非凍結規格。線速、頻寬、clock、DMA channels、CPU及PHY選型均待定；ETA未知。

本repo main基線 `ba3cf117a2d18713df5c6562d3428afa896a8a94`。表格來源open-ip固定df9d0ed早於本輪main；本輪重新讀取九個RTL角色，不能把表格報告coverage當成本輪重跑。無AGENTS.md／CLAUDE.md（recursive tree檢查）；已讀CONTRIBUTING與既有總計畫。

|項目／表格列|current|未凍結 required|gap|本輪 update|acceptance（未註實跑均待執行）|evidence|
|---|---|---|---|---|---|---|
|AXI4；TV #1; STB #1; IPCAM #1|AXI-VIP存在不等於AXI4 multi-ID fabric conformance；本輪未解壓重跑|多manager AXI memory fabric|不是 interconnect/DMA；無 ID routing、QoS、firewall；DW 參數不能推定128-bit|新增host DUT responder/monitor驗證契約與負向案例，實作待完成|來源ID/response routing、4KB、並行read/write、stall、error、drain|vips/AXI-VIP.zip（僅tree存在，未執行） @ ba3cf11|
|AXI4_Lite；TV #2; STB #2; IPCAM #2|axi4_lite.py為manager agent→memory model，含AW/W skew/PROT；不是host bridge|AXI-Lite CSR crossbar及APB bridge|沒有 bridge/decoder；無 AxPROT；參數不能推定泛用寬度|新增host DUT responder/monitor驗證契約與負向案例，實作待完成|AW-first/W-first、B/R stall stability、strobe、PSLVERR轉換|tools/uvm_agents/axi4_lite.py @ ba3cf11|
|AXI_Stream；TV #3; STB #3; IPCAM #3|axi_stream.py為transmitter→packet receiver model；32-bit TKEEP/TSTRB、ID/DEST，無media SOF|source/sink adapter、stream fabric及DMA|無SOF/packing/有效lane/回收及frame ownership|新增host DUT responder/monitor驗證契約與負向案例，實作待完成|SOF/EOL、tail mask、stall、overflow drop、pattern→DMA→buffer→sink|tools/uvm_agents/axi_stream.py @ ba3cf11|
|APB；TV #4; STB #4; IPCAM #4|APB-VIP測memory model；本輪另加獨立router bench|peripheral decoder/router；AXI→APB另外設計|completer不是decoder；wrapper不是bridge|新增獨立16-check router bench與mutation runner|16 directed checks、default-error mutation偵測、generic synthesis；coverage/STA待驗|docs/test_suites/APB-VIP.md；新增ipcheck/platform/ @ ba3cf11|
|I2C；TV #12; STB #12; IPCAM #12|I2C-VIP主要驅動target；ipcheck有target cross-check，不代表I2C host已驗|sensor/tuner I2C host|無SCL生成及host command/recovery|新增host DUT responder/monitor驗證契約與負向案例，實作待完成|獨立target的NACK/stretch/repeated START/last NACK/stuck-bus/abort|docs/test_suites/I2C-VIP.md；ipcheck/README.md @ ba3cf11|
|SPI；TV #13; STB #13; IPCAM #13|SPI-VIP測echo target；與portfolio main的CS high MISO行為不一致|peripheral SPI host|無SCLK/CS生成；main MISO未依CS釋放，PR13修復未合併|新增host DUT responder/monitor驗證契約與負向案例，實作待完成|四mode edge/CS timing/underflow/abort；mode0先實作則CAP限定|docs/test_suites/SPI-VIP.md；ipcheck/README.md @ ba3cf11|
|QSPI；TV #8; STB #8; IPCAM #8|現有xSPI-VIP不能憑名稱視為QSPI boot host完整peer；本輪未解壓其package|boot-flash host；XIP另議|無opcode/address/dummy引擎、bootROM/XIP；main OE未以CS gating|新增host DUT responder/monitor驗證契約與負向案例，實作待完成|獨立flash model read/dummy/turnaround/address/掉電；XIP另驗|vips/xSPI-UVM-VIP.zip（僅tree存在，未執行） @ ba3cf11|
|MDIO；TV #11; STB #11; IPCAM #11|mdio.py是station driver→地址5的fixed PHY model；不是host DUT responder|MAC-side station-management host|無MDC生成、host read/write及TA檢查|新增host DUT responder/monitor驗證契約與負向案例，實作待完成|PHYAD/REGAD、TA Z0/no-device、read/write、divider/abort|tools/uvm_agents/mdio.py；docs/test_suites/MDIO-UVM-VIP.md @ ba3cf11|
|SDIO；TV #25; STB #25; IPCAM #22|sdio.py送command→fixed R1-style model，未驗host enumerate/R4/R5/data|Wi-Fi module SDIO host（選配）|無enumeration/function0/CCCR、SDCLK、host DMA；VIP fixed response不補足|新增host DUT responder/monitor驗證契約與負向案例，實作待完成|獨立card enumerate/CCCR/R4/R5/data/CRC/busy/IRQ/abort；真實模組另驗|tools/uvm_agents/sdio.py；docs/test_suites/SDIO-UVM-VIP.md @ ba3cf11|
|DMA / shared fabric；三表 #1–4 的系統缺口；inventory無獨立DMA列|尚無本輪獨立host-DMA端到端結果|AXI manager、2D stride、多plane、ring/cache/domain/ownership|sink/subordinate/VIP不能替代DMA；DDR service bound與吞吐待定|參照ORCA draft PR3，共用contract保持proposed；本輪不覆寫該工作|pattern→DMA→buffer→sink；4KB/IDs/errors/abort drain/secure隔離；RTL待執行|repo recursive tree；ORCA PR #3（提案、不是驗證證據）|

## 角色與報告解讀

所有 protocol wrapper 的 APB4 slave 是控制面，不表示資料面能host。docs/test_suites 的 Sufficient／100% mutation僅針對其model與mutant集合，不能提升為system/production驗證。既有來源claim未在本輪重跑，不抹除既有證據，也不把其算入本輪結果。

open-ip主線SPI MISO CS-high釋放缺口已在PR #13有修復提案，本輪不重複修改。AXI4/AXI-Lite的地址步進/索引仍固定32-bit shape，不因DW參數宣稱128-bit相容；AXI read資料mux與同址write並行的stall stability需獨立回歸。QSPI output-enable未依CS gating也列後續，不擅自宣稱修復。

README中的118與130矛盾已按main CSV 130 rows及130個vips/*.zip修成130；沒有新增VIP catalog entry或改寫generated suite docs／zip。新的router bench是ipcheck原型驗證，不是第131個VIP。

## 本機來源指紋

四份原始資料已讀取；表格以IP-inventory.json交叉核對。未更動OneDrive來源。

|檔案|SHA256|
|---|---|
|TV-IP-table.md|507245f9887a89de320a8e0305e1d1d9af3069a2117630d69b0cf690de802a64|
|STB-IP-table.md|bd7c72c16257a1064430dff58249a4152abb50402a9af0dd6e8d8986f633ab0c|
|IPCAM-IP-table.md|c1ae61dbb72cae11ea1ffcb4bc0ef1833fd7e228787712c2f06ae7f25e88fa18|
|IP-inventory.json|188e63e772c08f525c0604e23231afaedc3f826bf081af56b2ae128c9b856093|
