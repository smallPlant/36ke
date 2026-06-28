"""亿欧投资事件数据模型。"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

from kr36.sources.events.iyiou.investors import format_iyiou_investors


@dataclass
class InvestEvent:
    """亿欧投资事件 API 单条记录。"""

    # 投资事件 ID
    invest_id: str
    # 企业简称
    brief_name: str
    # 企业全称
    full_name: str
    # 企业简介
    brief_intro: str
    # 融资轮次描述
    invest_round: str
    # 融资时间（YYYY-MM-DD）
    invest_time: str
    # 融资金额
    invest_amount: str
    # 投资方（已清洗为顿号分隔文本）
    investors: str
    # 注册地址
    reg_location: str
    # 省份
    province: str
    # 国家
    country: str
    # 行业名称
    industry: str
    # 亿欧企业 com_id
    com_id: str

    @classmethod
    def from_api_record(cls, record: dict[str, Any]) -> InvestEvent:
        """从亿欧 API 原始记录构建 InvestEvent。"""
        return cls(
            invest_id=str(record.get("investId") or ""),
            brief_name=str(record.get("briefName") or ""),
            full_name=str(record.get("fullName") or ""),
            brief_intro=str(record.get("briefIntro") or ""),
            invest_round=str(record.get("investRoundDesc") or ""),
            invest_time=str(record.get("investTime") or ""),
            invest_amount=str(record.get("investAmount") or ""),
            investors=format_iyiou_investors(record.get("investors")),
            reg_location=str(record.get("regLocation") or ""),
            province=str(record.get("provinceDesc") or ""),
            country=str(record.get("countryDesc") or ""),
            industry=str(record.get("industryName") or ""),
            com_id=str(record.get("comId") or ""),
        )

    def to_dict(self) -> dict[str, Any]:
        """转换为中文字段名的字典。"""
        return {
            "投资事件ID": self.invest_id,
            "企业简称": self.brief_name,
            "企业全称": self.full_name,
            "简介": self.brief_intro,
            "融资轮次": self.invest_round,
            "融资时间": self.invest_time,
            "融资金额": self.invest_amount,
            "投资方": self.investors,
            "注册地址": self.reg_location,
            "省份": self.province,
            "国家": self.country,
            "行业": self.industry,
            "企业ID": self.com_id,
        }

    def to_row(self) -> dict[str, str]:
        """转换为字符串类型的行字典，用于 Excel 导出。"""
        return {k: str(v) for k, v in self.to_dict().items()}
