# APB router cross-repository prototype check

此為TV/STB/IPCAM平台的隔離原型測試，不是新增catalog VIP。

```sh
python3 ipcheck/platform/run.py --ip-dir ../open-ip-portfolio --evidence-dir reports/platform
```

需求：Linux、Python3、iverilog/vvp、yosys。timeout、非零check數、負向decode／overlap案例與mutant偵測均由runner驗查；原始證據輸出到指定目錄。對應IP分支 `codex/platform-bus-host-20261101`，需包含 `rtl/platform/apb_window_router.sv`。

範圍及未驗項見 `docs/design/platform_verification_contract.md`。沒有改動既有UVM generator、zip或test-suite生成來源。
