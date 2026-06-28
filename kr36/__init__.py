"""36氪融资关联公司拉取工具包。

目录按功能划分：
  core/      — 配置、路径、数据模型
  pipeline/  — 主流程编排
  sources/   — 数据源（events 事件 / company 工商 / infra 基础设施）
  domain/    — 业务规则（华南判定、股东过滤）
  storage/   — SQLite 持久化
  output/    — Excel 导出
  notify/    — 飞书通知
  scheduler/ — 定时调度
  services/  — 缓存等业务服务
"""

__version__ = "0.2.0"
