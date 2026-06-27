from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

from kr36.iyiou.investors import format_iyiou_investors


@dataclass
class InvestEvent:
    invest_id: str
    brief_name: str
    full_name: str
    brief_intro: str
    invest_round: str
    invest_time: str
    invest_amount: str
    investors: str
    reg_location: str
    province: str
    country: str
    industry: str
    com_id: str

    @classmethod
    def from_api_record(cls, record: dict[str, Any]) -> InvestEvent:
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
        return {k: str(v) for k, v in self.to_dict().items()}
