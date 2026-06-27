from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass
class FinancingCompany:
    project_id: int
    project_name: str
    project_brief: str
    industry_list: list[str]
    financing_round: str
    financing_date: int
    financing_money: str
    investor: str
    url: str
    source: str = "36kr"
    com_id: str = ""
    full_name: str = ""
    reg_location: str = ""
    province: str = ""
    country: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class FinancingListRow:
    """PDF 2.4 融资公司列表导出行。"""

    brief_name: str
    full_name: str
    brief_intro: str
    financing_round: str
    financing_date: str
    financing_amount: str
    investor: str
    industry: str
    reg_location: str
    province: str
    country: str
    source: str = "36kr"

    def to_dict(self) -> dict[str, str]:
        return {
            "数据来源": self.source_label,
            "企业简称": self.brief_name,
            "企业全称": self.full_name,
            "简介": self.brief_intro,
            "融资轮次": self.financing_round,
            "融资时间": self.financing_date,
            "融资金额": self.financing_amount,
            "投资方": self.investor,
            "行业": self.industry,
            "注册地址": self.reg_location,
            "省份": self.province,
            "国家": self.country,
        }

    @property
    def source_label(self) -> str:
        return {"36kr": "36氪", "iyiou": "亿欧"}.get(self.source, self.source)


@dataclass
class Shareholder:
    name: str
    percent: str = ""
    amount: str = ""
    time: str = ""


@dataclass
class ProjectDetail:
    project_id: int
    name: str
    company_name: str
    reg_location: str
    english_name: str = ""
    legal_person: str = ""
    establish_date: str = ""
    province: str = ""
    city: str = ""
    country: str = "中国"
    website: str = ""
    is_south_china: bool = False
    shareholders: list[Shareholder] = field(default_factory=list)
    search_keyword: str = ""

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["shareholders"] = [asdict(s) for s in self.shareholders]
        return data


@dataclass
class RelatedCompanyRow:
    """Excel 输出行：融资公司 + 华南关联公司。"""

    financing_company: str
    financing_date: str
    financing_amount: str
    financing_round: str
    related_company: str
    related_type: str = ""  # self=融资公司本身, shareholder=股东

    def to_dict(self) -> dict[str, Any]:
        return {
            "融资公司": self.financing_company,
            "融资日期": self.financing_date,
            "融资金额": self.financing_amount,
            "融资轮次": self.financing_round,
            "华南关联公司": self.related_company,
            "关联类型": self.related_type_label,
        }

    @property
    def related_type_label(self) -> str:
        return {"self": "融资公司", "shareholder": "股东"}.get(self.related_type, self.related_type)


@dataclass
class CacheStats:
    hits: int = 0
    misses: int = 0
    expired: int = 0

    @property
    def total(self) -> int:
        return self.hits + self.misses + self.expired
