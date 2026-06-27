from __future__ import annotations

from kr36.db.repository import CompanyRepository
from kr36.models import CacheStats, ProjectDetail
from kr36.project import ProjectService


class CachedProjectService:
    """带 30 天 SQLite 缓存的公司详情服务。"""

    def __init__(
        self,
        project: ProjectService,
        company_repo: CompanyRepository,
    ) -> None:
        self.project = project
        self.company_repo = company_repo
        self.stats = CacheStats()

    def get_detail(self, project_id: int) -> ProjectDetail | None:
        cached = self.company_repo.get_by_project_id(project_id)
        if cached and self.company_repo.is_fresh(cached["fetched_at"]):
            self.stats.hits += 1
            return self.company_repo.row_to_detail(cached)
        if cached:
            self.stats.expired += 1
        else:
            self.stats.misses += 1

        detail = self.project.get_detail(project_id)
        if detail:
            self.company_repo.save_detail(detail)
        return detail

    def get_detail_by_name(self, keyword: str) -> ProjectDetail | None:
        keyword = keyword.strip()
        if not keyword:
            return None

        cached = self.company_repo.get_by_search_keyword(keyword)
        if cached and self.company_repo.is_fresh(cached["fetched_at"]):
            self.stats.hits += 1
            return self.company_repo.row_to_detail(cached)

        if cached:
            self.stats.expired += 1
        else:
            self.stats.misses += 1

        detail = self.project.get_detail_by_name(keyword)
        if detail:
            detail.search_keyword = keyword
            self.company_repo.save_detail(detail, search_keyword=keyword)
        return detail
