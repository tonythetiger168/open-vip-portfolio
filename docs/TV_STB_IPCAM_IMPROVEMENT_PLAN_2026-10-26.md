# TV／STB／IPCAM 系統驗證改善計畫

日期：2026-10-26（Asia/Taipei）。狀態：設計立項，未宣稱 RTL、PPA 或量產驗收完成。
本計畫涵蓋 TV／STB／IPCAM 共用平台。實作前重讀最新 main、AGENTS.md／CLAUDE.md、相關 PR 與驗證報告；來源衝突以具體 RTL、較新報告及可重現結果判定。不得把 VIP、行為 PHY、命名或 coverage 百分比等同完整協定或產品成熟度。

## 目標
本repo負責verification IP，不代表相應controller/PHY已完成。先盤點132項與實際檔案/工具結果的對照、重複RTL及版本；所有結果區分elaboration/smoke/conformance/system。
## 需新增或擴充
AXI4：burst、4KB boundary、IDs/outstanding、backpressure、error/timeout、abort drain。
Video stream：SOF/EOL、valid lane/pixel packing、frame size、stall stability、frame-boundary config。
Frame manager：ownership/refcount/多consumer、reuse/free、secure/nonsecure隔離。
Camera：CSI lane/VC/DT/ECC/CRC錯誤、RAW packing、sensor不可回壓時的overflow策略、時間戳。
Codec：標準decoder/encoder golden、conformance corpus清單、合法/損毀bitstream、長時間及多context。
Display/network/storage：underflow、frame pacing、MAC/FCS/PAUSE、SD斷電、DMA錯誤。
Security/power：越權DMA、debug鎖、reset/clock-gate/retention、malformed descriptors；僅在適當授權環境測試。
## 驗收
不能用same-template driver和scoreboard構成自我驗證；保留seed/config/tool/version/非零檢查點/waiver，加入mutation驗證scoreboard確實能抓錯。交付 docs/design/media_system_verification.md。

## 共通交付與驗收
- 設計交付：block diagram、模組責任、介面／CSR、資料格式、clock/reset/power、吞吐／頻寬估算、錯誤／abort／recovery、安全邊界、依賴及驗證矩陣。
- 依序進行參考模型、RTL、獨立 scoreboard、CRV、SVA、coverage（保留 raw 數據與逐條 waiver）、適用控制形式驗證與 mutation、系統端到端測試。
- 效能以實測 cycles、配置與工具版本記錄；假設頻率與估算 PPA 必須標明，合成／STA／板級驗證未做不得宣稱完成。
- 每次更新 docs/PROGRESS_TV_STB_IPCAM.md：台北時間、commit、完成／待驗收／阻塞、測試命令與結果、下一步。無結果不得填 PASS。
- 設計工作使用 codex/ 分支與 draft PR；不自動合併，不新增付費服務。跨 repo 介面變更須列出所有 consumer 與相容性。
