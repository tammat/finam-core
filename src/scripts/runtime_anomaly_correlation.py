from __future__ import annotations

import os
from datetime import datetime, timezone

import psycopg2

from finam_core.notifications.telegram_notifier import TelegramNotifier


SEVERITY_INFO = "INFO"
SEVERITY_WARNING = "WARNING"
SEVERITY_CRITICAL = "CRITICAL"


def main() -> int:
    dsn = os.getenv("DATABASE_URL")
    if not dsn:
        raise RuntimeError("DATABASE_URL is empty")

    correlation_signal_threshold = int(
        os.getenv("ANOMALY_CORRELATION_SIGNAL_THRESHOLD", "2")
    )

    correlation_watchlist_threshold = int(
        os.getenv("ANOMALY_CORRELATION_WATCHLIST_THRESHOLD", "3")
    )

    conn = psycopg2.connect(dsn)

    with conn:
        with conn.cursor() as cur:
            cur.execute("""
                select
                    created_at,
                    active_signals,
                    active_watchlist,
                    active_positions
                from runtime_state_snapshots
                where state_key = 'runtime_state'
                order by created_at desc
                limit 1
            """)
            snapshot = cur.fetchone()

            cur.execute("""
                select count(*)
                from radar_candidate_analysis
                where created_at >= now() - interval '30 minutes'
                  and reason ilike '%корреляционный лимит%'
            """)
            correlation_blocks = int(cur.fetchone()[0] or 0)

            cur.execute("""
                select count(*)
                from radar_candidate_analysis
                where created_at >= now() - interval '30 minutes'
                  and reason ilike '%нет стратегии%'
            """)
            no_strategy_blocks = int(cur.fetchone()[0] or 0)

            cur.execute("""
                select count(*)
                from radar_candidate_analysis
                where created_at >= now() - interval '30 minutes'
                  and reason ilike '%реальная позиция%'
            """)
            portfolio_blocks = int(cur.fetchone()[0] or 0)

            cur.execute("""
                select count(*)
                from market_radar_results
                where ts >= now() - interval '30 minutes'
                  and status = 'ANOMALY'
            """)
            market_anomalies = int(cur.fetchone()[0] or 0)

    if snapshot is None:
        print("RUNTIME_ANOMALY_CORRELATION_EMPTY", flush=True)
        return 0

    snapshot_ts = snapshot[0]
    active_signals = int(snapshot[1] or 0)
    active_watchlist = int(snapshot[2] or 0)
    active_positions = int(snapshot[3] or 0)

    severity = SEVERITY_INFO
    findings: list[str] = []

    if correlation_blocks >= correlation_signal_threshold:
        severity = SEVERITY_WARNING
        findings.append(
            f"корреляционные блокировки: {correlation_blocks}"
        )

    if no_strategy_blocks >= correlation_watchlist_threshold:
        severity = SEVERITY_WARNING
        findings.append(
            f"watchlist без стратегии: {no_strategy_blocks}"
        )

    if portfolio_blocks >= correlation_signal_threshold:
        severity = SEVERITY_WARNING
        findings.append(
            f"portfolio pressure blocks: {portfolio_blocks}"
        )

    if market_anomalies >= 3:
        severity = SEVERITY_CRITICAL
        findings.append(
            f"market anomalies detected: {market_anomalies}"
        )

    if active_watchlist == 0:
        severity = SEVERITY_CRITICAL
        findings.append("runtime watchlist collapsed")

    if active_signals == 0 and active_positions == 0:
        findings.append("runtime inactive: no signals and no positions")

    text = (
        "🧠 Runtime Anomaly Correlation\n\n"
        f"Severity: {severity}\n"
        f"Snapshot: {snapshot_ts}\n"
        f"Signals: {active_signals}\n"
        f"Watchlist: {active_watchlist}\n"
        f"Positions: {active_positions}\n\n"
    )

    if findings:
        text += "Findings:\n" + "\n".join(findings)

    print(
        "RUNTIME_ANOMALY_CORRELATION_OK "
        f"severity={severity} "
        f"findings={len(findings)}",
        flush=True,
    )

    if severity in (SEVERITY_WARNING, SEVERITY_CRITICAL):
        TelegramNotifier().send(text)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
