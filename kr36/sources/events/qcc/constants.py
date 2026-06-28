from __future__ import annotations

QCC_ORIGIN = "https://www.qcc.com"
QCC_GRAPH_ORIGIN = "https://graph.qcc.com"
DATA_SOURCE_QCC = "qcc"

EVENT_MAINLAND_FINANCING = "mainland_financing"
EVENT_IPO = "ipo_event"
EVENT_EXIT = "exit_event"
EVENT_MERGER_ACQUISITION = "merger_acquisition"
EVENT_ADDITIONAL = "additional_financing"
EVENT_INDUSTRIAL_CHAIN = "industrial_chain"

EVENT_TYPES: tuple[str, ...] = (
    EVENT_MAINLAND_FINANCING,
    EVENT_IPO,
    EVENT_EXIT,
    EVENT_MERGER_ACQUISITION,
    EVENT_ADDITIONAL,
    EVENT_INDUSTRIAL_CHAIN,
)

EVENT_TYPE_LABELS: dict[str, str] = {
    "financing": "融资",
    EVENT_MAINLAND_FINANCING: "境内融资",
    EVENT_IPO: "IPO上市",
    EVENT_EXIT: "退出事件",
    EVENT_MERGER_ACQUISITION: "并购事件",
    EVENT_ADDITIONAL: "定向增发",
    EVENT_INDUSTRIAL_CHAIN: "产业链融资",
}

EVENT_PAGE_PATHS: dict[str, str] = {
    "/web/project/venture-capital/mainland-financing": EVENT_MAINLAND_FINANCING,
    "/web/project/venture-capital/ipo-events": EVENT_IPO,
    "/web/project/venture-capital/exit-events": EVENT_EXIT,
    "/web/project/venture-capital/merger-acquisition": EVENT_MERGER_ACQUISITION,
    "/web/project/venture-capital/additional": EVENT_ADDITIONAL,
    "/web/industrial-chain/overview": EVENT_INDUSTRIAL_CHAIN,
}

EVENT_API_PATHS: dict[str, str] = {
    EVENT_MAINLAND_FINANCING: "/api/investOrg/getMainlandFinancingList",
    EVENT_IPO: "/api/investOrg/getIPOFinancingList",
    EVENT_EXIT: "/api/investOrg/getExitFinancingList",
    EVENT_MERGER_ACQUISITION: "/api/investOrg/getMergerAcquisitionList",
    EVENT_ADDITIONAL: "/api/investOrg/getAdditionalFinancingList",
    EVENT_INDUSTRIAL_CHAIN: "/api/investOrg/getFinanceEventsList",
}

EVENT_REFERERS: dict[str, str] = {
    EVENT_MAINLAND_FINANCING: f"{QCC_ORIGIN}/web/project/venture-capital/mainland-financing",
    EVENT_IPO: f"{QCC_ORIGIN}/web/project/venture-capital/ipo-events",
    EVENT_EXIT: f"{QCC_ORIGIN}/web/project/venture-capital/exit-events",
    EVENT_MERGER_ACQUISITION: f"{QCC_ORIGIN}/web/project/venture-capital/merger-acquisition",
    EVENT_ADDITIONAL: f"{QCC_ORIGIN}/web/project/venture-capital/additional",
    EVENT_INDUSTRIAL_CHAIN: f"{QCC_GRAPH_ORIGIN}/web/industrial-chain/overview",
}

DEFAULT_EVENT_TYPE = EVENT_MAINLAND_FINANCING
DEFAULT_PAGE_SIZE = 20
MAX_PAGES = 200
