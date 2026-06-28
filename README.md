# 36Ke — 融资关联公司拉取

基于 Python + Conda，从 36氪 PitchHub（及可选亿欧数据）拉取最新融资公司，解析股东与注册地址，筛选华南地区（广东、广西、福建、海南）关联公司，**SQLite 缓存公司详情（30 天）**，导出 Excel 并通过 **lark-cli** 发送给本人。

详细设计见 [docs/TECH_DESIGN.md](docs/TECH_DESIGN.md)。

## 处理流程

1. **拉取融资公司** — 36kr `project/financing/list`；可选亿欧 Playwright 首页
2. **解析公司详情（带缓存）** — 先查 SQLite，未命中或超过 30 天才请求 36kr API/HTML
3. **华南判定** — cpca 解析注册地址，匹配广东 / 广西 / 福建 / 海南
4. **股东过滤** — 剔除名称含「咨询 / 投资 / 管理 / 基金 / 股权」的股东
5. **华南判定（股东）** — 搜索股东公司并查注册地（同样走缓存）
6. **导出 Excel + 飞书 CLI 发送** — 融资列表（表1）+ 华南关联（表2）

## 环境准备

```bash
conda env create -f environment.yml
conda activate kr36
pip install -r requirements.txt

# 亿欧数据源（可选）
pip install playwright && playwright install chromium

# 飞书 CLI（可选，用于推送 Excel）
python main.py setup-feishu          # 自动安装 lark-cli + 浏览器授权（只需一次）
# 或双击 scripts/setup_feishu.bat（Windows）/ scripts/setup_feishu.sh（Mac/Linux）
```

## 使用

```bash
# 拉取最近 7 天（36kr，默认 30 天缓存）
python main.py --days 7

# 拉 1 页，指定数据库
python main.py --pages 1 --db data/kr36.db --cache-ttl-days 30

# 亿欧数据源（Playwright 首页）
python main.py --source iyiou --no-push-feishu

# 合并 36kr + 亿欧
python main.py --source all --days 3

# 不推送飞书
python main.py --pages 3 --no-push-feishu

# 每日定时（约 9:00 ±15 分钟，时间按日期随机）
python main.py schedule --source all --days 3
python main.py schedule --dry-run          # 查看下次执行时间

# 安装为系统定时任务
# macOS:  bash scripts/install_daily_schedule.sh
# Windows: scripts\install_daily_schedule.bat
```

## Windows 完整版（用户无需 Python）

**最终用户**：解压 `36Ke-全功能版-win64.zip`，运行「配置环境.bat」，再「立即执行.bat」或「每日定时任务.bat」。

**构建发布包**（需 Windows + Python 3.11，仅构建一次）：

```bat
packaging\build_full.bat
```

输出 `dist\36Ke-全功能版-win64.zip`（内置 Chromium + Node.js + lark-cli）。解压后使用 **配置环境.bat** → **立即执行.bat** / **每日定时任务.bat**。

详见 [packaging/README.md](packaging/README.md)。

## Excel 格式

**表1 融资公司列表**：企业简称、企业全称、简介、融资轮次、融资时间、融资金额、投资方、行业、注册地址、省份、国家

**表2 华南关联公司**：

| 融资公司 | 融资日期 | 融资金额 | 融资轮次 | 华南关联公司 |
|---------|---------|---------|---------|------------|

## 项目结构

```
36Ke/
├── main.py
├── docs/TECH_DESIGN.md    # 技术方案（服务设计 + 数据表）
└── kr36/
    ├── pipeline.py          # 主流程编排
    ├── services/            # CachedProjectService（30天缓存）
    ├── db/                  # SQLite schema + repository
    ├── project.py           # 36kr 公司详情解析
    ├── financing.py         # 36kr 融资列表
    ├── iyiou/               # 亿欧 Playwright 数据源
    ├── export.py / feishu.py
    └── region.py / filters.py
```

## 说明

- 公司详情缓存默认 **30 天**，存储于 `data/kr36.db`
- 第二次运行同批公司时会显著减少 API 请求（CLI 会输出缓存命中统计）
- 飞书需先 `python main.py setup-feishu`（或 `lark-cli auth login`）
