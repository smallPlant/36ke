from __future__ import annotations

from pathlib import Path

import pandas as pd

from kr36.models import FinancingListRow, RelatedCompanyRow


def save_excel(rows: list[RelatedCompanyRow], output_path: Path) -> Path:
    """按需求文档导出华南关联 Excel（表2）。"""
    output_path.parent.mkdir(parents=True, exist_ok=True)

    if not rows:
        df = pd.DataFrame(columns=["融资公司", "融资日期", "融资金额", "融资轮次", "华南关联公司"])
    else:
        grouped: dict[str, list[RelatedCompanyRow]] = {}
        for row in rows:
            grouped.setdefault(row.financing_company, []).append(row)

        flat_rows: list[dict[str, str]] = []
        for _, group in grouped.items():
            for index, row in enumerate(group):
                if index == 0:
                    flat_rows.append(
                        {
                            "融资公司": row.financing_company,
                            "融资日期": row.financing_date,
                            "融资金额": row.financing_amount,
                            "融资轮次": row.financing_round,
                            "华南关联公司": row.related_company,
                        }
                    )
                else:
                    flat_rows.append(
                        {
                            "融资公司": "",
                            "融资日期": "",
                            "融资金额": "",
                            "融资轮次": "",
                            "华南关联公司": row.related_company,
                        }
                    )
        df = pd.DataFrame(flat_rows)

    df.to_excel(output_path, index=False, engine="openpyxl")
    return output_path


def save_financing_excel(rows: list[FinancingListRow], output_path: Path) -> Path:
    """按需求文档 PDF 2.4 导出融资公司列表 Excel（表1）。"""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    columns = [
        "数据来源",
        "企业简称",
        "企业全称",
        "简介",
        "融资轮次",
        "融资时间",
        "融资金额",
        "投资方",
        "行业",
        "注册地址",
        "省份",
        "国家",
    ]
    if not rows:
        df = pd.DataFrame(columns=columns)
    else:
        df = pd.DataFrame([row.to_dict() for row in rows])
    df.to_excel(output_path, index=False, engine="openpyxl")
    return output_path
