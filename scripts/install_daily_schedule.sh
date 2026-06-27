#!/usr/bin/env bash
# 安装 macOS 每日定时任务（launchd 守护，约 9:00 ±15 分钟执行）
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
LABEL="com.kr36.daily"
PLIST="$HOME/Library/LaunchAgents/${LABEL}.plist"

if ! command -v python3 >/dev/null 2>&1; then
  echo "未找到 python3"
  exit 1
fi

PYTHON="$(command -v python3)"
mkdir -p "$HOME/Library/LaunchAgents" "$ROOT/data"

cat > "$PLIST" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key>
  <string>${LABEL}</string>
  <key>ProgramArguments</key>
  <array>
    <string>${PYTHON}</string>
    <string>${ROOT}/main.py</string>
    <string>schedule</string>
    <string>--source</string>
    <string>all</string>
    <string>--days</string>
    <string>3</string>
  </array>
  <key>WorkingDirectory</key>
  <string>${ROOT}</string>
  <key>EnvironmentVariables</key>
  <dict>
    <key>PYTHONPATH</key>
    <string>${ROOT}</string>
  </dict>
  <key>StandardOutPath</key>
  <string>${ROOT}/data/schedule.stdout.log</string>
  <key>StandardErrorPath</key>
  <string>${ROOT}/data/schedule.stderr.log</string>
  <key>RunAtLoad</key>
  <true/>
  <key>KeepAlive</key>
  <true/>
</dict>
</plist>
EOF

launchctl bootout "gui/$(id -u)/${LABEL}" 2>/dev/null || true
launchctl bootstrap "gui/$(id -u)" "$PLIST"
launchctl enable "gui/$(id -u)/${LABEL}"

echo "已安装定时任务: ${LABEL}"
echo "  命令: python main.py schedule --source all --days 3"
echo "  日志: ${ROOT}/data/schedule.log"
echo ""
echo "查看下次执行时间:"
echo "  cd ${ROOT} && PYTHONPATH=. python main.py schedule --dry-run"
echo ""
echo "卸载:"
echo "  launchctl bootout gui/\$(id -u)/${LABEL} && rm ${PLIST}"
