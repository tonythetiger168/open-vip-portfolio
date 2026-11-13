# 平台 bus／host 獨立驗證契約

2026-11-01。此文件補充逐項 current→required→gap→update→acceptance→evidence 矩陣；不把VIP driver當成host RTL。未新增catalog VIP，未重包generated zip；現有 generated suite的「Sufficient／無已知缺口」只針對其固定model範圍，不能延伸到TV/STB/IPCAM。

## 已落地原型驗證

新增 `ipcheck/platform/apb_window_router_tb.sv`，對 open-ip-portfolio 的新 `rtl/platform/apb_window_router.sv` 執行獨立directed checks。bench不使用該repo既有APB_top，也不複製router decode作oracle，而用固定合法／非法addresses與預期select/read data觀察。

Linux重現（兩repo放在同目錄，需Icarus/Yosys/Python）：

```sh
python3 ipcheck/platform/run.py --ip-dir ../open-ip-portfolio --evidence-dir reports/platform
```

已實跑：Icarus 12.0、Yosys 0.52、WSL Python 3.14.4；16 checks通過，default error response刪除mutant exit1且被checker判敗，generic synthesis／`check -assert` exit0。原始logs與commands存 `reports/platform/`。synthesis用generic cells，無technology library／STA／PPA，不能把這個結果當physical。

涵蓋：reset select gating、兩window、setup/access、back-to-back、3個wait observations、PSLVERR completion、hole/misalignment／overlap fail closed、attribute/PSTRB/PPROT透傳。PSTRB只驗透傳，沒有驗下游storage byte-update。未做五項coverage closure、formal proof、CDC、multi-manager、clocked integration或host/DMA conformance。不能宣稱完整APB4 qualification。

## Host DUT 與 agent 角色矩陣（待新增）

|DUT|現有agent角色|host驗證需要的獨立peer／monitor|最低正／負案例|驗收證據|
|---|---|---|---|---|
|I2C host|目前主要manager driver→target|開漏target responder；獨立SCL/SDA解碼與仲裁競爭者|address/data ACK/NACK、stretch、repeated START、最後NACK、stuck pins、arbitration loss／9 pulse recovery|每bit取樣點、OE不drive1、payload比對、timeout與partial bytes|
|SPI host|manager driver→echo target|可指定MISO資料的responder＋四mode edge monitor|CPOL/CPHA、CS setup/hold/keep、underflow、abort各phase|MOSI/MISO逐bit、CS inactive時pins、nonzero bytes／checks|
|QSPI host|xSPI名稱不足證明QSPI boot host可驗|獨立flash command/address/dummy parser、IO OE contention monitor|03／profile-specific quad read、3/4-byte、dummy、QE policy、write禁用、掉電|phase/lane資料、dummy不誤取、兩端OE無爭用；XIP另列|
|MDIO host|station driver→地址5固定PHY|Clause22 responder帶可讀寫register file＋passive monitor|read/write、所有PHYAD/REGAD、TA missing/no-device、divider、abort|線上ST/OP/TA/data、不能只驗status mirror；target0x0C adapter設定明示|
|SDIO host|command driver→固定R1-style model|enumeration/function0/CCCR/R4/R5與data responder|CMD5/3/7、CMD52 RAW、CMD53 byte/block/count0、CRC7/16、busy/data timeout、DAT1 IRQ、1/4-bit|command/response/data分開scoreboard，錯CRC不發布buffer，真實Wi-Fi模組另驗|

反向測試不能僅把driver改名成responder。host DUT的clock/pin ownership、turnaround與no-device要在wire上量測；任何可配置peer行為（如stretch、late R5、CRC錯）需seed與config存檔。使用既有portfolio target只能做補充interop，不可讓driver/model同源預期結果自我證明。

## AXI／stream／DMA 待驗

|範圍|acceptance|負向／mutation|
|---|---|---|
|AXI memory fabric|來源ID不碰撞、AW/W配對、同ID順序、跨ID亂序、read/write同時、4KB split、decode errors、stall stability|錯route B/R、提早重用ID、漏B、AR跨界、停滯時改payload|
|AXI-Lite→APB|AW/W任一先到、單筆APB、backpressure、PSTRB、PSLVERR映射、reset/quiesce|丟W-first、重複write、提前B、APB wait時變PADDR|
|video byte profile|frame/plane descriptor、SOF/EOL、contiguousTKEEP、line bytes、stall、epoch|TKEEP忽略、SOF提前、EOL缺失、tail padding寫入|
|DMA＋frame manager|pattern→DMA write→buffer→DMA read→sink，獨立byte-address memory/ownership模型|越權descriptor、同slot雙writer、提早READY/reuse、abort未drain、completion覆寫|

每個run保留source SHA、contract version、clock/reset、seed、accepted bytes/frames、check count、cycles、raw log與waiver。distinguish elaboration／smoke／model-functional／DUT conformance／system；已有repo-reported coverage不重新算作本輪結果。deadline依DDR最大服務間隔與每consumer需求決定，未定時只記observed latency，不宣稱hard realtime。

## 下階段順序與依賴

先consumer review host contracts與SKU模式，再選一種host落地、增加responder/monitor及mutation，再掛DMA/system bench。全域host完成ETA未知。toolchain現有Verilator 5.032，低於repo coverage基準5.052；本輪未執行其coverage flow，不把工具存在當作closure。沒有商用模擬器、PHY或板級驗證。
