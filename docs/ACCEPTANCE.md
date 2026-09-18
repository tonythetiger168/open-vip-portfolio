# VIP Portfolio v1.7.3 — 使用者驗收指南

本指南說明如何驗收 **87 個獨立 SystemVerilog UVM VIP**（v1.7.3）。每個 VIP 內含完整
UVM testbench：driver / monitor / sequencer / scoreboard / functional coverage /
L1–L4 分層 SVA checker / functional DUT model / README，以及 `scripts/` 下的固定四件組
（`Makefile`、`coverage.mk`、`cov_check.py`、`coverage_regression.sh`，預設 COV_GOAL=100，
支援 VCS / Xcelium / Questa）。

驗收分三層：

| 層級 | 名稱 | 工具需求 | 通過標準 |
|------|------|----------|----------|
| L1 | 開源靜態閘（elaboration gate + DUT 冒煙測試） | iverilog 11、pyslang 11、uvm-core | 87/87 `ELAB_ERRORS=0` 且全部 `SMOKE_PASS` |
| L2 | 單一 VIP 動態回歸（coverage-driven） | VCS 或 Xcelium 或 Questa（擇一） | line/fsm/toggle/assert 四項 coverage 皆達 100% |
| L3 | 全 87 VIP 批次回歸 | 同 L2 | 87/87 `REGRESSION PASSED` |

---

## 0. 路徑約定

本指南以本環境的實際路徑為例；若 portfolio 以 git repo 形式發佈，請把
`PORTFOLIO_ROOT` 改成 repo 根目錄（repo 內應有 `vips/`、`tools/`、`smoke/`、`ci/` 四個目錄）。

```bash
export PORTFOLIO_ROOT=/mnt/agents/output/work_v174   # portfolio 根目錄
export TOOLS_DIR=/mnt/agents/output/tools            # 固化工具（elab_scan.py、uvm-core、setup 腳本）
ls "$PORTFOLIO_ROOT/vips" | wc -l                    # 應為 87
```

---

## 1. 環境準備

### 1.1 L1 所需：開源工具鏈（無需商用授權）

**(a) Icarus Verilog 11 + vvp（DUT 冒煙測試用）**

本環境已備妥離線還原腳本（內含 18 個快取 deb，斷網也可用）：

```bash
bash "$TOOLS_DIR/setup_eda_tools.sh"          # 已安裝則直接回報版本
bash "$TOOLS_DIR/setup_eda_tools.sh" --force  # 強制由本機 deb 重裝
iverilog -V | head -1                          # 預期：Icarus Verilog version 11.0 (stable)
```

在一般 Debian/Ubuntu 機器上亦可直接 `sudo apt-get install -y iverilog`。

> 已知限制：Icarus Verilog 不支援 UVM-1.2 class library，**只用於編譯/模擬各 VIP 的
> functional DUT model 冒煙測試**；UVM testbench 本身的編譯由 (b) 的 pyslang 靜態閘與
> L2/L3 的商用模擬器負責。

**(b) pyslang 11（elaboration gate 用）**

```bash
python3 -m pip install "pyslang>=11,<12"
python3 -c "import pyslang; print(pyslang.VersionInfo.getMajor())"   # 預期輸出：11
```

**(c) Accellera uvm-core（UVM 標準庫原始碼）**

```bash
git clone --depth 1 https://github.com/accellera-official/uvm-core.git "$TOOLS_DIR/uvm-core"
ls "$TOOLS_DIR/uvm-core/src/uvm_pkg.sv"     # 必須存在
```

`elab_scan.py` 預設使用 `$TOOLS_DIR/uvm-core/src`；若 uvm-core 放在別處，請設環境變數
指向 **src 目錄**（不是 repo 根目錄）：

```bash
export UVM_CORE=/path/to/uvm-core/src
```

### 1.2 L2/L3 所需：商用模擬器（三擇一）

| 模擬器 | 建議版本 | 授權環境變數 | 自我檢查指令 |
|--------|----------|--------------|--------------|
| Synopsys VCS | 2023.03 或更新 | `SNPSLMD_LICENSE_FILE` / `LM_LICENSE_FILE` | `vcs -ID` |
| Cadence Xcelium | 23.09 或更新 | `CDS_LIC_FILE` / `LM_LICENSE_FILE` | `xrun -version` |
| Siemens Questa | 2023.4 或更新 | `MGLS_LICENSE_FILE` / `LM_LICENSE_FILE` | `vsim -version` |

模擬器需內建或可取得 UVM-1.2（VCS 用 `-ntb_opts uvm-1.2`，三家的 flags 已內建於各
VIP 的 `scripts/Makefile` 與 `scripts/coverage.mk`）。確認 license daemon 可達：

```bash
lmstat -a -c "$LM_LICENSE_FILE" | head    # 應列出可用的 feature
```

### 1.3 環境自我檢查（一分鐘 smoke）

```bash
cd "$PORTFOLIO_ROOT"
python3 "$TOOLS_DIR/elab_scan.py" vips/AHB-VIP     # 預期：ELAB_ERRORS=0
iverilog -V | head -1                              # 預期：version 11.0
```

---

## 2. 驗收流程

### L1a — 開源靜態閘：elaboration gate（pyslang + uvm-core）

對單一 VIP 做完整 parse + elaborate（`--lint-only --single-unit --timescale=1ns/1ps`，
檔案順序依 common_pkg → defs → interface → pkg → 其餘 → top_tb 排列，include path 自動
涵蓋 uvm-core 與其 macros）：

```bash
cd "$PORTFOLIO_ROOT"
python3 "$TOOLS_DIR/elab_scan.py" vips/AHB-VIP
```

預期輸出（通過時只有一行）：

```
ELAB_ERRORS=0
```

有失敗時會列出至多 25 行帶檔案位置的 error，例如：

```
ELAB_ERRORS=2
  vip/ahb/ahb_driver.svh:42:17: error: ...
```

對全部 87 個 VIP 跑批次並產生報表：

```bash
cd "$PORTFOLIO_ROOT"
mkdir -p logs/l1
pass=0; fail=0
: > logs/l1/elab_summary.txt
for vip in vips/*/; do
  name=$(basename "$vip")
  if python3 "$TOOLS_DIR/elab_scan.py" "$vip" > "logs/l1/${name}.log" 2>&1 \
     && grep -q '^ELAB_ERRORS=0$' "logs/l1/${name}.log"; then
    echo "PASS  $name" | tee -a logs/l1/elab_summary.txt; pass=$((pass+1))
  else
    echo "FAIL  $name  （詳見 logs/l1/${name}.log）" | tee -a logs/l1/elab_summary.txt
    fail=$((fail+1))
  fi
done
echo "elab gate：PASS=$pass FAIL=$fail（總計 $((pass+fail))）"
[ "$fail" -eq 0 ]   # 87/87 全過才算 L1a 通過
```

### L1b — 開源靜態閘：iverilog DUT 冒煙測試

以 Icarus Verilog（`iverilog -g2012` + `vvp`）編譯並執行每個 VIP 內的 functional DUT
model 冒煙測試，確認 DUT 基本行為可用。harness 位於 `$PORTFOLIO_ROOT/smoke/`
（詳細介面以 `smoke/` 內 README 為準）：

```bash
cd "$PORTFOLIO_ROOT"

# 單一 VIP：
bash smoke/run_smoke.sh vips/AHB-VIP
# 預期結尾輸出：SMOKE_PASS AHB-VIP

# 不帶參數：全部 87 個 VIP 依序執行，並產生 smoke_report.csv：
bash smoke/run_smoke.sh
# 每個 VIP 一行結果：SMOKE_PASS / SMOKE_FAIL / SMOKE_SKIP <vip>
# 彙總表：smoke/smoke_report.csv
```

`SMOKE_SKIP` 表示該 VIP 無適合 iverilog 的 DUT 冒煙標的（不計入失敗）；`SMOKE_FAIL`
需比照 L1a 的日誌逐條排查。L1 通過條件：L1a 87/87 `ELAB_ERRORS=0`，且 L1b 無任何
`SMOKE_FAIL`。

### L2 — 單一 VIP 動態驗收（coverage-driven regression，需商用模擬器）

以 AHB-VIP 為例（任何 VIP 用法相同，只需更換目錄；各 VIP 預設的 TESTS 清單不同，
由各自的 `coverage_regression.sh` 內建）：

```bash
cd "$PORTFOLIO_ROOT/vips/AHB-VIP/scripts"
SIMULATOR=vcs bash coverage_regression.sh        # 或 SIMULATOR=xcelium / questa
```

腳本流程：① `make cov_build`（帶 coverage instrumentation 編譯）→ ② 以 xargs 平行跑
「test × seed」矩陣，每 run 各自傾印 coverage → ③ `make cov_merge` → `make cov_report`
→ `make cov_check`（呼叫 `cov_check.py` 解析合併報表，四項指標任一低於目標即 exit 1）。

開頭會印出設定摘要，預期輸出（節錄）：

```
==============================================================
 AHB-VIP — Coverage-Driven Regression
 Simulator : vcs
 Goal      : 100% (line / fsm / toggle / assert)
 Tests     : amba_base_test amba_axi_test amba_ahb_test amba_apb_test
 Seeds     : 12345 67890 13579 24680 99999
 Jobs      : 4
==============================================================
...
==============================================================
 Coverage Closure Check (goal per metric)
--------------------------------------------------------------
  line    : 100.00%  (goal 100%)  PASS
  fsm     : 100.00%  (goal 100%)  PASS
  toggle  : 100.00%  (goal 100%)  PASS
  assert  : 100.00%  (goal 100%)  PASS
==============================================================
[COV-CHECK] PASS: 100% closure on line/fsm/toggle/assert.
==============================================================
 REGRESSION PASSED — coverage goal 100% reached
==============================================================
```

可用環境變數（皆為 `coverage_regression.sh` 內建，可直接覆寫）：

| 變數 | 預設 | 說明 |
|------|------|------|
| `SIMULATOR` | `vcs` | `vcs` / `xcelium` / `questa` |
| `COV_GOAL` | `100` | 四項 coverage 指標的通過門檻（%） |
| `SEEDS` | 5 個固定 seed | 每個 test 各跑一遍的隨機種子清單 |
| `TESTS` | 依 VIP 而異 | UVM test 名稱清單（如 `amba_ahb_test`） |
| `JOBS` | `4` | xargs 平行 job 數 |

除錯時可縮小矩陣，例如只跑一個 test 一個 seed：

```bash
SIMULATOR=vcs TESTS="amba_ahb_test" SEEDS="12345" JOBS=1 bash coverage_regression.sh
```

### L3 — 全 87 VIP 批次回歸

```bash
cd "$PORTFOLIO_ROOT"
mkdir -p logs/l3
pass=0; fail=0; failed_vips=()
for vip in vips/*/; do
  name=$(basename "$vip")
  echo "=== [$name] 開始 $(date +%T) ==="
  if (cd "$vip/scripts" && SIMULATOR=vcs bash coverage_regression.sh) \
       > "logs/l3/${name}.log" 2>&1; then
    pass=$((pass+1)); echo "=== [$name] PASS ==="
  else
    fail=$((fail+1)); failed_vips+=("$name")
    echo "=== [$name] FAIL（詳見 logs/l3/${name}.log）==="
  fi
done
echo "----------------------------------------"
echo "L3 回歸結果：PASS=$pass FAIL=$fail（總計 $((pass+fail))）"
[ "$fail" -gt 0 ] && printf '失敗 VIP：%s\n' "${failed_vips[@]}"
[ "$fail" -eq 0 ] && echo "驗收通過：87/87 REGRESSION PASSED"
```

說明：
- 單一 VIP 內部的 test×seed 已由 `JOBS` 平行化，外層迴圈採序列執行以避免 license
  被瞬間吃光；若 license seat 充足，可改用 `xargs -P` 平行跑多個 VIP。
- 欲先快速摸底可將 `COV_GOAL=90` 傳入（`SIMULATOR=vcs COV_GOAL=90 bash ...`），但
  **正式驗收必須以預設 COV_GOAL=100 判定**。

---

## 3. 驗收通過標準（總表）

1. L1a：87/87 VIP `ELAB_ERRORS=0`。
2. L1b：`smoke/smoke_report.csv` 中無 `SMOKE_FAIL`。
3. L2：抽驗的 VIP（建議至少每類別一個，或直接全跑 L3）四項 coverage 指標
   （line / fsm / toggle / assert）皆達 100%，且 `cov_check.py` exit code 為 0。
4. L3：87/87 VIP 印出 `REGRESSION PASSED`，迴圈結尾 `FAIL=0`。

---

## 4. 常見問題 FAQ

### Q1. 模擬器報 license 錯誤（VCS / Xcelium / Questa）

排查順序：
1. 確認環境變數指向正確的 license server：
   - VCS：`echo $SNPSLMD_LICENSE_FILE`（或 `LM_LICENSE_FILE`）
   - Xcelium：`echo $CDS_LIC_FILE`
   - Questa：`echo $MGLS_LICENSE_FILE`
2. `lmstat -a -c <port>@<host>` 確認 daemon 存活、對應 feature（如 `vcs`、`xcelium`
   / `Xcelium_Single_Use`、`qhsimvl`）有可用 seat 且未過期。
3. 若批次回歸中途才失敗，通常是 seat 不足：降低 `JOBS`（單 VIP 內平行度），或讓 L3
   外層維持序列執行。
4. VCS 的 `Unable to checkout license` 有時是 `SNPSLMD_LICENSE_FILE` 與
   `LM_LICENSE_FILE` 指向不同 server 造成，請統一。

### Q2. coverage 未達 100%，怎麼排查？

依序檢查：
1. **看是哪一項指標不足**：`cov_check.py` 的表格會標出 FAIL 的 metric（line / fsm /
   toggle / assert）；若顯示 `NOT FOUND in report`，代表合併報表缺該項資料，通常是
   `make cov_merge`/`cov_report` 步驟失敗或 assert coverage 未開啟，先查
   `logs/l3/<vip>.log` 中 merge 階段的錯誤。
2. **開合併報表找最低分的模組/群組**：`cov_check.py` 採「所有 row 取最小值」的保守
   判定，任一 module 低於目標即 FAIL；用各家 coverage GUI（URG / IMC / vcover）打開
   `coverage/` 下的合併資料庫，定位未覆蓋的 bin / 分支 / FSM transition。
3. **加 seed 再試**：隨機約束未打到的 bin 常可靠加 seed 補齊：
   `SEEDS="12345 67890 13579 24680 99999 11111 22222 33333"`。
4. **確認 TESTS 涵蓋所有 sequence**：對照該 VIP README 的 sequence library 表格，
   若某 directed sequence 沒有被任何 test 觸發，需把它加入對應 test。
5. **確認 corner case 有被打到**：例如 AHB-VIP 的 functional DUT 在 `0xEE00_0000`
   區域會回 HRESP ERROR，若 ERROR 處理路徑的 coverage/SVA 未過，多半是沒有 test 觸及
   該區域。
6. **FSM / toggle 差一點點**：先確認 DUT model 與 checker 都被 instrumentation 涵蓋，
   再考慮是否是合法但難以到達的狀態；確定為不可達時，應以 exclusion 檔記錄並與
   維護者確認，**不要**直接調降 `COV_GOAL` 矇混過關。

### Q3. 如何對單一 VIP 除錯？

1. 靜態層先過：`python3 "$TOOLS_DIR/elab_scan.py" vips/<VIP>`，有 error 行會附
   檔案與行號，先修到 `ELAB_ERRORS=0`。
2. 縮小動態範圍：
   ```bash
   cd "$PORTFOLIO_ROOT/vips/<VIP>/scripts"
   SIMULATOR=vcs TESTS="<單一 test>" SEEDS="12345" JOBS=1 bash coverage_regression.sh
   ```
3. 手動重現單 run 並提高 UVM 訊息量：
   ```bash
   make compile elaborate SIMULATOR=vcs
   # VCS：
   ./simv +UVM_TESTNAME=<test> +ntb_random_seed=12345 +UVM_VERBOSITY=UVM_HIGH -l debug.log
   ```
4. 需要波形時，依各家工具加上 dump 選項（VCS：`-debug_access+all` 編譯 +
   `$fsdbDumpvars`；Xcelium：`-access +rwc` 已內建於 `xmelab` flags + `shm` probe；
   Questa：`vsim -wlf` / `log -r /*`）。
5. SVA 相關失敗：該 VIP 的 L1–L4 checker 在 `rtl/sva/`，對照 README 的 SVA 分層說明
   定位違反的 property。

### Q4. `elab_scan.py` 報 `uvm_pkg` 找不到 / 一堆 UVM macro 未定義？

`UVM_CORE` 沒設對。它必須指向 uvm-core 的 **src 目錄**（該目錄內要有 `uvm_pkg.sv`
與 `macros/`）：

```bash
export UVM_CORE=/path/to/uvm-core/src
ls "$UVM_CORE/uvm_pkg.sv" "$UVM_CORE/macros/uvm_macros.svh"   # 兩者都要存在
```

### Q5. 可以用 iverilog 跑整個 UVM testbench 嗎？

不行。Icarus Verilog 11 不支援 UVM-1.2 class library；它在本 portfolio 的角色僅限
L1b 的 functional DUT model 冒煙測試。UVM testbench 的編譯驗證由 L1a（pyslang
elaboration gate）把關，動態行為與 coverage 由 L2/L3 的商用模擬器把關。

### Q6. CI 如何接入？

參考 `ci/CI_README.md`：GitHub Actions 範例在 `ci/.github/workflows/vip_regression.yml`
（L1 開源閘，ubuntu runner 即可跑），Jenkins 範例在 `ci/Jenkinsfile`；商用模擬器的
L2/L3 在兩個範例中都以「self-hosted / 指定 label 的節點」註解區塊示範。
