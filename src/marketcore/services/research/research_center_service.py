from __future__ import annotations

from decimal import Decimal

from marketcore.presentation.viewmodels.research_center_vm import (
    ResearchCandidateVM,
    ResearchCenterVM,
    ResearchCheckVM,
    ResearchEdgeValidationVM,
    ResearchFrontierCandidateVM,
    ResearchFrontierVM,
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
        frontier = fallback.frontier

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


            pair_table = (
                "analytics."
                "entry_exit_signal_shadow_pair_v2"
            )

            workflow_table = (
                "analytics."
                "entry_exit_promotion_workflow_v1"
            )

            if (
                table_exists(cur, pair_table)
                and table_exists(cur, workflow_table)
            ):
                cur.execute("""
                    WITH active AS (
                        SELECT DISTINCT
                            strategy_code,
                            symbol_group,
                            side_code,
                            candidate_code
                        FROM
                            analytics.entry_exit_promotion_workflow_v1
                        WHERE
                            evidence #>>
                            '{promotion_workflow,selected_for_shadow_funnel}'
                            = 'true'
                    ),

                    paired AS (
                        SELECT
                            p.strategy_code,
                            p.symbol_code,
                            p.side_code,
                            p.candidate_code,

                            CASE
                                WHEN p.symbol_code LIKE 'BR%@RTSX'
                                    THEN 'BR'
                                WHEN p.symbol_code LIKE 'NG%@RTSX'
                                    THEN 'NG'
                                WHEN p.symbol_code LIKE 'USDRUBF%@RTSX'
                                    THEN 'USD'
                                WHEN p.symbol_code LIKE 'CNYRUBF%@RTSX'
                                    THEN 'CNY'
                                WHEN p.symbol_code LIKE 'GD%@RTSX'
                                    THEN 'GOLD'
                                WHEN p.symbol_code LIKE '%@MISX'
                                    THEN split_part(
                                        p.symbol_code,
                                        '@',
                                        1
                                    )
                                ELSE split_part(
                                    p.symbol_code,
                                    '@',
                                    1
                                )
                            END AS canonical_group,

                            p.shadow_net_r,
                            p.actual_net_r,
                            p.placebo_net_r,
                            p.is_oos

                        FROM
                            analytics.entry_exit_signal_shadow_pair_v2 p

                        WHERE
                            p.shadow_net_r IS NOT NULL
                            AND p.actual_net_r IS NOT NULL
                    ),

                    aggregated AS (
                        SELECT
                            p.strategy_code,
                            p.canonical_group AS symbol_group,
                            p.symbol_code AS physical_symbol,
                            p.side_code,
                            p.candidate_code,

                            count(*) AS pairs,

                            count(*) FILTER (
                                WHERE p.is_oos IS TRUE
                            ) AS oos_pairs,

                            avg(p.shadow_net_r) AS net_expectancy,

                            avg(
                                p.shadow_net_r
                                - p.actual_net_r
                            ) AS paired_gain,

                            avg(
                                p.shadow_net_r
                                - p.placebo_net_r
                            ) FILTER (
                                WHERE p.placebo_net_r
                                    IS NOT NULL
                            ) AS placebo_delta

                        FROM paired p

                        JOIN active a
                          ON a.strategy_code
                                = p.strategy_code
                         AND a.symbol_group
                                = p.canonical_group
                         AND a.side_code
                                = p.side_code
                         AND a.candidate_code
                                = p.candidate_code

                        GROUP BY
                            p.strategy_code,
                            p.canonical_group,
                            p.symbol_code,
                            p.side_code,
                            p.candidate_code
                    ),

                    scored AS (
                        SELECT
                            *,

                            CASE
                                WHEN pairs < 10
                                    THEN 'INSUFFICIENT_SAMPLE'

                                WHEN net_expectancy > 0
                                 AND paired_gain > 0
                                 AND placebo_delta > 0
                                    THEN 'TARGET_CANDIDATE'

                                WHEN net_expectancy > 0
                                 AND paired_gain <= 0
                                    THEN
                                    'NET_POSITIVE_BASELINE_INFERIOR'

                                WHEN net_expectancy <= 0
                                 AND paired_gain > 0
                                    THEN
                                    'BASELINE_SUPERIOR_NET_NEGATIVE'

                                ELSE
                                    'NET_NEGATIVE_BASELINE_INFERIOR'
                            END AS frontier_state,

                            greatest(
                                -net_expectancy,
                                0
                            )
                            +
                            greatest(
                                -paired_gain,
                                0
                            )
                            +
                            greatest(
                                -coalesce(placebo_delta, 0),
                                0
                            )
                            +
                            (
                                greatest(
                                    60 - pairs,
                                    0
                                )::numeric
                                / 60
                            ) AS priority_gap

                        FROM aggregated
                    )

                    SELECT
                        physical_symbol,
                        strategy_code,
                        side_code,
                        candidate_code,
                        frontier_state,
                        pairs,
                        oos_pairs,
                        net_expectancy,
                        paired_gain,
                        placebo_delta,
                        priority_gap

                    FROM scored

                    ORDER BY
                        CASE frontier_state
                            WHEN 'TARGET_CANDIDATE'
                                THEN 0
                            WHEN
                                'NET_POSITIVE_BASELINE_INFERIOR'
                                THEN 1
                            WHEN
                                'BASELINE_SUPERIOR_NET_NEGATIVE'
                                THEN 2
                            WHEN 'INSUFFICIENT_SAMPLE'
                                THEN 3
                            ELSE 4
                        END,
                        priority_gap,
                        pairs DESC

                    LIMIT 5;
                """)

                frontier_rows = cur.fetchall()

                if frontier_rows:
                    frontier_candidates = [
                        ResearchFrontierCandidateVM(
                            rank=index,
                            physical_symbol=str(row[0]),
                            strategy=str(row[1]),
                            side=str(row[2]),
                            candidate=str(row[3]),
                            state=str(row[4]),
                            pairs=int(row[5] or 0),
                            oos_pairs=int(row[6] or 0),
                            net_expectancy=(
                                _ru_decimal(row[7], 4)
                                if row[7] is not None
                                else "—"
                            ),
                            paired_gain=(
                                _ru_decimal(row[8], 4)
                                if row[8] is not None
                                else "—"
                            ),
                            placebo_delta=(
                                _ru_decimal(row[9], 4)
                                if row[9] is not None
                                else "—"
                            ),
                            priority_gap=(
                                _ru_decimal(row[10], 4)
                                if row[10] is not None
                                else "—"
                            ),
                        )
                        for index, row in enumerate(
                            frontier_rows,
                            start=1,
                        )
                    ]

                    frontier = ResearchFrontierVM(
                        status="READY",
                        physical_cohorts=len(
                            frontier_candidates
                        ),
                        target_candidates=sum(
                            row.state == "TARGET_CANDIDATE"
                            for row in frontier_candidates
                        ),
                        contract_mixing_allowed=False,
                        source_read_only=True,
                        rows=frontier_candidates,
                    )

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
            frontier=frontier,
            actions=fallback.actions,
        )
