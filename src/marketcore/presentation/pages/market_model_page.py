from __future__ import annotations

import psycopg2
import psycopg2.extras

from marketcore.presentation.components import render_data_table, render_kpi_card, render_section, render_tree_view
from marketcore.presentation.page import Page


class MarketModelPage(Page):
    def __init__(self) -> None:
        super().__init__(
            route="/market-model",
            title="Market Model",
            icon="🧩",
            menu_order=48,
        )

    def render(self) -> str:
        with psycopg2.connect("postgresql:///finam_core") as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute("""
                    SELECT
                        count(*) AS instruments,
                        count(*) FILTER (WHERE is_active=true) AS active_instruments,
                        count(DISTINCT asset_class) AS asset_classes,
                        count(DISTINCT exchange_code) AS exchanges
                    FROM analytics.market_instrument_v1;
                """)
                summary = dict(cur.fetchone() or {})

                cur.execute("""
                    SELECT
                        i.symbol,
                        i.exchange_code,
                        i.asset_class,
                        i.currency_code,
                        i.eligibility_scope,
                        s.lot_size,
                        s.tick_size,
                        s.tick_value,
                        s.contract_multiplier,
                        s.price_precision
                    FROM analytics.market_instrument_v1 i
                    JOIN analytics.market_contract_spec_v1 s
                      ON s.symbol=i.symbol
                     AND s.is_active=true
                    WHERE i.is_active=true
                    ORDER BY i.exchange_code, i.asset_class, i.symbol
                    LIMIT 100;
                """)
                rows = [dict(row) for row in cur.fetchall()]

        kpi = "".join([
            render_kpi_card("Инструменты", summary.get("instruments", 0), "в market model"),
            render_kpi_card("Активные", summary.get("active_instruments", 0), "доступны для расчётов"),
            render_kpi_card("Классы активов", summary.get("asset_classes", 0), "asset_class"),
            render_kpi_card("Биржи", summary.get("exchanges", 0), "exchange_code"),
        ])

        tree = render_tree_view({
            "Market Model": {
                "Instrument": "symbol, exchange, asset_class, currency",
                "Contract": "lot_size, tick_size, tick_value, multiplier",
                "Trading Cost": "broker fee, exchange fee, slippage",
                "Tax": "account tax profile",
                "Eligibility": "BASE / QUALIFIED universe",
                "Version": "market model snapshot",
            }
        })

        table = render_data_table(
            [
                "symbol",
                "exchange_code",
                "asset_class",
                "currency_code",
                "eligibility_scope",
                "lot_size",
                "tick_size",
                "tick_value",
                "contract_multiplier",
                "price_precision",
            ],
            rows,
        )

        return (
            render_section("Market Model", kpi)
            + render_section("Структура модели", tree)
            + render_section("Активные инструменты", table)
        )
