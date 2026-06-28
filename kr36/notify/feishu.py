"""飞书消息通知：通过 lark-cli 发送文本摘要与 Excel 附件。"""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path
from typing import Any

from kr36.core.config import Settings
from kr36.core.models import RelatedCompanyRow


class FeishuNotifier:
    """通过 lark-cli 向本人发送飞书消息与 Excel 文件。"""

    def __init__(self, settings: Settings) -> None:
        """从 Settings 读取飞书用户 ID 与 lark-cli 路径。"""
        self.user_id = settings.feishu_user_id.strip()
        self.cli_bin = settings.lark_cli_bin.strip() or "lark-cli"
        self._cached_user_id: str | None = None

    @property
    def enabled(self) -> bool:
        """检查 lark-cli 是否可用（绝对路径或 PATH）。"""
        if Path(self.cli_bin).is_file():
            return True
        return bool(shutil.which(self.cli_bin))

    def _run_cli(
        self,
        args: list[str],
        *,
        cwd: Path | None = None,
    ) -> dict[str, Any]:
        """执行 lark-cli 命令并解析 JSON 输出。"""
        cmd = [self.cli_bin, *args]
        result = subprocess.run(
            cmd,
            cwd=cwd,
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode != 0:
            detail = (result.stderr or result.stdout or "").strip()
            raise RuntimeError(f"lark-cli 执行失败 ({' '.join(args[:3])}): {detail}")
        stdout = result.stdout.strip()
        if not stdout:
            return {}
        try:
            return json.loads(stdout)
        except json.JSONDecodeError:
            return {"raw": stdout}

    def resolve_user_id(self) -> str:
        """获取飞书 open_id：优先配置/缓存，否则调用 lark-cli 查询当前用户。"""
        if self.user_id:
            return self.user_id
        if self._cached_user_id:
            return self._cached_user_id

        data = self._run_cli(["contact", "+get-user", "--as", "user", "--json"])
        user = data.get("data", {}).get("user") or data.get("user") or {}
        open_id = user.get("open_id") or user.get("openId") or ""
        if not open_id:
            raise RuntimeError(
                "无法获取当前飞书用户 ID，请先执行 `lark-cli auth login`，"
                "或设置环境变量 FEISHU_USER_ID=ou_xxx"
            )
        self._cached_user_id = open_id
        return open_id

    def send_text(self, text: str, *, user_id: str | None = None) -> dict[str, Any]:
        """向指定用户发送纯文本消息。"""
        target = user_id or self.resolve_user_id()
        return self._run_cli(
            ["im", "+messages-send", "--user-id", target, "--text", text],
        )

    def send_file(self, file_path: Path, *, user_id: str | None = None) -> dict[str, Any]:
        """向指定用户发送文件附件。"""
        path = file_path.resolve()
        if not path.is_file():
            raise FileNotFoundError(f"文件不存在: {path}")

        target = user_id or self.resolve_user_id()
        # lark-cli 仅接受相对路径，需在文件所在目录执行
        return self._run_cli(
            ["im", "+messages-send", "--user-id", target, "--file", path.name],
            cwd=path.parent,
        )

    def notify_result(
        self,
        rows: list[RelatedCompanyRow],
        related_excel_path: str | Path,
        *,
        financing_excel_path: str | Path,
        financing_count: int,
    ) -> dict[str, Any] | None:
        """发送拉取结果摘要文本及两个 Excel 附件，成功后删除本地 Excel。"""
        if not self.enabled:
            raise RuntimeError(
                f"未找到 {self.cli_bin}。请运行: python main.py setup-feishu"
            )

        related_path = Path(related_excel_path)
        financing_path = Path(financing_excel_path)
        lines = [
            "【36氪融资关联公司拉取】完成",
            f"扫描融资公司: {financing_count} 家",
            f"华南关联记录: {len(rows)} 条",
            f"附件1（华南关联）: {related_path.name}",
            f"附件2（融资列表）: {financing_path.name}",
            "",
            "部分华南关联预览:",
        ]
        for row in rows[:10]:
            lines.append(
                f"- {row.financing_company} | {row.financing_round} | {row.related_company}"
            )
        if len(rows) > 10:
            lines.append(f"... 共 {len(rows)} 条，详见附件1")
        if not rows:
            lines.append("（暂无华南关联记录）")

        self.send_text("\n".join(lines))
        self.send_file(related_path)
        result = self.send_file(financing_path)
        self._cleanup_local_files(related_path, financing_path)
        return result

    @staticmethod
    def _cleanup_local_files(*paths: Path) -> None:
        """飞书发送成功后删除本地 Excel 文件。"""
        for path in paths:
            try:
                path.unlink(missing_ok=True)
            except OSError as exc:
                print(f"⚠️  清理本地 Excel 失败 {path}: {exc}")
