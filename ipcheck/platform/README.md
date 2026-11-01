# APB router cross-repository prototype check

此為TV/STB/IPCAM平台的隔離原型測試，不是新增catalog VIP。

```sh
python3 ipcheck/platform/run.py --ip-dir ../open-ip-portfolio --evidence-dir reports/platform
```

需求：Linux、Python3、iverilog/vvp、yosys。timeout、非零check數、負向decode／overlap案例與mutant偵測均由runner驗查；原始證據輸出到指定目錄。對應IP分支 `codex/platform-bus-host-20261101`，需包含 `rtl/platform/apb_window_router.sv`。

範圍及未驗項見 `docs/design/platform_verification_contract.md`。沒有改動既有UVM generator、zip或test-suite生成來源。

## Bounded RTL slice 與 coverage export policy

```sh
python3 ipcheck/platform/run_slice.py --ip-dir ../open-ip-portfolio --evidence-dir reports/platform_slice
python3 -m unittest discover -s ipcheck/platform/coverage -p test_check_export.py -v
```

第一個命令連接真實 router＋adapter＋兩個APB_top，三產品label各自跑固定seeds，明確不是完整SoC／UVM。第二個命令只測synthetic coverage政策資料，不產出產品coverage。規格與blocked dependencies見 `docs/design/platform_shared_uvm_plan.md`。

UVM source與strict原生前端／runtime runner在`ipcheck/platform/uvm/`；來源鎖在paired IP的`integration/platform/uvm_sources.json`。見`docs/design/platform_uvm_execution.md`。目前原生前端PASS，模擬執行BLOCKED；不能把兩者合稱UVM PASS。
