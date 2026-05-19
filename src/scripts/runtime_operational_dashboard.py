from __future__ import annotations

import os
from datetime import datetime, timezone

import psycopg2

from finam_core.notifications.telegram_notifier import TelegramNotifier


def scalar(cur, sql: str) -> int:
    cur.execute(sql)
    row = cur.fetchone()
    return int(row[0] or 0)


def main() -> int:
    dsn = os.getenv("DATABASE_URL")
    if not dsn:
        raise RuntimeError("DATABASE_URL is empty")

    send_always = os.getenv(
        "RUNTIME_OPERATIONAL_DASHBOARD_SEND_ALWAYS",
        "0",
    ) == "1"

    conn = psycopg2.connect(dsn)

    with conn:
        with conn.cursor() as cur:
            cur.execute("""
                select
                    created_at,
                    active_signals,
                    active_watchlist,
                    active_positions,
                    status
                from runtime_state_snapshots
                where state_key = 'runtime_state'
                order by created_at desc
                limit 1
            """)
            snapshot = cur.fetchone()

            cur.execute("""
                select
                    coalesce(margin_utilization_pct, 0),
                    coalesce(drawdown, 0),
                    coalesce(total_exposure, exposure, 0)
                from portfolio_snapshots
                order by ts desc
                limit 1
            """)
            portfolio = cur.fetchone()

            cur.execute("""
                select count(*)
                from market_radar_results
                where ts >= now() - interval '30 minutes'
                  and status = 'ANOMALY'
            """)
            market_anomalies = int(cur.fetchone()[0] or 0)

            cur.execute("""
                select count(*)
                from radar_candidate_analysis
                where created_at >= now() - interval '30 minutes'
                  and decision = 'WATCH'
            """)
            watch_decisions = int(cur.fetchone()[0] or 0)

            cur.execute("""
                select count(*)
                from radar_candidate_analysis
                where created_at >= now() - interval '30 minutes'
                  and decision = 'ALERT'
            """)
            alert_decisions = int(cur.fetchone()[0] or 0)

            cur.execute("""
                select count(*)
                from signal_lifecycle
                where state in ('NEW','ACTIVE','TRIGGERED')
            """)
            lifecycle_active = int(cur.fetchone()[0] or 0)

            cur.execute("""
                select count(*)
                from signal_lifecycle
                where state = 'CLOSED'
                  and closed_at >= now() - interval '24 hours'
            """)
            lifecycle_closed = int(cur.fetchone()[0] or 0)

    if snapshot is None:
        print("RUNTIME_OPERATIONAL_DASHBOARD_EMPTY", flush=True)
        return 0

    snapshot_ts = snapshot[0]
    active_signals = int(snapshot[1] or 0)
    active_watchlist = int(snapshot[2] or 0)
    active_positions = int(snapshot[3] or 0)
    runtime_status = snapshot[4]

    margin_utilization_pct = float(portfolio[0] or 0) if portfolio else 0.0
    drawdown = float(portfolio[1] or 0) if portfolio else 0.0
    total_exposure = float(portfolio[2] or 0) if portfolio else 0.0

    severity = "INFO"

    if market_anomalies >= 3:
        severity = "CRITICAL"
    elif margin_utilization_pct >= 70:
        severity = "WARNING"
    elif active_watchlist == 0:
        severity = "WARNING"

    text = (
        "🧭 Runtime Operational Dashboard\n\n"
        f"Severity: {severity}\n"
        f"Snapshot: {snapshot_ts}\n"
        f"Runtime status: {runtime_status}\n\n"

        "=== Runtime ===\n"
        f"Signals: {active_signals}\n"
        f"Watchlist: {active_watchlist}\n"
        f"Positions: {active_positions}\n\n"

        "=== Portfolio ===\n"
        f"Margin utilization: {margin_utilization_pct:.2f}%\n"
        f"Drawdown: {drawdown:.2f}\n"
        f"Exposure: {total_exposure:.2f}\n\n"

        "=== Market ===\n"
        f"Market anomalies: {market_anomalies}\n"
        f"Runtime WATCH: {watch_decisions}\n"
        f"Runtime ALERT: {alert_decisions}\n\n"

        "=== Lifecycle ===\n"
        f"Lifecycle ACTIVE: {lifecycle_active}\n"
        f"Lifecycle CLOSED 24h: {lifecycle_closed}\n"
    )

    print(
        "RUNTIME_OPERATIONAL_DASHBOARD_OK "
        f"severity={severity} "
        f"signals={active_signals} "
        f"watchlist={active_watchlist} "
        f"positions={active_positions}",
        flush=True,
    )

    if severity in ("WARNING", "CRITICAL") or send_always:
        TelegramNotifier().send(text)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
