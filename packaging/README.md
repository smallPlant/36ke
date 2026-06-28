# Windows 全功能版打包

## 给最终用户

1. 解压 `36Ke-全功能版-win64.zip`
2. **配置环境.bat** — 飞书授权 + 企查查登录
3. **立即执行.bat** — 立即拉取并推送飞书
4. **每日定时任务.bat** — 安装每天约 9:00 自动执行

无需安装 Python。内置 Chromium、Node.js、lark-cli。

---

## 给开发者：构建

```bat
packaging\build_full.bat
```

产物：`dist/36Ke-全功能版-win64.zip`（约 400MB）

---

## 产物脚本

| 脚本 | 说明 |
|------|------|
| 配置环境.bat | 飞书 CLI + 企查查 Cookie |
| 立即执行.bat | 全源拉取 + 飞书推送 |
| 每日定时任务.bat | Windows 计划任务 |

内部辅助：`_env.bat`、`_schedule-runner.bat`（勿删）
