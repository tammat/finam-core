from __future__ import annotations

import json
import os

import psycopg2

from finam_core.runtime.portfolio_reconciliation_engine import (
    PortfolioReconciliationEngine,
)


def main() -> int:
    dsn = os.getenv("DATABASE_URL")

    if not dsn:
        raise RuntimeError("DATABASE_URL is empty")

    conn = psycopg2.connect(dsn)

    engine = PortfolioReconciliationEngine()

    with conn:
        with conn.cursor() as cur:

            cur.execute("""
                create table if not exists portfolio_reconciliation_events (
                    id bigserial primary key,
                    created_at timestamptz not null default now(),

                    severity text not null,
                    category text not null,
                    symbol text not null,

                    reason text not null,

                    raw_json jsonb not null default '{}'::jsonb
                )
            """)

            issues = []

            cur.execute("""
                select
                    p.symbol,
                    coalesce(p.qty, 0) as position_qty,
                    coalesce(l.remaining_qty, 0) as lifecycle_qty,
                    coalesce(p.source, '') as position_source,
                    exists(
                        select 1
                        from position_lifecycle_state x
                        where x.symbol = p.symbol
                    ) as lifecycle_exists
                from real_portfolio_positions p
                left join position_lifecycle_state l
                    on l.symbol = p.symbol
            """)

            for row in cur.fetchall():
                (
                    symbol,
                    position_qty,
                    lifecycle_qty,
                    position_source,
                    lifecycle_exists,
                ) = row

                # Русский комментарий: ручные/внешние брокерские позиции не считаем ошибкой lifecycle.
                is_runtime_owned = str(position_source) == "paper_execution_bridge"

                if is_runtime_owned:
                    issue = engine.check_position_vs_lifecycle(
                        symbol=symbol,
                        position_qty=float(position_qty),
                        lifecycle_qty=float(lifecycle_qty),
                    )

                    if issue:
                        issues.append(issue)

                    issue = engine.check_orphan_position(
                        symbol=symbol,
                        position_qty=float(position_qty),
                        lifecycle_exists=bool(lifecycle_exists),
                    )

                    if issue:
                        issues.append(issue)

            cur.execute("""
                select
                    l.symbol,
                    coalesce(l.remaining_qty, 0) as lifecycle_qty,
                    exists(
                        select 1
                        from real_portfolio_positions p
                        where p.symbol = l.symbol
                    ) as position_exists
                from position_lifecycle_state l
            """)

            for row in cur.fetchall():
                (
                    symbol,
                    lifecycle_qty,
                    position_exists,
                ) = row

                issue = engine.check_orphan_lifecycle(
                    symbol=symbol,
                    lifecycle_qty=float(lifecycle_qty),
                    position_exists=bool(position_exists),
                )

                if issue:
                    issues.append(issue)

            cur.execute("""
                select
                    symbol,
                    sum(executed_qty) as executed_qty
                from execution_intents
                where intent_state = 'FILLED'
                group by symbol
            """)

            execution_map = {
                row[0]: float(row[1] or 0)
                for row in cur.fetchall()
            }

            cur.execute("""
                select
                    symbol,
                    qty,
                    coalesce(source, '') as source
                from real_portfolio_positions
            """)

            for row in cur.fetchall():
                symbol, position_qty, position_source = row

                # Русский комментарий: execution mismatch проверяем только для runtime-owned paper positions.
                if str(position_source) != "paper_execution_bridge":
                    continue

                executed_qty = execution_map.get(symbol, 0.0)

                issue = engine.check_execution_vs_position(
                    symbol=symbol,
                    executed_qty=float(executed_qty),
                    position_qty=float(position_qty or 0),
                )

                if issue:
                    issues.append(issue)

            inserted = 0

            for issue in issues:

                cur.execute("""
                    insert into portfolio_reconciliation_events (
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
                    "RECONCILIATION_ISSUE "
                    f"severity={issue.severity} "
                    f"category={issue.category} "
                    f"symbol={issue.symbol} "
                    f"reason={issue.reason}",
                    flush=True,
                )

                inserted += 1

    print(
        f"PORTFOLIO_RECONCILIATION_ENGINE_OK issues={inserted}",
        flush=True,
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
