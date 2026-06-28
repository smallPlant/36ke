"""数据模型：融资公司、项目详情、股东、导出行列与缓存统计。"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass
class FinancingCompany:
    """单条融资/创投事件，兼容 36氪、亿欧与企查查。"""

    # 项目 ID（36氪数字 ID，或亿欧/企查查生成的稳定伪 ID）
    project_id: int
    # 企业简称 / 产品名
    project_name: str
    # 企业简介或事件描述
    project_brief: str
    # 行业标签列表
    industry_list: list[str]
    # 融资轮次或退出类型描述
    financing_round: str
    # 融资/事件日期（毫秒时间戳，0 表示未知）
    financing_date: int
    # 融资金额或交易金额文本
    financing_money: str
    # 投资方名称（顿号分隔）
    investor: str
    # 详情页或新闻原文链接
    url: str
    # 数据来源标识：36kr / iyiou / qcc
    source: str = "36kr"
    # 亿欧企业 com_id
    com_id: str = ""
    # 企业工商全称
    full_name: str = ""
    # 注册地址
    reg_location: str = ""
    # 省份
    province: str = ""
    # 国家
    country: str = ""
    # 事件类型：financing / mainland_financing / ipo_event / exit_event 等
    event_type: str = "financing"
    # 数据源侧唯一事件 ID（企查查 Id、亿欧 investId）
    external_id: str = ""
    # 企查查企业 KeyNo
    company_keyno: str = ""
    # 城市
    city: str = ""
    # 区县
    county: str = ""
    # 估值（36kr 等）
    valuation: str = ""
    # 股票代码
    stock_code: str = ""
    # 企查查行业门类
    industry_category: str = ""
    # 企查查行业大类
    industry_major: str = ""
    # 国标行业
    national_industry: str = ""
    # 上市板块（IPO）
    listing_board: str = ""
    # 成立日期 YYYY-MM-DD
    establish_date: str = ""
    # 购买方/竞买方（并购）
    buyer: str = ""
    # 出让方（并购）
    seller: str = ""
    # 交易股权比例（并购）
    trade_equity_ratio: str = ""
    # 退出方式（企查查退出事件）
    exit_type: str = ""
    # 退出方
    holder_name: str = ""
    # 资本回报倍数
    return_multiple: str = ""
    # 内部收益率
    irr: str = ""
    # 退出股权比例
    exit_equity_ratio: str = ""
    # 产业链代码（仅拉取参数，可选持久化）
    chain_code: str = ""
    # 企查查产品/品牌 ID
    product_id: str = ""

    def to_dict(self) -> dict[str, Any]:
        """序列化为普通字典。"""
        return asdict(self)


@dataclass
class FinancingListRow:
    """融资公司列表 Excel 导出行（表1）。"""

    # 企业简称
    brief_name: str
    # 企业全称
    full_name: str
    # 简介
    brief_intro: str
    # 融资轮次
    financing_round: str
    # 融资时间（YYYY-MM-DD）
    financing_date: str
    # 融资金额
    financing_amount: str
    # 投资方
    investor: str
    # 行业（顿号分隔）
    industry: str
    # 注册地址
    reg_location: str
    # 省份
    province: str
    # 国家
    country: str
    # 数据来源：36kr / iyiou / qcc
    source: str = "36kr"
    # 事件类型
    event_type: str = "financing"
    # 企查查行业门类
    industry_category: str = ""
    # 企查查行业大类
    industry_major: str = ""
    # 国标行业
    national_industry: str = ""
    # 城市
    city: str = ""
    # 区县
    county: str = ""
    # 成立日期
    establish_date: str = ""
    # 上市板块
    listing_board: str = ""
    # 购买方
    buyer: str = ""
    # 出让方
    seller: str = ""
    # 交易股权
    trade_equity_ratio: str = ""
    # 退出类型
    exit_type: str = ""
    # 退出方
    holder_name: str = ""
    # 资本回报倍数
    return_multiple: str = ""
    # 内部收益率
    irr: str = ""
    # 退出股权
    exit_equity_ratio: str = ""

    def to_dict(self) -> dict[str, str]:
        """转换为 Excel 列名与中文值的字典。"""
        return {
            "数据来源": self.source_label,
            "事件类型": self.event_type_label,
            "项目名称": self.brief_name,
            "企业名称": self.full_name,
            "简介": self.brief_intro,
            "事件日期": self.financing_date,
            "融资轮次": self.financing_round,
            "融资金额": self.financing_amount,
            "投资方": self.investor,
            "国标行业": self.national_industry,
            "企查查行业门类": self.industry_category,
            "企查查行业大类": self.industry_major,
            "所属省份": self.province,
            "所属城市": self.city,
            "所属区县": self.county,
            "所属地区": self.country,
            "成立日期": self.establish_date,
            "上市板块": self.listing_board,
            "购买方": self.buyer,
            "出让方": self.seller,
            "交易股权": self.trade_equity_ratio,
            "退出方式": self.exit_type,
            "退出方": self.holder_name,
            "资本回报倍数": self.return_multiple,
            "内部收益率": self.irr,
            "退出股权": self.exit_equity_ratio,
        }

    @property
    def source_label(self) -> str:
        """数据来源的中文展示名。"""
        return {"36kr": "36氪", "iyiou": "亿欧", "qcc": "企查查"}.get(self.source, self.source)

    @property
    def event_type_label(self) -> str:
        """事件类型的中文展示名。"""
        from kr36.sources.events.qcc.constants import EVENT_TYPE_LABELS

        return EVENT_TYPE_LABELS.get(self.event_type, self.event_type)


@dataclass
class Shareholder:
    """工商股东信息（来自 36氪 business.shareholder）。"""

    # 股东名称
    name: str
    # 持股比例
    percent: str = ""
    # 认缴出资额
    amount: str = ""
    # 认缴出资日期
    time: str = ""


@dataclass
class ProjectDetail:
    """公司工商详情，含华南地区判定结果与股东列表。"""

    # 36氪项目 ID 或数据源伪 ID
    project_id: int
    # 项目简称
    name: str
    # 工商注册全称
    company_name: str
    # 注册地址
    reg_location: str
    # 英文名称
    english_name: str = ""
    # 法定代表人
    legal_person: str = ""
    # 成立日期
    establish_date: str = ""
    # 省份
    province: str = ""
    # 城市
    city: str = ""
    # 国家
    country: str = "中国"
    # 官网
    website: str = ""
    # 是否属于华南地区（粤桂闽琼）
    is_south_china: bool = False
    # 股东列表
    shareholders: list[Shareholder] = field(default_factory=list)
    # 按名称搜索时使用的关键词（用于缓存键）
    search_keyword: str = ""

    def to_dict(self) -> dict[str, Any]:
        """序列化为普通字典，股东列表嵌套展开。"""
        data = asdict(self)
        data["shareholders"] = [asdict(s) for s in self.shareholders]
        return data


@dataclass
class RelatedCompanyRow:
    """华南关联公司 Excel 导出行（表2）。"""

    # 融资公司名称
    financing_company: str
    # 融资日期
    financing_date: str
    # 融资金额
    financing_amount: str
    # 融资轮次
    financing_round: str
    # 华南关联公司名称
    related_company: str
    # 关联类型：self=融资公司本身，shareholder=股东
    related_type: str = ""

    def to_dict(self) -> dict[str, Any]:
        """转换为 Excel 列名与中文值的字典。"""
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
        """关联类型的中文展示名。"""
        return {"self": "融资公司", "shareholder": "股东"}.get(self.related_type, self.related_type)


@dataclass
class CacheStats:
    """公司详情缓存命中 / 过期 / 新拉取计数。"""

    # 缓存命中次数
    hits: int = 0
    # 缓存未命中（首次拉取）次数
    misses: int = 0
    # 缓存过期后重新拉取次数
    expired: int = 0

    @property
    def total(self) -> int:
        """缓存查询总次数。"""
        return self.hits + self.misses + self.expired
