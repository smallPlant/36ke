# Windows 完整版打包（用户无需 Python）

## 给最终用户

1. 获取 `36Ke-完整版-win64.zip`
2. 解压到任意文件夹
3. 双击 **`启动-最近3天.bat`**

无需安装 Python、Conda、Playwright。

---

## 给开发者：构建发布包

**必须在 Windows 上构建**（PyInstaller 不能从 Mac 交叉编译 Windows exe）。

### 方式 A：本机一键打包

构建机需安装 [Python 3.11+](https://www.python.org/downloads/)（勾选 Add to PATH）。

```bat
packaging\build_full.bat
```

产物：

```
dist/
├── 36Ke/                    # 绿色目录
└── 36Ke-完整版-win64.zip    # 分发给用户的压缩包
```

### 方式 B：GitHub Actions（推荐无 Windows 构建机时）

1. 推送代码到 GitHub
2. Actions → **Build Windows Package** → Run workflow
3. 下载 Artifacts 中的 `36Ke-win64.zip`

或打 tag `v1.0.0` 推送后自动构建。

---

## 产物结构

```
36Ke/
├── 36Ke.exe
├── _internal/
├── browsers/              # Chromium ~150MB
├── 启动-最近3天.bat
├── 启动-最近7天.bat
├── 安装定时任务.bat
├── 配置飞书.bat
├── 使用说明.txt
└── data/                  # 首次运行后生成
```

体积约 **350~500 MB**。

---

## 技术说明

- PyInstaller `--onedir` 模式，入口 `main.py`
- `PLAYWRIGHT_BROWSERS_PATH` 指向 `./browsers`
- 数据目录相对 exe 路径（`kr36/paths.py`）
- 飞书推送未内置 Node.js，可选 `配置飞书.bat`
