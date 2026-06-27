#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
echo "=== 36Ke 飞书 CLI 安装 ==="
python main.py setup-feishu
