from __future__ import annotations

import json
import os

import psycopg2

from finam_core.runtime.broker_reconciliation_engine import BrokerReconciliationEngine


def main() -> int:
    dsn = os.getenv("DATABASE_URL")
    if not dsn:
        raise RuntimeError("DATABASE_URL is empty")

    conn = psycopg2.connect(dsn)
    engine = BrokerReconciliationEngine()

    with conn:
        with conn.cursor() as cur:
            cur.execute("""
                create table if not exists broker_reconciliation_events (
                    id bigserial primary key,
                    created_at timestamptz not null default now(),
                    severity text not null,
                    category text not null,
                    symbol text not null,
                    reason text not null,
                    raw_json jsonb not null default '{}'::jsonb
                )
            """)

            cur.execute("""
                select
                    symbol,
                    sum(executed_qty) as bot_executed_qty
                from execution_intents
                where intent_state = 'FILLED'
                group by symbol
            """)

            bot_exec = {
                str(symbol): float(qty or 0.0)
                for symbol, qty in cur.fetchall()
            }

            cur.execute("""
                select
                    symbol,
                    coalesce(qty, 0) as broker_qty,
                    coalesce(source, '') as source
                from real_portfolio_positions
                where coalesce(qty, 0) <> 0
            """)

            issues = []

            for symbol, broker_qty, source in cur.fetchall():
                issue = engine.classify_position(
                    symbol=str(symbol),
                    broker_qty=float(broker_qty or 0.0),
                    bot_executed_qty=float(bot_exec.get(str(symbol), 0.0)),
                    source=str(source or ""),
                )

                if issue:
                    issues.append(issue)


            cur.execute("""
                select
                    coalesce(source, 'UNKNOWN') as source,
                    count(*) as positions,
                    sum(abs(qty)) as total_qty
                from real_portfolio_positions
                where coalesce(qty, 0) <> 0
                group by coalesce(source, 'UNKNOWN')
                order by positions desc
            """)

            for source, positions, total_qty in cur.fetchall():
                print(
                    "BROKER_RECONCILIATION_SUMMARY "
                    f"source={source} "
                    f"positions={positions} "
                    f"total_qty={total_qty}",
                    flush=True,
                )

            inserted = 0

            for issue in issues:
                cur.execute("""
                    insert into broker_reconciliation_events (
                        severity,
                        category,
                        symbol,
                        reason,
                        raw_json
                    )
                    values (%s,%s,%s,%s,%s::jsonb)
                """, (
                    issue.severity,
                    issue.category,
                    issue.symbol,
                    issue.reason,
                    json.dumps({
                        "severity": issue.severity,
                        "category": issue.category,
                        "symbol": issue.symbol,
                        "reason": issue.reason,
                    }, ensure_ascii=False),
                ))

                print(
                    "BROKER_RECONCILIATION_EVENT "
                    f"severity={issue.severity} "
                    f"category={issue.category} "
                    f"symbol={issue.symbol} "
                    f"reason={issue.reason}",
                    flush=True,
                )

                inserted += 1

    print(f"BROKER_RECONCILIATION_ENGINE_OK events={inserted}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
