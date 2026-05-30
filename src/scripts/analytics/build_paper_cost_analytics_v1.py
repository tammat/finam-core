from __future__ import annotations

import os
import psycopg
from psycopg.rows import dict_row

from finam_core.analytics.statistics_repository import build_psycopg_url


SQL = """
select
    symbol,
    count(*)::int as trades,
    sum(abs(qty * price))::float as gross_turnover_rub,
    sum(coalesce(commission, 0))::float as commission_column_rub,
    sum(coalesce((payload->>'commission_rub')::float, 0))::float as commission_payload_rub,
    sum(coalesce((payload->>'broker_commission_rub')::float, 0))::float as broker_commission_rub,
    sum(coalesce((payload->>'exchange_commission_rub')::float, 0))::float as exchange_commission_rub,
    sum(coalesce((payload->>'tax_rub')::float, 0))::float as tax_rub,
    sum(coalesce((payload->>'net_cost_rub')::float, 0))::float as net_cost_rub,
    count(*) filter (where payload ? 'net_cost_rub')::int as cost_enriched_trades,
    min(created_at) as first_trade,
    max(created_at) as last_trade
from trades
where coalesce(payload->>'paper_only', 'true') in ('true', '1', 'True')
group by symbol
order by last_trade desc;
"""


def fmt(value: object) -> str:
    try:
        return f"{float(value or 0.0):.6f}"
    except Exception:
        return "0.000000"


def main() -> int:
    print("PAPER_COST_ANALYTICS_V1", flush=True)
    print(
        "PAPER_COST_CONFIG",
        f"currency={os.getenv('PAPER_CURRENCY', 'RUB')}",
        f"broker_rate={os.getenv('PAPER_BROKER_COMMISSION_RATE', '0')}",
        f"exchange_rate={os.getenv('PAPER_EXCHANGE_COMMISSION_RATE', '0')}",
        f"min_commission={os.getenv('PAPER_MIN_COMMISSION', '0')}",
        f"tax_enabled={os.getenv('PAPER_TAX_ENABLED', '0')}",
        f"tax_rate={os.getenv('PAPER_TAX_RATE', '0')}",
        flush=True,
    )

    with psycopg.connect(build_psycopg_url(), row_factory=dict_row) as conn:
        with conn.cursor() as cur:
            cur.execute(SQL)
            rows = [dict(r) for r in cur.fetchall()]

    total_trades = 0
    total_net_cost = 0.0
    total_enriched = 0

    for row in rows:
        trades = int(row.get("trades") or 0)
        enriched = int(row.get("cost_enriched_trades") or 0)
        net_cost = float(row.get("net_cost_rub") or 0.0)

        total_trades += trades
        total_enriched += enriched
        total_net_cost += net_cost

        print(
            "PAPER_COST_SYMBOL",
            f"symbol={row.get('symbol')}",
            f"trades={trades}",
            f"cost_enriched_trades={enriched}",
            f"coverage={(enriched / trades if trades else 0.0):.6f}",
            f"gross_turnover_rub={fmt(row.get('gross_turnover_rub'))}",
            f"commission_column_rub={fmt(row.get('commission_column_rub'))}",
            f"commission_payload_rub={fmt(row.get('commission_payload_rub'))}",
            f"broker_commission_rub={fmt(row.get('broker_commission_rub'))}",
            f"exchange_commission_rub={fmt(row.get('exchange_commission_rub'))}",
            f"tax_rub={fmt(row.get('tax_rub'))}",
            f"net_cost_rub={fmt(row.get('net_cost_rub'))}",
            f"first_trade={row.get('first_trade')}",
            f"last_trade={row.get('last_trade')}",
            flush=True,
        )

    print(
        "PAPER_COST_SUMMARY",
        f"symbols={len(rows)}",
        f"trades={total_trades}",
        f"cost_enriched_trades={total_enriched}",
        f"coverage={(total_enriched / total_trades if total_trades else 0.0):.6f}",
        f"net_cost_rub={total_net_cost:.6f}",
        flush=True,
    )
    print("PAPER_COST_ANALYTICS_V1_OK", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
