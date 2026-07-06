from __future__ import annotations

import psycopg2
import psycopg2.extras

from marketcore.presentation.components import render_data_table, render_kpi_card, render_section
from marketcore.presentation.page import Page


class PaperMtmPage(Page):
    def __init__(self) -> None:
        super().__init__(
            route="/paper-mtm",
            title="Paper MTM",
            icon="📊",
            menu_order=47,
        )

    def render(self) -> str:
        with psycopg2.connect("postgresql:///finam_core") as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute("""
                    SELECT
                        count(*) AS rows,
                        coalesce(sum(trades),0) AS trades,
                        coalesce(round(sum(net_after_tax),6),0) AS net_after_tax,
                        coalesce(round(min(max_drawdown),6),0) AS worst_drawdown
                    FROM analytics.paper_portfolio_mtm_snapshot_v1
                    WHERE snapshot_ts = (
                        SELECT max(snapshot_ts)
                        FROM analytics.paper_portfolio_mtm_snapshot_v1
                    );
                """)
                summary = dict(cur.fetchone() or {})

                cur.execute("""
                    SELECT
                        candidate_id,
                        strategy_code,
                        symbol,
                        timeframe,
                        trades,
                        round(gross_pnl,6) AS gross_pnl,
                        round(commission,6) AS commission,
                        round(slippage,6) AS slippage,
                        round(net_trading_pnl,6) AS net_trading_pnl,
                        round(estimated_tax,6) AS estimated_tax,
                        round(net_after_tax,6) AS net_after_tax,
                        round(max_drawdown,6) AS max_drawdown
                    FROM analytics.paper_portfolio_mtm_snapshot_v1
                    ORDER BY snapshot_id DESC
                    LIMIT 50;
                """)
                rows = [dict(row) for row in cur.fetchall()]

        kpi = "".join([
            render_kpi_card("Кандидаты", summary.get("rows", 0), "последний MTM-снимок"),
            render_kpi_card("Сделки", summary.get("trades", 0), "paper/research trades"),
            render_kpi_card("Net after tax", summary.get("net_after_tax", 0), "после издержек и налога"),
            render_kpi_card("Worst drawdown", summary.get("worst_drawdown", 0), "по последнему снимку"),
        ])

        table = render_data_table(
            [
                "candidate_id",
                "strategy_code",
                "symbol",
                "timeframe",
                "trades",
                "gross_pnl",
                "commission",
                "slippage",
                "net_trading_pnl",
                "estimated_tax",
                "net_after_tax",
                "max_drawdown",
            ],
            rows,
        )

        return (
            render_section("Paper MTM", kpi)
            + render_section("Последние MTM-снимки", table)
        )
