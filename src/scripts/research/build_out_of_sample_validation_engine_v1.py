#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
OUT_OF_SAMPLE_VALIDATION_ENGINE_V1

Research-only OOS validation.
Источник кандидатов: research.global_edge_forensic_reports_v1.
Runtime не меняется.
Micro Live не разрешается.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from decimal import Decimal
from typing import Any

import psycopg2
import psycopg2.extras


def db_url() -> str:
    return os.getenv("DATABASE_URL", "postgresql:///finam_core")


def one(cur, sql: str, params: tuple[Any, ...] = ()) -> dict[str, Any] | None:
    cur.execute(sql, params)
    row = cur.fetchone()
    return dict(row) if row else None


def dec(v: Any) -> Decimal:
    if v is None:
        return Decimal("0")
    return Decimal(str(v))


def ensure_tables(cur) -> None:
    cur.execute("CREATE SCHEMA IF NOT EXISTS research")
    cur.execute("""
        CREATE TABLE IF NOT EXISTS research.oos_validation_campaigns_v1 (
            campaign_id BIGSERIAL PRIMARY KEY,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            forensic_report_id BIGINT NOT NULL,
            candidate_id TEXT NOT NULL,
            symbol TEXT NOT NULL,
            strategy TEXT NOT NULL,
            timeframe TEXT NOT NULL,
            train_start TIMESTAMPTZ,
            train_end TIMESTAMPTZ,
            oos_start TIMESTAMPTZ NOT NULL,
            oos_end TIMESTAMPTZ NOT NULL,
            status TEXT NOT NULL,
            payload JSONB NOT NULL
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS research.oos_validation_results_v1 (
            result_id BIGSERIAL PRIMARY KEY,
            campaign_id BIGINT NOT NULL REFERENCES research.oos_validation_campaigns_v1(campaign_id),
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            trades BIGINT NOT NULL,
            wins BIGINT NOT NULL,
            losses BIGINT NOT NULL,
            net_pnl NUMERIC NOT NULL,
            expectancy NUMERIC,
            profit_factor NUMERIC,
            commission NUMERIC NOT NULL,
            max_drawdown NUMERIC,
            status TEXT NOT NULL,
            payload JSONB NOT NULL
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS research.oos_validation_decisions_v1 (
            decision_id BIGSERIAL PRIMARY KEY,
            campaign_id BIGINT NOT NULL REFERENCES research.oos_validation_campaigns_v1(campaign_id),
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            decision TEXT NOT NULL,
            decision_reason TEXT NOT NULL,
            runtime_changed BOOLEAN NOT NULL DEFAULT false,
            micro_live_allowed BOOLEAN NOT NULL DEFAULT false,
            payload JSONB NOT NULL
        )
    """)


def load_report(cur, candidate_id: str) -> dict[str, Any]:
    row = one(cur, """
        SELECT *
        FROM research.global_edge_forensic_reports_v1
        WHERE candidate_id=%s
          AND recommendation='PROMOTE_TO_OOS_VALIDATION'
          AND replay_status='PASS'
          AND robustness_status='PASS'
          AND runtime_changed=false
          AND micro_live_allowed=false
        ORDER BY created_at DESC
        LIMIT 1
    """, (candidate_id,))
    if not row:
        raise RuntimeError(f"oos_ready_forensic_report_not_found={candidate_id}")
    return row


def build_oos_dataset(cur, report: dict[str, Any]) -> None:
    payload = report["payload"]
    scorecard_id = int(payload["scorecard_id"])

    cur.execute("DROP TABLE IF EXISTS tmp_oos_edge_v1")
    cur.execute("""
        CREATE TEMP TABLE tmp_oos_edge_v1 AS
        WITH s AS (
            SELECT *
            FROM research.analytics_global_edge_scorecard_v1
            WHERE id=%s
        ),
        ctx AS (
            SELECT
                trade_state_id,
                max(entry_compact_signature) AS instrument_signature,
                max(context_compact_signature) FILTER (WHERE context_code='FX_USDRUB') AS fx_signature,
                max(context_compact_signature) FILTER (WHERE context_code='ENERGY_BR') AS energy_signature
            FROM research.market_state_index_context_links_v1
            GROUP BY trade_state_id
        )
        SELECT
            tss.trade_state_id,
            tss.trade_id,
            tss.symbol,
            ct.strategy,
            tss.timeframe,
            ct.entry_ts,
            ct.exit_ts,
            ct.net_pnl::numeric AS net_pnl,
            ct.commission::numeric AS commission
        FROM research.trade_state_snapshots_v1 tss
        JOIN public.closed_trades ct ON ct.id::text=tss.trade_id::text
        JOIN ctx ON ctx.trade_state_id=tss.trade_state_id
        JOIN s ON true
        WHERE tss.symbol=s.symbol
          AND ct.strategy=s.strategy
          AND tss.timeframe=s.timeframe
          AND ctx.instrument_signature=s.instrument_signature
          AND ctx.fx_signature=s.fx_signature
          AND ctx.energy_signature=s.energy_signature
          AND ct.exit_ts > s.last_trade
    """, (scorecard_id,))


def compute_oos(cur) -> dict[str, Any]:
    row = one(cur, """
        SELECT
            count(*)::bigint AS trades,
            sum(CASE WHEN net_pnl > 0 THEN 1 ELSE 0 END)::bigint AS wins,
            sum(CASE WHEN net_pnl <= 0 THEN 1 ELSE 0 END)::bigint AS losses,
            coalesce(sum(net_pnl),0) AS net_pnl,
            avg(net_pnl) AS expectancy,
            coalesce(sum(CASE WHEN net_pnl > 0 THEN net_pnl ELSE 0 END),0) AS gross_profit,
            abs(coalesce(sum(CASE WHEN net_pnl < 0 THEN net_pnl ELSE 0 END),0)) AS gross_loss,
            coalesce(sum(commission),0) AS commission,
            min(exit_ts) AS oos_start,
            max(exit_ts) AS oos_end
        FROM tmp_oos_edge_v1
    """)
    gross_loss = dec(row["gross_loss"])
    pf = None if gross_loss == 0 else dec(row["gross_profit"]) / gross_loss

    trades = int(row["trades"] or 0)
    net = dec(row["net_pnl"])
    expectancy = dec(row["expectancy"])

    if trades < 20:
        status = "INSUFFICIENT_OOS_SAMPLE"
        decision = "UNDER_REVIEW"
        reason = "oos_trades_below_20"
    elif net > 0 and expectancy > 0 and pf is not None and pf >= Decimal("1.10"):
        status = "OOS_PASS"
        decision = "PASS_TO_SHADOW"
        reason = "positive_oos_edge_confirmed"
    else:
        status = "OOS_FAIL"
        decision = "REJECT"
        reason = "oos_edge_not_confirmed"

    return {
        "trades": trades,
        "wins": int(row["wins"] or 0),
        "losses": int(row["losses"] or 0),
        "net_pnl": str(net),
        "expectancy": str(row["expectancy"]) if row["expectancy"] is not None else None,
        "profit_factor": str(pf) if pf is not None else None,
        "commission": str(row["commission"]),
        "oos_start": row["oos_start"],
        "oos_end": row["oos_end"],
        "status": status,
        "decision": decision,
        "decision_reason": reason,
    }


def save(cur, report: dict[str, Any], metrics: dict[str, Any]) -> int:
    ensure_tables(cur)

    payload = report["payload"]
    train_start = payload.get("scorecard_first_trade") or payload.get("first_trade")
    train_end = payload.get("scorecard_last_trade") or payload.get("last_trade")

    cur.execute("""
        INSERT INTO research.oos_validation_campaigns_v1 (
            forensic_report_id, candidate_id, symbol, strategy, timeframe,
            train_start, train_end, oos_start, oos_end, status, payload
        )
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s::jsonb)
        RETURNING campaign_id
    """, (
        report["report_id"],
        report["candidate_id"],
        report["symbol"],
        report["strategy"],
        report["timeframe"],
        train_start,
        train_end,
        metrics["oos_start"],
        metrics["oos_end"],
        metrics["status"],
        json.dumps({"source": "OUT_OF_SAMPLE_VALIDATION_ENGINE_V1"}, ensure_ascii=False),
    ))
    campaign_id = int(cur.fetchone()["campaign_id"])

    cur.execute("""
        INSERT INTO research.oos_validation_results_v1 (
            campaign_id, trades, wins, losses, net_pnl, expectancy,
            profit_factor, commission, max_drawdown, status, payload
        )
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s::jsonb)
    """, (
        campaign_id,
        metrics["trades"],
        metrics["wins"],
        metrics["losses"],
        metrics["net_pnl"],
        metrics["expectancy"],
        metrics["profit_factor"],
        metrics["commission"],
        None,
        metrics["status"],
        json.dumps(metrics, default=str, ensure_ascii=False),
    ))

    cur.execute("""
        INSERT INTO research.oos_validation_decisions_v1 (
            campaign_id, decision, decision_reason,
            runtime_changed, micro_live_allowed, payload
        )
        VALUES (%s,%s,%s,false,false,%s::jsonb)
    """, (
        campaign_id,
        metrics["decision"],
        metrics["decision_reason"],
        json.dumps(metrics, default=str, ensure_ascii=False),
    ))

    return campaign_id


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--candidate-id", default="MSC-000001")
    parser.add_argument("--save", action="store_true")
    args = parser.parse_args()

    with psycopg2.connect(db_url()) as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            report = load_report(cur, args.candidate_id)
            build_oos_dataset(cur, report)
            metrics = compute_oos(cur)

            campaign_id = 0
            if args.save:
                campaign_id = save(cur, report, metrics)
                conn.commit()
            else:
                conn.rollback()

    print("=== OUT_OF_SAMPLE_VALIDATION_ENGINE_V1 ===")
    print(f"mode={'save' if args.save else 'dry_run'}")
    print(f"candidate_id={args.candidate_id}")
    print(f"campaign_id={campaign_id}")
    print(f"trades={metrics['trades']}")
    print(f"wins={metrics['wins']}")
    print(f"losses={metrics['losses']}")
    print(f"net_pnl={metrics['net_pnl']}")
    print(f"expectancy={metrics['expectancy']}")
    print(f"profit_factor={metrics['profit_factor']}")
    print(f"commission={metrics['commission']}")
    print(f"status={metrics['status']}")
    print(f"decision={metrics['decision']}")
    print(f"decision_reason={metrics['decision_reason']}")
    print("runtime_changed=0")
    print("micro_live_allowed=0")
    print(f"VERDICT={metrics['decision']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
