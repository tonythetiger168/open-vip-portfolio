// =============================================================================
// VIP Portfolio v1.7.3 — CI 回歸（Jenkins declarative pipeline 範例）
//
// 流程與 GitHub Actions 範例（ci/.github/workflows/vip_regression.yml）相同：
//   Stage 1 環境準備：iverilog + pyslang 11 + Accellera uvm-core
//   Stage 2 L1a elaboration gate：對全部 87 個 VIP 跑 tools/elab_scan.py
//   Stage 3 L1b iverilog DUT 冒煙測試：smoke/run_smoke.sh 存在時才執行
//   Stage 4 歸檔報告 artifact（失敗也保留日誌）
//   檔案尾端以註解示範 Stage 5：在具商用模擬器 license 的節點跑 L2/L3。
//
// 假設 repo 版面：
//   <repo>/vips/<協定>-VIP/            ← 87 個 VIP 目錄
//   <repo>/tools/elab_scan.py          ← elaboration gate 腳本
//   <repo>/smoke/run_smoke.sh          ← iverilog DUT 冒煙測試 harness（選配）
// =============================================================================

pipeline {
    agent any

    options {
        timestamps()                 // 每行輸出加時間戳，便於比對 license 等待時間
        disableConcurrentBuilds()    // 避免並行 build 搶 license / 互踩 reports 目錄
        buildDiscarder(logRotator(numToKeepStr: '20'))
    }

    environment {
        // uvm-core 的 src 目錄（elab_scan.py 透過 UVM_CORE 環境變數取得）
        UVM_CORE = "${WORKSPACE}/tools/uvm-core/src"
    }

    stages {
        stage('環境準備') {
            steps {
                sh '''
                    set -e
                    # (a) Icarus Verilog（L1b DUT 冒煙測試用）
                    if ! command -v iverilog >/dev/null; then
                        sudo apt-get update && sudo apt-get install -y iverilog
                    fi
                    iverilog -V | head -1

                    # (b) pyslang 11（slang SystemVerilog 前端之 Python 綁定）
                    python3 -m pip install --user "pyslang>=11,<12"
                    python3 -c "import pyslang; print('pyslang major =', pyslang.VersionInfo.getMajor())"

                    # (c) Accellera uvm-core（UVM-1.2 標準庫原始碼）
                    if [ ! -f "$UVM_CORE/uvm_pkg.sv" ]; then
                        rm -rf "${WORKSPACE}/tools/uvm-core"
                        git clone --depth 1 \
                            https://github.com/accellera-official/uvm-core.git \
                            "${WORKSPACE}/tools/uvm-core"
                    fi
                    ls "$UVM_CORE/uvm_pkg.sv" "$UVM_CORE/macros/uvm_macros.svh"
                '''
            }
        }

        stage('L1a：elaboration gate（87 VIP）') {
            steps {
                sh '''
                    set -u
                    mkdir -p reports/elab
                    pass=0; fail=0
                    : > reports/elab/elab_summary.txt
                    for vip in vips/*/; do
                        name=$(basename "$vip")
                        log="reports/elab/${name}.log"
                        # elab_scan.py 一律 exit 0，必須以輸出的 ELAB_ERRORS 判定
                        if python3 tools/elab_scan.py "$vip" > "$log" 2>&1 \
                           && grep -q '^ELAB_ERRORS=0$' "$log"; then
                            echo "PASS  $name" | tee -a reports/elab/elab_summary.txt
                            pass=$((pass+1))
                        else
                            echo "FAIL  $name" | tee -a reports/elab/elab_summary.txt
                            fail=$((fail+1))
                        fi
                    done
                    echo "elab gate 結果：PASS=$pass FAIL=$fail（總計 $((pass+fail))）" \
                        | tee -a reports/elab/elab_summary.txt
                    [ "$fail" -eq 0 ]   # 任何一個 VIP 失敗即讓整個 pipeline 失敗
                '''
            }
        }

        stage('L1b：iverilog DUT 冒煙測試') {
            steps {
                sh '''
                    set -u
                    mkdir -p reports/smoke
                    if [ -f smoke/run_smoke.sh ]; then
                        # 不帶參數＝跑全部 87 個 VIP，輸出 SMOKE_PASS/SMOKE_FAIL/
                        # SMOKE_SKIP 並產生 smoke/smoke_report.csv；
                        # 詳細介面以 smoke/ 內 README 為準
                        bash smoke/run_smoke.sh | tee reports/smoke/smoke.log
                        cp -f smoke/smoke_report.csv reports/smoke/ 2>/dev/null || true
                        if grep -q 'SMOKE_FAIL' reports/smoke/smoke.log; then
                            echo "DUT 冒煙測試有 SMOKE_FAIL，詳見 reports/smoke/smoke.log"
                            exit 1
                        fi
                    else
                        echo "smoke/run_smoke.sh 尚未納入 repo，略過 L1b（參見 ci/ACCEPTANCE.md）"
                    fi
                '''
            }
        }
    }

    post {
        always {
            // 失敗也保留全部日誌供排查
            archiveArtifacts artifacts: 'reports/**', allowEmptyArchive: true
        }
        success {
            echo 'L1 開源閘全數通過（87/87 ELAB_ERRORS=0，無 SMOKE_FAIL）'
        }
        failure {
            echo 'L1 開源閘失敗：請查看 reports/elab/elab_summary.txt 與各 VIP 日誌'
        }
    }
}

// =============================================================================
// Stage 5 範例（註解）：L2/L3 商用模擬器 coverage-driven 回歸
//
// 請在 Jenkins 中建立掛有 label「eda」的節點（預裝 VCS/Xcelium/Questa 並可達
// license server），再把下列 stage 加入 stages{} 區塊；建議只在夜間排程或
// 手動觸發的 job 啟用，避免消耗 PR 檢查時間。
//
//        stage('L2/L3：coverage 回歸（商用模擬器）') {
//            agent { label 'eda' }
//            environment {
//                SIMULATOR = 'vcs'      // 或 xcelium / questa
//                COV_GOAL  = '100'      // 正式驗收門檻固定 100
//                JOBS      = '4'
//            }
//            steps {
//                sh '''
//                    set -u
//                    vcs -ID || true     # 確認模擬器安裝與 license
//                    lmstat -a -c "$LM_LICENSE_FILE" | head
//                    mkdir -p reports/l3
//                    pass=0; fail=0
//                    for vip in vips/*/; do
//                        name=$(basename "$vip")
//                        echo "=== [$name] 開始 $(date +%T) ==="
//                        if (cd "$vip/scripts" && bash coverage_regression.sh) \
//                             > "reports/l3/${name}.log" 2>&1; then
//                            pass=$((pass+1)); echo "=== [$name] PASS ==="
//                        else
//                            fail=$((fail+1)); echo "=== [$name] FAIL ==="
//                        fi
//                    done
//                    echo "L3 結果：PASS=$pass FAIL=$fail"
//                    [ "$fail" -eq 0 ]
//                '''
//            }
//            post {
//                always {
//                    archiveArtifacts artifacts: 'reports/l3/**',
//                                     allowEmptyArchive: true
//                }
//            }
//        }
// =============================================================================
