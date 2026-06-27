from __future__ import annotations

from kr36.client import PitchHubClient
from kr36.config import PITCHHUB_ORIGIN
from kr36.filters import is_south_china_region
from kr36.models import ProjectDetail, Shareholder
from kr36.region import parse_address


class ProjectService:
    """搜索项目并解析公司详情（工商信息、股东列表）。"""

    SEARCH_PATH = "project/search"
    DETAIL_PATH = "project/detail"
    SEARCH_REFERER = f"{PITCHHUB_ORIGIN}/search"

    def __init__(self, client: PitchHubClient | None = None) -> None:
        self.client = client or PitchHubClient()

    def search_project_id(self, keyword: str) -> int | None:
        keyword = keyword.strip()
        if not keyword:
            return None
        data = self.client.gateway_post(
            self.SEARCH_PATH,
            {"keyword": keyword, "pageNo": 1, "pageSize": 5},
            referer=self.SEARCH_REFERER,
        )["data"]
        for item in data.get("projectList", []):
            name = self.client.strip_html(item.get("companyName") or item.get("name") or "")
            if keyword in name or name in keyword:
                return int(item["id"])
        project_list = data.get("projectList", [])
        if project_list:
            return int(project_list[0]["id"])
        return None

    def get_detail(self, project_id: int) -> ProjectDetail | None:
        detail = self._fetch_detail_via_gateway(project_id)
        if detail:
            return detail
        return self._fetch_detail_via_html(project_id)

    def get_detail_by_name(self, keyword: str) -> ProjectDetail | None:
        project_id = self.search_project_id(keyword)
        if not project_id:
            return None
        detail = self.get_detail(project_id)
        if detail:
            detail.search_keyword = keyword.strip()
        return detail

    def _fetch_detail_via_gateway(self, project_id: int) -> ProjectDetail | None:
        try:
            data = self.client.gateway_post(
                self.DETAIL_PATH,
                {"id": project_id},
                referer=f"{PITCHHUB_ORIGIN}/project/{project_id}",
            )["data"]
        except RuntimeError:
            return None
        return self._build_detail(project_id, data)

    def _fetch_detail_via_html(self, project_id: int) -> ProjectDetail | None:
        html = self.client.get_project_html(project_id)
        props = self.client.parse_init_props(html)
        if not props:
            return None
        project_data = props.get("projectData") or {}
        return self._build_detail(
            int(project_data.get("projectId") or project_id),
            project_data,
        )

    def _build_detail(self, project_id: int, data: dict) -> ProjectDetail | None:
        business = data.get("business") or {}
        shareholders = self._parse_shareholders(business.get("shareholder"))
        if not business and not shareholders and not data.get("name"):
            return None

        reg_location = business.get("regLocation") or ""
        province = data.get("provinceName") or ""
        city = ""
        parsed = parse_address(reg_location)
        if parsed:
            province = province or parsed.province
            city = parsed.city

        country = "海外" if data.get("ifOverseas") else "中国"
        if parsed and parsed.province and country == "中国":
            pass

        return ProjectDetail(
            project_id=project_id,
            name=data.get("name", ""),
            company_name=business.get("name") or data.get("companyName", ""),
            reg_location=reg_location,
            english_name=business.get("property3") or "",
            legal_person=business.get("legalPersonName") or "",
            establish_date=business.get("estiblishTime") or data.get("setupDate") or "",
            province=province,
            city=city,
            country=country,
            website=data.get("corpWebUrl") or "",
            is_south_china=is_south_china_region(reg_location=reg_location, province=province),
            shareholders=shareholders,
        )

    @staticmethod
    def _parse_shareholders(raw_list: list | None) -> list[Shareholder]:
        return [
            Shareholder(
                name=item.get("name", ""),
                percent=item.get("percent", ""),
                amount=item.get("amomon", ""),
                time=item.get("time", ""),
            )
            for item in (raw_list or [])
            if item.get("name")
        ]
