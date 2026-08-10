from __future__ import annotations

from decimal import Decimal

from marketcore.presentation.viewmodels.research_center_vm import (
    ResearchCandidateVM,
    ResearchCenterVM,
    ResearchCheckVM,
    ResearchEdgeValidationVM,
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
        edge_validation = fallback.edge_validation

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

            robustness_view = (
                "marketcore_ui."
                "trend_pullback_canonical_robustness_v1"
            )

            cost_view = (
                "marketcore_ui."
                "trend_pullback_equity_base_cost_validation_v1"
            )

            if (
                table_exists(cur, robustness_view)
                and table_exists(cur, cost_view)
            ):
                cur.execute("""
                    SELECT
                        r.symbol,
                        r.robustness_status,
                        r.positive_variants,
                        r.variants_total,
                        r.stable_variants,
                        r.variants_evaluated_for_fold_stability,

                        COALESCE(
                            c.cost_validation_status,
                            CASE
                                WHEN r.symbol LIKE '%@RTSX'
                                    THEN 'FUTURES_COST_SEMANTICS_PENDING'
                                ELSE 'COST_VALIDATION_PENDING'
                            END
                        ) AS cost_status,

                        c.net_pnl,
                        c.net_expectancy,
                        c.net_profit_factor,

                        COALESCE(
                            c.economic_edge_claimed,
                            false
                        ) AS economic_edge_claimed,

                        false AS micro_live_allowed

                    FROM
                        marketcore_ui.trend_pullback_canonical_robustness_v1 r

                    LEFT JOIN
                        marketcore_ui.trend_pullback_equity_base_cost_validation_v1 c
                    ON
                        c.symbol = r.symbol
                        AND c.strategy_code = r.strategy_code
                        AND c.timeframe = r.timeframe

                    WHERE
                        r.strategy_code = 'TREND_PULLBACK_V1'
                        AND r.timeframe = 'M5'

                    ORDER BY r.symbol;
                """)

                edge_rows = cur.fetchall()

                if edge_rows:
                    edge_validation = [
                        ResearchEdgeValidationVM(
                            symbol=str(r[0]),
                            robustness=str(r[1]),
                            positive_variants=(
                                f"{r[2]}/{r[3]}"
                            ),
                            stable_variants=(
                                f"{r[4]}/{r[5]}"
                            ),
                            cost_status=str(r[6]),
                            net_pnl=(
                                _ru_decimal(r[7], 2)
                                if r[7] is not None
                                else "—"
                            ),
                            net_expectancy=(
                                _ru_decimal(r[8], 4)
                                if r[8] is not None
                                else "—"
                            ),
                            net_profit_factor=(
                                _ru_decimal(r[9], 4)
                                if r[9] is not None
                                else "—"
                            ),
                            economic_edge=(
                                "ДА"
                                if bool(r[10])
                                else "НЕТ"
                            ),
                            micro_live=(
                                "РАЗРЕШЁН"
                                if bool(r[11])
                                else "ЗАПРЕЩЁН"
                            ),
                        )
                        for r in edge_rows
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
            edge_validation=edge_validation,
            actions=fallback.actions,
        )
