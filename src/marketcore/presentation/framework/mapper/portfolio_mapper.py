from __future__ import annotations

from typing import Any

from marketcore.presentation.framework.mapper.base_mapper import BaseMapper
from marketcore.presentation.workspace_v2.domain.portfolio_model_v1 import PortfolioRowV1


class PortfolioRowMapperV1(BaseMapper):
    @classmethod
    def from_db(cls, row: Any) -> dict[str, Any]:
        return dict(row)

    @classmethod
    def to_domain(cls, source_view: str, row: Any) -> PortfolioRowV1:
        return PortfolioRowV1(
            source_view=source_view,
            values=cls.from_db(row),
        )

    @classmethod
    def rows_to_domain(cls, source_view: str, rows: list[Any]) -> tuple[PortfolioRowV1, ...]:
        return tuple(cls.to_domain(source_view, row) for row in rows)
