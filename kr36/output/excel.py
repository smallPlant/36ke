"""Excel 导出：融资公司列表（表1）与华南关联公司（表2）。"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from kr36.core.models import FinancingListRow, RelatedCompanyRow


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
    """导出融资公司列表 Excel（表1）。"""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    columns = [
        "数据来源",
        "事件类型",
        "项目名称",
        "企业名称",
        "简介",
        "事件日期",
        "融资轮次",
        "融资金额",
        "投资方",
        "国标行业",
        "企查查行业门类",
        "企查查行业大类",
        "所属省份",
        "所属城市",
        "所属区县",
        "所属地区",
        "成立日期",
        "上市板块",
        "购买方",
        "出让方",
        "交易股权",
        "退出方式",
        "退出方",
        "资本回报倍数",
        "内部收益率",
        "退出股权",
    ]
    if not rows:
        df = pd.DataFrame(columns=columns)
    else:
        df = pd.DataFrame([row.to_dict() for row in rows])
    df.to_excel(output_path, index=False, engine="openpyxl")
    return output_path
