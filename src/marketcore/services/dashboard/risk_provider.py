from __future__ import annotations

from marketcore.presentation.viewmodels.executive_overview_vm import HomeMetricVM, HomeRiskVM
from marketcore.services.dashboard.db import db_cursor, table_exists


class RiskProvider:
    def _load_level(self) -> tuple[str, str, str]:
        level = "HIGH"
        reason = "Корреляция"
        priority = "P1"

        try:
            with db_cursor() as cur:
                if table_exists(cur, "warehouse.risk_assessment_scorecard_v1"):
                    cur.execute("""
                        SELECT COALESCE(risk_level,'HIGH')
                        FROM warehouse.risk_assessment_scorecard_v1
                        WHERE section_name='Correlation Risk'
                        ORDER BY id DESC
                        LIMIT 1;
                    """)
                    row = cur.fetchone()
                    if row and row[0]:
                        level = str(row[0])
        except Exception:
            level = "HIGH"

        return level, reason, priority

    def load_platform_metric(self) -> HomeMetricVM:
        level, _, _ = self._load_level()
        return HomeMetricVM("Риски", level, level, "План P1", "/risk")

    def load_risk(self) -> HomeRiskVM:
        level, reason, priority = self._load_level()
        return HomeRiskVM(
            title="Риски",
            value=level,
            reason=reason,
            priority=priority,
            action_label="План P1",
            action_href="/risk",
        )
