from __future__ import annotations

from marketcore.presentation.viewmodels.risk_control_center_vm import (
    RiskControlCenterVM,
    RiskEventVM,
    RiskMetricVM,
    RiskRuleVM,
    build_default_risk_control_center_vm,
)
from marketcore.services.common.safe_query import safe_query
from marketcore.services.dashboard.db import db_cursor, table_exists


class RiskControlCenterService:
    def load(self) -> RiskControlCenterVM:
        return safe_query(self._load_from_db, build_default_risk_control_center_vm())

    def _load_from_db(self) -> RiskControlCenterVM:
        fallback = build_default_risk_control_center_vm()

        level = "Высокий"
        level_status = "HIGH"
        reason = "Корреляция"
        priority = "P1"

        rules = fallback.rules
        events = fallback.events

        with db_cursor() as cur:
            if table_exists(cur, "warehouse.risk_assessment_scorecard_v1"):
                cur.execute("""
                    SELECT COALESCE(risk_level, 'HIGH')
                    FROM warehouse.risk_assessment_scorecard_v1
                    WHERE section_name='Correlation Risk'
                    ORDER BY id DESC
                    LIMIT 1;
                """)
                row = cur.fetchone()
                if row and row[0]:
                    level_status = str(row[0])
                    level = "Высокий" if level_status == "HIGH" else str(row[0])

            if table_exists(cur, "public.risk_events"):
                cur.execute("""
                    SELECT
                        COALESCE(created_at::text, 'Сейчас'),
                        COALESCE(event_name, 'Риск'),
                        COALESCE(priority, 'P1'),
                        COALESCE(status, 'HIGH')
                    FROM public.risk_events
                    ORDER BY id DESC
                    LIMIT 5;
                """)
                rows = cur.fetchall()
                if rows:
                    events = [
                        RiskEventVM(
                            time_label="Сейчас",
                            event=str(r[1]),
                            level=str(r[2]),
                            status=str(r[3]),
                        )
                        for r in rows
                    ]

        return RiskControlCenterVM(
            title="Риски",
            subtitle="Risk Control Center",
            overview=[
                RiskMetricVM("Уровень", level, level_status, "План P1", "/risk"),
                RiskMetricVM(reason, priority, level_status, "Проверить", "/risk"),
                RiskMetricVM("Kill Switch", "Готово", "READY", "Детали", "/risk"),
                RiskMetricVM("Micro Live", "Выкл.", "DISABLED", "Детали", "/risk"),
            ],
            rules=rules,
            events=events,
            actions=fallback.actions,
        )
