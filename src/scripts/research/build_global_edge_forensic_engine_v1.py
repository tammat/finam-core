#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
GLOBAL_EDGE_FORENSIC_ENGINE_V1

Единый research-only forensic engine:
- воспроизводит edge dataset через trade_state_snapshots + closed_trades + context_links;
- сверяет replay со scorecard;
- считает forensic и robustness;
- не меняет Runtime;
- не разрешает Micro Live;
- запись в БД только с --save.
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


def d(value: Any) -> Decimal:
    if value is None:
        return Decimal("0")
    return Decimal(str(value))


def one(cur, sql: str, params: tuple[Any, ...] = ()) -> dict[str, Any] | None:
    cur.execute(sql, params)
    row = cur.fetchone()
    return dict(row) if row else None


def all_rows(cur, sql: str, params: tuple[Any, ...] = ()) -> list[dict[str, Any]]:
    cur.execute(sql, params)
    return [dict(r) for r in cur.fetchall()]


def ensure_report_table(cur) -> None:
    cur.execute("CREATE SCHEMA IF NOT EXISTS research")
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS research.global_edge_forensic_reports_v1 (
            report_id BIGSERIAL PRIMARY KEY,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            candidate_id TEXT NOT NULL,
            symbol TEXT NOT NULL,
            strategy TEXT NOT NULL,
            timeframe TEXT NOT NULL,
            replay_status TEXT NOT NULL,
            forensic_status TEXT NOT NULL,
            robustness_status TEXT NOT NULL,
            recommendation TEXT NOT NULL,
            micro_live_allowed BOOLEAN NOT NULL DEFAULT false,
            runtime_changed BOOLEAN NOT NULL DEFAULT false,
            payload JSONB NOT NULL
        )
        """
    )


def load_candidate(cur, candidate_id: str) -> dict[str, Any]:
    row = one(
        cur,
        """
        SELECT *
        FROM research.research_candidates_v1
        WHERE candidate_id=%s
        """,
        (candidate_id,),
    )
    if not row:
        raise RuntimeError(f"candidate_not_found={candidate_id}")
    return row


def load_scorecard(cur, candidate: dict[str, Any]) -> dict[str, Any]:
    # Сначала ищем строго по полному набору сигнатур кандидата.
    # Если seed-кандидат содержит устаревшие сигнатуры, используем безопасный fallback
    # по symbol/strategy/timeframe и берем последний scorecard как источник replay.
    row = one(
        cur,
        """
        SELECT *
        FROM research.analytics_global_edge_scorecard_v1
        WHERE symbol=%s
          AND strategy=%s
          AND timeframe=%s
          AND instrument_signature=%s
          AND fx_signature=%s
          AND energy_signature=%s
        ORDER BY created_at DESC
        LIMIT 1
        """,
        (
            candidate["symbol"],
            candidate["strategy"],
            candidate["timeframe"],
            candidate["instrument_signature"],
            candidate["fx_signature"],
            candidate["energy_signature"],
        ),
    )
    if row:
        row["scorecard_match_mode"] = "STRICT_SIGNATURE"
        return row

    row = one(
        cur,
        """
        SELECT *
        FROM research.analytics_global_edge_scorecard_v1
        WHERE symbol=%s
          AND strategy=%s
          AND timeframe=%s
        ORDER BY created_at DESC
        LIMIT 1
        """,
        (
            candidate["symbol"],
            candidate["strategy"],
            candidate["timeframe"],
        ),
    )
    if row:
        row["scorecard_match_mode"] = "FALLBACK_SYMBOL_STRATEGY_TIMEFRAME"
        return row

    # Последний безопасный fallback для первого вручную расследованного кандидата.
    # MSC-000001 был создан seed-скриптом и содержит устаревшую идентификацию,
    # а воспроизводимый scorecard подтвержден как research.analytics_global_edge_scorecard_v1.id=1.
    if candidate.get("candidate_id") == "MSC-000001":
        row = one(
            cur,
            """
            SELECT *
            FROM research.analytics_global_edge_scorecard_v1
            WHERE id=1
            """,
        )
        if row:
            row["scorecard_match_mode"] = "FALLBACK_CANONICAL_SCORECARD_ID_1"
            return row

    raise RuntimeError("matching_scorecard_not_found")


def build_temp_edge_dataset(cur, candidate: dict[str, Any], scorecard: dict[str, Any]) -> None:
    cur.execute("DROP TABLE IF EXISTS tmp_global_edge_forensic_v1")
    cur.execute(
        """
        CREATE TEMP TABLE tmp_global_edge_forensic_v1 AS
        WITH ctx AS (
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
            ctx.instrument_signature,
            ctx.fx_signature,
            ctx.energy_signature,
            ct.entry_ts,
            ct.exit_ts,
            ct.net_pnl::numeric AS net_pnl,
            ct.commission::numeric AS commission,
            coalesce(ct.root_symbol,'NULL') AS contract,
            coalesce(ct.entry_regime,'unknown') AS entry_regime,
            coalesce(ct.exit_regime,'unknown') AS exit_regime
        FROM research.trade_state_snapshots_v1 tss
        JOIN public.closed_trades ct
          ON ct.id::text=tss.trade_id::text
        JOIN ctx
          ON ctx.trade_state_id=tss.trade_state_id
        WHERE tss.symbol=%s
          AND ct.strategy=%s
          AND tss.timeframe=%s
          AND ctx.instrument_signature=%s
          AND ctx.fx_signature=%s
          AND ctx.energy_signature=%s
        """,
        (
            scorecard["symbol"],
            scorecard["strategy"],
            scorecard["timeframe"],
            scorecard["instrument_signature"],
            scorecard["fx_signature"],
            scorecard["energy_signature"],
        ),
    )


def compute_report(cur, candidate: dict[str, Any], scorecard: dict[str, Any]) -> dict[str, Any]:
    replay = one(
        cur,
        """
        SELECT
            count(*)::int AS trades,
            sum(CASE WHEN net_pnl > 0 THEN 1 ELSE 0 END)::int AS wins,
            sum(CASE WHEN net_pnl <= 0 THEN 1 ELSE 0 END)::int AS losses,
            coalesce(sum(net_pnl),0) AS net_pnl,
            avg(net_pnl) AS expectancy,
            coalesce(sum(CASE WHEN net_pnl > 0 THEN net_pnl ELSE 0 END),0) AS gross_profit,
            abs(coalesce(sum(CASE WHEN net_pnl < 0 THEN net_pnl ELSE 0 END),0)) AS gross_loss,
            coalesce(sum(commission),0) AS commission
        FROM tmp_global_edge_forensic_v1
        """
    )

    by_day = all_rows(
        cur,
        """
        SELECT
            to_char(exit_ts,'YYYY-MM-DD') AS day,
            count(*)::int AS trades,
            coalesce(sum(net_pnl),0) AS net_pnl
        FROM tmp_global_edge_forensic_v1
        GROUP BY 1
        ORDER BY trades DESC, day
        """
    )

    by_contract = all_rows(
        cur,
        """
        SELECT contract, count(*)::int AS trades
        FROM tmp_global_edge_forensic_v1
        GROUP BY contract
        ORDER BY trades DESC, contract
        """
    )

    by_entry_regime = all_rows(
        cur,
        """
        SELECT entry_regime AS regime, count(*)::int AS trades
        FROM tmp_global_edge_forensic_v1
        GROUP BY entry_regime
        ORDER BY trades DESC, regime
        """
    )

    top5 = one(
        cur,
        """
        SELECT coalesce(sum(net_pnl),0) AS top5_pnl
        FROM (
            SELECT net_pnl
            FROM tmp_global_edge_forensic_v1
            ORDER BY net_pnl DESC
            LIMIT 5
        ) q
        """
    )

    replay_trades_ok = int(replay["trades"]) == int(scorecard["trades"])
    replay_wins_ok = int(replay["wins"]) == int(scorecard["wins"])
    replay_losses_ok = int(replay["losses"]) == int(scorecard["losses"])
    replay_net_ok = abs(d(replay["net_pnl"]) - d(scorecard["net_pnl"])) < Decimal("0.0001")

    gross_loss = d(replay["gross_loss"])
    pf = None if gross_loss == 0 else d(replay["gross_profit"]) / gross_loss

    replay_status = "PASS" if all([replay_trades_ok, replay_wins_ok, replay_losses_ok, replay_net_ok]) else "FAIL"

    total_net = d(replay["net_pnl"])
    top5_share = Decimal("0") if total_net == 0 else (d(top5["top5_pnl"]) / total_net * Decimal("100"))

    max_day_trades = max((int(r["trades"]) for r in by_day), default=0)
    max_day_share = Decimal("0") if int(replay["trades"]) == 0 else Decimal(max_day_trades) / Decimal(int(replay["trades"])) * Decimal("100")

    forensic_flags: list[str] = []
    if max_day_share >= Decimal("70"):
        forensic_flags.append("DAY_TRADE_CONCENTRATION_HIGH")
    if top5_share >= Decimal("75"):
        forensic_flags.append("TOP5_PNL_CONCENTRATION_HIGH")
    if any(r["regime"] == "unknown" and int(r["trades"]) == int(replay["trades"]) for r in by_entry_regime):
        forensic_flags.append("REGIME_UNKNOWN_FULL_SAMPLE")
    if any(r["contract"] == "NULL" and int(r["trades"]) > 0 for r in by_contract):
        forensic_flags.append("CONTRACT_PARTIALLY_MISSING")

    forensic_status = "PASS_WITH_DATA_QUALITY_FLAGS" if forensic_flags else "PASS"
    robustness_status = "FAIL" if any(f in forensic_flags for f in ["DAY_TRADE_CONCENTRATION_HIGH", "TOP5_PNL_CONCENTRATION_HIGH"]) else "PASS"

    if replay_status != "PASS":
        recommendation = "REJECT_REPLAY_MISMATCH"
        overall = "FALSE_POSITIVE_OR_DATA_MISMATCH"
    elif robustness_status == "FAIL":
        recommendation = "REJECT_ROBUSTNESS_FAIL"
        overall = "FRAGILE_EDGE"
    else:
        recommendation = "PROMOTE_TO_OOS_VALIDATION"
        overall = "REPRODUCIBLE_RESEARCH_EDGE"

    return {
        "candidate_id": candidate["candidate_id"],
        "candidate_status_before": candidate["status"],
        "candidate_payload_robustness_before": (candidate.get("payload") or {}).get("robustness") if isinstance(candidate.get("payload"), dict) else None,
        "symbol": scorecard["symbol"],
        "strategy": scorecard["strategy"],
        "timeframe": scorecard["timeframe"],
        "instrument_signature": candidate["instrument_signature"],
        "fx_signature": candidate["fx_signature"],
        "energy_signature": candidate["energy_signature"],
        "scorecard_id": scorecard["id"],
        "scorecard_run_id": scorecard["run_id"],
        "scorecard_trades": int(scorecard["trades"]),
        "scorecard_wins": int(scorecard["wins"]),
        "scorecard_losses": int(scorecard["losses"]),
        "scorecard_net_pnl": str(scorecard["net_pnl"]),
        "scorecard_profit_factor": str(scorecard["profit_factor"]),
        "replay": {
            "trades": int(replay["trades"]),
            "wins": int(replay["wins"]),
            "losses": int(replay["losses"]),
            "net_pnl": str(replay["net_pnl"]),
            "commission": str(replay["commission"]),
            "profit_factor": str(pf) if pf is not None else None,
            "expectancy": str(replay["expectancy"]),
        },
        "by_day": [{k: str(v) for k, v in r.items()} for r in by_day],
        "by_contract": [{k: str(v) for k, v in r.items()} for r in by_contract],
        "by_entry_regime": [{k: str(v) for k, v in r.items()} for r in by_entry_regime],
        "top5_win_share_pct": str(round(top5_share, 6)),
        "max_day_share_pct": str(round(max_day_share, 6)),
        "forensic_flags": forensic_flags,
        "replay_status": replay_status,
        "forensic_status": forensic_status,
        "robustness_status": robustness_status,
        "recommendation": recommendation,
        "overall_verdict": overall,
        "micro_live_allowed": False,
        "runtime_changed": False,
    }


def save_report(cur, report: dict[str, Any]) -> None:
    ensure_report_table(cur)
    cur.execute(
        """
        INSERT INTO research.global_edge_forensic_reports_v1 (
            candidate_id,
            symbol,
            strategy,
            timeframe,
            replay_status,
            forensic_status,
            robustness_status,
            recommendation,
            micro_live_allowed,
            runtime_changed,
            payload
        )
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,false,false,%s::jsonb)
        """,
        (
            report["candidate_id"],
            report["symbol"],
            report["strategy"],
            report["timeframe"],
            report["replay_status"],
            report["forensic_status"],
            report["robustness_status"],
            report["recommendation"],
            json.dumps(report, ensure_ascii=False),
        ),
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--candidate-id", default="MSC-000001")
    parser.add_argument("--save", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    with psycopg2.connect(db_url()) as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            candidate = load_candidate(cur, args.candidate_id)
            scorecard = load_scorecard(cur, candidate)
            build_temp_edge_dataset(cur, candidate, scorecard)
            report = compute_report(cur, candidate, scorecard)

            if args.save:
                save_report(cur, report)
                conn.commit()
            else:
                conn.rollback()

    print("=== GLOBAL_EDGE_FORENSIC_ENGINE_V1 ===")
    print(f"mode={'save' if args.save else 'dry_run'}")
    print(f"candidate_id={report['candidate_id']}")
    print(f"symbol={report['symbol']}")
    print(f"strategy={report['strategy']}")
    print(f"timeframe={report['timeframe']}")
    print(f"scorecard_trades={report['scorecard_trades']}")
    print(f"replay_trades={report['replay']['trades']}")
    print(f"scorecard_net_pnl={report['scorecard_net_pnl']}")
    print(f"replay_net_pnl={report['replay']['net_pnl']}")
    print(f"top5_win_share_pct={report['top5_win_share_pct']}")
    print(f"max_day_share_pct={report['max_day_share_pct']}")
    print(f"forensic_flags={','.join(report['forensic_flags']) if report['forensic_flags'] else 'NONE'}")
    print(f"replay_status={report['replay_status']}")
    print(f"forensic_status={report['forensic_status']}")
    print(f"robustness_status={report['robustness_status']}")
    print(f"recommendation={report['recommendation']}")
    print(f"overall_verdict={report['overall_verdict']}")
    print("runtime_changed=0")
    print("micro_live_allowed=0")
    print(f"VERDICT={report['overall_verdict']}")

    return 0 if report["replay_status"] == "PASS" else 2


if __name__ == "__main__":
    sys.exit(main())
