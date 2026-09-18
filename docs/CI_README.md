# CI 接入說明 — VIP Portfolio v1.7.3

本目錄提供 VIP portfolio（87 個 UVM VIP）的 CI pipeline 範例與使用者驗收文件。
四個檔案的角色：

| 檔案 | 用途 | 接入位置 |
|------|------|----------|
| `ACCEPTANCE.md` | 使用者驗收指南：環境準備、L1→L2→L3 驗收流程、FAQ | 直接參考，不需搬移 |
| `.github/workflows/vip_regression.yml` | GitHub Actions：L1 開源閘（elab gate + iverilog smoke）+ 商用回歸註解範例 | 複製到 repo 的 `.github/workflows/` |
| `Jenkinsfile` | Jenkins declarative pipeline：同等流程 | 複製到 repo 根目錄 |
| `CI_README.md` | 本說明 | 直接參考，不需搬移 |

## 假設的 repo 版面

CI 範例假設 portfolio repo 根目錄長這樣（本環境對應
`/mnt/agents/output/work_v174/` 與 `/mnt/agents/output/tools/`）：

```
<repo>/
├── vips/                     # 87 個 VIP 目錄（唯讀，各含 scripts/ 四件組）
├── tools/
│   ├── elab_scan.py          # pyslang elaboration gate（L1a）
│   └── setup_eda_tools.sh    # 離線還原 iverilog/yosys（本環境用）
├── smoke/
│   └── run_smoke.sh          # iverilog DUT 冒煙測試 harness（L1b，選配）
└── ci/                       # 本目錄
```

## GitHub Actions 接入

```bash
mkdir -p .github/workflows
cp ci/.github/workflows/vip_regression.yml .github/workflows/
```

- ubuntu runner 上自動安裝 iverilog、`pip install "pyslang>=11,<12"`、clone
  Accellera uvm-core，接著對 `vips/*/` 逐個跑 `tools/elab_scan.py`，
  標準為 `ELAB_ERRORS=0`；smoke harness 存在時加跑 L1b。
- 報告（每 VIP 日誌 + 彙總）以 artifact 上傳，保留 30 天。
- 商用模擬器的 L2/L3 回歸在檔案尾端以註解示範：需改用
  `runs-on: [self-hosted, eda]` 的 runner（預裝 VCS/Xcelium/Questa 且可達
  license server）。

## Jenkins 接入

```bash
cp ci/Jenkinsfile <repo>/Jenkinsfile
```

- 任一 agent 即可跑 L1（stage 內自動安裝 iverilog / pyslang / uvm-core）。
- 報告以 `archiveArtifacts` 歸檔（失敗也保留）。
- 商用 L2/L3 stage 在檔案尾端註解中：需先建立掛 label `eda` 的節點。

## 注意事項

- 兩個 pipeline 都以「輸出字樣」判定成敗（elab gate 看 `ELAB_ERRORS=0`，smoke 看
  有無 `SMOKE_FAIL`），因為 `elab_scan.py` 一律 exit 0；請勿改成只看 exit code。
- 商用回歸（L2/L3）正式驗收門檻固定 `COV_GOAL=100`；調低僅供除錯摸底。
- 詳細指令、預期輸出與排查順序請見 `ACCEPTANCE.md`。
