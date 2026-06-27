from __future__ import annotations

IYIOU_INVEST_LIST_URL = "https://data.iyiou.com/company/investlist"
IYIOU_API_BASE = "https://apidata.iyiou.com"
IYIOU_INVEST_API = f"{IYIOU_API_BASE}/spa/invest/defaultList"

DEFAULT_COLUMN_ORDER = (
    "briefName,fullName,briefIntro,investRoundDesc,investTime,investAmount,investors,"
    "regLocation,establishTime,operatingStatusDesc,industryName,tags,countryDesc,provinceDesc"
)

STEALTH_USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)

STEALTH_INIT_SCRIPT = 'Object.defineProperty(navigator, "webdriver", {get: () => undefined})'
