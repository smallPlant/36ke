from __future__ import annotations

from pathlib import Path

import pandas as pd

from kr36.iyiou.models import InvestEvent


def save_invest_excel(rows: list[InvestEvent], output_path: Path) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        pd.DataFrame(
            columns=[
                "企业简称",
                "企业全称",
                "简介",
                "融资轮次",
                "融资时间",
                "融资金额",
                "投资方",
                "注册地址",
                "省份",
                "国家",
                "行业",
            ]
        ).to_excel(output_path, index=False)
    else:
        pd.DataFrame([row.to_row() for row in rows]).to_excel(output_path, index=False)
    return output_path
