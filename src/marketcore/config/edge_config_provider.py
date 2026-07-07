from __future__ import annotations

import os
from decimal import Decimal
from typing import Any

import psycopg2
import psycopg2.extras


class EdgeConfigProvider:
    def __init__(
        self,
        edge_name: str = "EDGE_DISCOVERY_LOOP",
        database_url: str | None = None,
    ) -> None:
        self.edge_name = edge_name
        self.database_url = database_url or os.getenv("DATABASE_URL", "postgresql:///finam_core")
        self._config: dict[str, Any] = {}
        self._enabled = False

    def load(self) -> "EdgeConfigProvider":
        with psycopg2.connect(self.database_url) as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute(
                    """
                    SELECT enabled, config_json
                    FROM analytics.edge_configuration_v1
                    WHERE edge_name=%s
                    """,
                    (self.edge_name,),
                )
                row = cur.fetchone()

        if not row:
            raise LookupError(f"EDGE_CONFIG_NOT_FOUND edge_name={self.edge_name}")

        self._enabled = bool(row["enabled"])
        self._config = dict(row["config_json"] or {})
        return self

    def raw(self) -> dict[str, Any]:
        return dict(self._config)

    def discovery_enabled(self) -> bool:
        return self._enabled and bool(self._config.get("discovery_enabled", False))

    def profile(self) -> str:
        return str(self._config.get("profile", "DEFAULT"))

    def interval_minutes(self) -> int:
        return int(self._config.get("interval_minutes", 60))

    def max_parallel_research_jobs(self) -> int:
        return int(self._config.get("max_parallel_research_jobs", 1))

    def max_new_parameter_searches_per_day(self) -> int:
        return int(self._config.get("max_new_parameter_searches_per_day", 10))

    def max_active_sprints(self) -> int:
        return int(self._config.get("max_active_sprints", 1))

    def min_candidate_score(self) -> Decimal:
        return Decimal(str(self._config.get("min_candidate_score", "0")))

    def min_expectancy(self) -> Decimal:
        return Decimal(str(self._config.get("min_expectancy", "0")))

    def min_profit_factor(self) -> Decimal:
        return Decimal(str(self._config.get("min_profit_factor", "1.0")))

    def max_drawdown_pct(self) -> Decimal:
        return Decimal(str(self._config.get("max_drawdown_pct", "100")))

    def paper_candidates_limit(self) -> int:
        return int(self._config.get("paper_candidates_limit", 10))

    def auto_recommendation(self) -> bool:
        return bool(self._config.get("auto_recommendation", False))

    def auto_queue(self) -> bool:
        return bool(self._config.get("auto_queue", False))

    def auto_paper(self) -> bool:
        return bool(self._config.get("auto_paper", False))

    def market_data_max_age_sec(self) -> int:
        return int(self._config.get("market_data_max_age_sec", 900))
