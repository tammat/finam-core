from __future__ import annotations

import os
import uuid

import psycopg2
import psycopg2.extras


DB = os.getenv("DATABASE_URL", "postgresql:///finam_core")
TARGET = int(os.getenv("FRESH_V3_OOS_MIN_TRADES", "80"))
NAMESPACE = uuid.UUID("fba690ab-b371-4ee3-bcb3-4012c8ae506e")


def missing(value: object) -> bool:
    return str(value or "").strip().upper() in {"", "UNKNOWN", "UNSPECIFIED"}


def plan_status(row: dict) -> tuple[str, str]:
    if missing(row.get("session_code")) or missing(row.get("exit_rule")):
        return "WAITING_CONTEXT_DEFINITION", "ARCHIVE_SESSION_OR_EXIT_MISSING"
    if missing(row.get("regime_code")):
        return "ACTIVE_SPLIT_REGIME", "COLLECT_EACH_OBSERVED_REGIME_SEPARATELY"
    if int(row.get("accumulated_trades") or 0) >= TARGET:
        return "READY_FOR_OOS", "EXACT_V3_SAMPLE_READY"
    if str(row.get("side_code") or "").upper() == "SHORT":
        return "ACTIVE", "COLLECT_ARCHIVE_SHORT_BRANCH"
    return "ACTIVE", "COLLECT_EXACT_ARCHIVE_CONTEXT"


def main() -> int:
    with psycopg2.connect(DB) as connection:
        with connection.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cursor:
            cursor.execute("SELECT pg_try_advisory_lock(194001) locked")
            if not cursor.fetchone()["locked"]:
                print("VERDICT=ARCHIVE_EXACT_V3_BRANCH_PLAN_ALREADY_RUNNING")
                return 0
            cursor.execute("""
                SELECT h.hypothesis_id archive_hypothesis_id,h.symbol archive_symbol,
                       h.strategy_code,h.side_code,h.session_code,h.regime_code,h.holding_code exit_rule,
                       h.priority_score,b.portfolio_scope,b.symbol,
                       coalesce(max(CASE WHEN b.archive_match_code='EXACT' THEN b.v3_closed_trades END),0)::int accumulated_trades
                FROM analytics.trade_outcome_hypothesis_v1 h
                JOIN analytics.archive_v3_oos_bridge_v1 b ON b.archive_hypothesis_id=h.hypothesis_id
                  AND split_part(b.symbol,'@',1) LIKE h.symbol || '%'
                GROUP BY h.hypothesis_id,h.symbol,h.strategy_code,h.side_code,h.session_code,h.regime_code,
                         h.holding_code,h.priority_score,b.portfolio_scope,b.symbol
                ORDER BY h.priority_score DESC
            """)
            rows = [dict(row) for row in cursor.fetchall()]
            for row in rows:
                status, reason = plan_status(row)
                branch_id = uuid.uuid5(NAMESPACE, str(row["archive_hypothesis_id"]))
                cursor.execute("""
                    INSERT INTO analytics.archive_exact_v3_branch_plan_v1(
                        branch_id,archive_hypothesis_id,portfolio_scope,symbol,strategy_code,side_code,
                        session_code,regime_code,exit_rule,accumulated_trades,target_trades,priority_score,
                        status_code,reason_code
                    ) VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                    ON CONFLICT(archive_hypothesis_id) DO UPDATE SET portfolio_scope=excluded.portfolio_scope,
                        symbol=excluded.symbol,strategy_code=excluded.strategy_code,side_code=excluded.side_code,
                        session_code=excluded.session_code,regime_code=excluded.regime_code,exit_rule=excluded.exit_rule,
                        accumulated_trades=excluded.accumulated_trades,target_trades=excluded.target_trades,
                        priority_score=excluded.priority_score,status_code=excluded.status_code,
                        reason_code=excluded.reason_code,updated_at=clock_timestamp()
                """, (str(branch_id),str(row["archive_hypothesis_id"]),row["portfolio_scope"],row["symbol"],
                      row["strategy_code"],row["side_code"],row["session_code"],row["regime_code"],row["exit_rule"],
                      row["accumulated_trades"],TARGET,row["priority_score"],status,reason))
    print(f"branches={len(rows)}")
    print("VERDICT=ARCHIVE_EXACT_V3_BRANCH_PLAN_V1_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
