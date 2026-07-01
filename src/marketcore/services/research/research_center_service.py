from __future__ import annotations

from decimal import Decimal

from marketcore.presentation.viewmodels.research_center_vm import (
    ResearchCandidateVM,
    ResearchCenterVM,
    ResearchCheckVM,
    ResearchMetricVM,
    build_default_research_center_vm,
)
from marketcore.services.common.safe_query import safe_query
from marketcore.services.dashboard.db import db_cursor, table_exists


def _ru_decimal(value: object, digits: int = 2) -> str:
    try:
        return f"{Decimal(str(value)):.{digits}f}".replace(".", ",")
    except Exception:
        return "0,00"


class ResearchCenterService:
    def load(self) -> ResearchCenterVM:
        fallback = build_default_research_center_vm()
        return safe_query(self._load_from_db, fallback)

    def _load_from_db(self) -> ResearchCenterVM:
        fallback = build_default_research_center_vm()

        candidates = fallback.candidates
        checks = fallback.checks

        with db_cursor() as cur:
            if table_exists(cur, "public.analytics_research_candidates"):
                cur.execute("""
                    SELECT
                        COALESCE(symbol, 'BRM6@RTSX'),
                        COALESCE(strategy_name, 'BR Breakout'),
                        COALESCE(timeframe, 'M5'),
                        COALESCE(trades_count, 0),
                        COALESCE(net_pnl, 0),
                        COALESCE(profit_factor, 0),
                        COALESCE(status, 'READY')
                    FROM public.analytics_research_candidates
                    ORDER BY id DESC
                    LIMIT 5;
                """)
                rows = cur.fetchall()
                if rows:
                    candidates = [
                        ResearchCandidateVM(
                            symbol=str(r[0]),
                            strategy=str(r[1]),
                            timeframe=str(r[2]),
                            trades=str(r[3]),
                            pnl=_ru_decimal(r[4], 2),
                            pf=_ru_decimal(r[5], 2),
                            status=str(r[6]),
                        )
                        for r in rows
                    ]

            if table_exists(cur, "public.analytics_research_checks"):
                cur.execute("""
                    SELECT
                        COALESCE(check_name, 'Проверка'),
                        COALESCE(result_label, 'Готово'),
                        COALESCE(status, 'READY')
                    FROM public.analytics_research_checks
                    ORDER BY id DESC
                    LIMIT 5;
                """)
                rows = cur.fetchall()
                if rows:
                    checks = [
                        ResearchCheckVM(
                            check=str(r[0]),
                            result=str(r[1]),
                            status=str(r[2]),
                        )
                        for r in rows
                    ]

        return ResearchCenterVM(
            title="Исследования",
            subtitle="Research Center",
            overview=[
                ResearchMetricVM("Кандидаты", str(len(candidates)), "READY", "Открыть", "/research"),
                ResearchMetricVM("Replay", "Готово", "READY", "Детали", "/research"),
                ResearchMetricVM("OOS", "План", "WARNING", "Детали", "/research"),
                ResearchMetricVM("Edge", "Есть", "READY", "Детали", "/research"),
            ],
            candidates=candidates,
            checks=checks,
            actions=fallback.actions,
        )
