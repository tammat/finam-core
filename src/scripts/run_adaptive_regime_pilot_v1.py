from __future__ import annotations

import os
import statistics
import uuid
from collections import defaultdict
from decimal import Decimal

import psycopg2
import psycopg2.extras

DB = os.getenv("DATABASE_URL", "postgresql:///finam_core")
SOURCE_VERSION = "ADAPTIVE_REGIME_PILOT_V2"
NAMESPACE = uuid.UUID("878acfc2-a4ca-4761-a1eb-986a74027697")
LOOKBACK_DAYS = int(os.getenv("ADAPTIVE_PILOT_SHADOW_LOOKBACK_DAYS", "5"))
SHADOW_MINIMUM = int(os.getenv("ADAPTIVE_PILOT_SHADOW_MINIMUM", "5"))
PAPER_CONFIRM_MINIMUM = int(os.getenv("ADAPTIVE_PILOT_CONFIRM_MINIMUM", "12"))


def dec(value) -> Decimal:
    return Decimal(str(value or 0))


def performance(values: list[Decimal]) -> dict:
    profit = sum((v for v in values if v > 0), Decimal(0))
    loss = abs(sum((v for v in values if v < 0), Decimal(0)))
    pf = profit / loss if loss else (Decimal("999") if profit else None)
    cumulative = peak = drawdown = Decimal(0)
    for value in values:
        cumulative += value
        peak = max(peak, cumulative)
        drawdown = max(drawdown, peak - cumulative)
    scale = Decimal(str(statistics.median([float(abs(v)) for v in values]))) if values else Decimal(0)
    return {
        "observations": len(values), "wins": sum(value > 0 for value in values),
        "profit_factor": pf,
        "expectancy": sum(values, Decimal(0)) / len(values) if values else Decimal(0),
        "max_drawdown": drawdown, "loss_scale": scale,
    }


def shadow_decision(metric: dict, placebo_metric: dict, placebo_coverage: Decimal) -> tuple[str, str]:
    if metric["observations"] < SHADOW_MINIMUM:
        return "SHADOW_COLLECTING", "WAITING_FIVE_FRESH_REGIME_OBSERVATIONS"
    if metric["expectancy"] <= 0:
        return "SHADOW_COLLECTING", "SHADOW_EXPECTANCY_NOT_POSITIVE"
    if metric["profit_factor"] is None or metric["profit_factor"] < Decimal("1.20"):
        return "SHADOW_COLLECTING", "SHADOW_PROFIT_FACTOR_BELOW_1_20"
    if metric["wins"] < 3:
        return "SHADOW_COLLECTING", "SHADOW_TOO_FEW_POSITIVE_OUTCOMES"
    if metric["max_drawdown"] > max(metric["loss_scale"] * 2, Decimal("0.000001")):
        return "SHADOW_COLLECTING", "SHADOW_DRAWDOWN_ABOVE_TWO_R"
    if placebo_coverage < Decimal("0.80"):
        return "SHADOW_COLLECTING", "PLACEBO_COVERAGE_BELOW_80_PERCENT"
    if metric["expectancy"] <= placebo_metric["expectancy"]:
        return "SHADOW_COLLECTING", "SHADOW_DOES_NOT_BEAT_MATCHED_PLACEBO"
    return "PILOT_ACTIVE", "FRESH_REGIME_SHADOW_BEATS_PLACEBO"


def paper_decision(values: list[Decimal], loss_scale: Decimal) -> tuple[str, str]:
    metric = performance(values)
    if len(values) >= 2 and values[-1] < 0 and values[-2] < 0:
        return "ROLLED_BACK", "TWO_CONSECUTIVE_PILOT_LOSSES"
    if sum(values, Decimal(0)) <= -(max(loss_scale, Decimal("0.000001")) * 2):
        return "ROLLED_BACK", "PILOT_DRAWDOWN_REACHED_TWO_R"
    if len(values) >= 5 and (
        metric["expectancy"] <= 0 or metric["profit_factor"] is None
        or metric["profit_factor"] < Decimal("1.05")
    ):
        return "ROLLED_BACK", "FIVE_TRADE_PILOT_HAS_NO_NET_EDGE"
    if len(values) >= PAPER_CONFIRM_MINIMUM:
        if metric["expectancy"] > 0 and metric["profit_factor"] is not None and metric["profit_factor"] >= Decimal("1.15"):
            return "PAPER_CONFIRMED", "SEQUENTIAL_PAPER_EDGE_CONFIRMED"
        return "ROLLED_BACK", "PAPER_CONFIRMATION_GATE_FAILED"
    return "PILOT_ACTIVE", "PILOT_COLLECTING_SEQUENTIAL_EVIDENCE"


def main() -> int:
    assessed = activated = rolled_back = confirmed = 0
    with psycopg2.connect(DB) as connection:
      with connection.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
        cur.execute("SELECT pg_try_advisory_xact_lock(184003) locked")
        if not cur.fetchone()["locked"]:
            print("VERDICT=ADAPTIVE_REGIME_PILOT_ALREADY_RUNNING")
            return 0
        cur.execute("""SELECT * FROM analytics.entry_exit_signal_shadow_pair_v2
            WHERE shadow_entered AND shadow_net_r IS NOT NULL
              AND label_end_ts>=clock_timestamp()-(%s*interval '1 day')
            ORDER BY label_end_ts,source_signal_id,candidate_code""", (LOOKBACK_DAYS,))
        groups = defaultdict(list)
        for row in cur.fetchall():
            regime = str((row["entry_context"] or {}).get("regime") or "UNKNOWN")
            key = (row["symbol_code"], row["side_code"], row["strategy_code"],
                   row["candidate_code"], regime)
            groups[key].append(row)
        for (symbol, side, strategy, code, regime), raw_rows in groups.items():
            # At most one observation for a 15-minute market event.
            independent = {}
            for row in raw_rows:
                ts = row["label_start_ts"]
                bucket = ts.replace(minute=(ts.minute // 15) * 15, second=0, microsecond=0)
                independent[bucket] = row
            rows = sorted(independent.values(), key=lambda row: row["label_end_ts"])
            values = [dec(row["shadow_net_r"]) for row in rows]
            placebo_rows = [row for row in rows if row["placebo_net_r"] is not None]
            placebo_values = [dec(row["placebo_net_r"]) for row in placebo_rows]
            metric, placebo_metric = performance(values), performance(placebo_values)
            placebo_coverage = Decimal(len(placebo_rows)) / len(rows) if rows else Decimal(0)
            status, reason = shadow_decision(metric, placebo_metric, placebo_coverage)
            identity = f"{symbol}|{side}|{strategy}|{code}|{regime}"
            pilot_id = uuid.uuid5(NAMESPACE, identity)
            cur.execute("""SELECT * FROM analytics.adaptive_regime_paper_pilot_v1
                WHERE pilot_id=%s""", (str(pilot_id),))
            existing = cur.fetchone()
            activated_at = existing["activated_at"] if existing else None
            if existing and existing["status_code"] in {"PILOT_ACTIVE", "PAPER_CONFIRMED", "ROLLED_BACK"}:
                status = existing["status_code"]
            if status == "PILOT_ACTIVE" and activated_at is None:
                symbol_group = (
                    "BR" if strategy == "BR_CONSERVATIVE_BREAKOUT" else
                    "NG" if strategy == "NG_CONSERVATIVE_BREAKOUT_M1" else
                    "CNY" if strategy == "CNY_REGIME_FUTURES" else
                    symbol.split("@", 1)[0]
                )
                cur.execute("""SELECT has_table_privilege(
                    current_user,'analytics.entry_exit_runtime_profile_v1','INSERT,UPDATE'
                ) allowed""")
                can_activate = bool(cur.fetchone()["allowed"])
                cur.execute("""SELECT profile_id,candidate_code FROM
                    analytics.entry_exit_runtime_profile_v1
                    WHERE strategy_code=%s AND symbol_group=%s AND side_code=%s
                      AND execution_mode='paper' AND status='ACTIVE'""",
                    (strategy, symbol_group, side))
                active_profile = cur.fetchone()
                if active_profile and active_profile["candidate_code"] != code:
                    status, reason = "SHADOW_COLLECTING", "CURRENT_PAPER_PROFILE_OCCUPIES_FAMILY"
                elif not active_profile and not can_activate:
                    status, reason = "SHADOW_COLLECTING", "RUNTIME_PROFILE_OWNER_GRANT_REQUIRED"
                else:
                    if not active_profile:
                        selected = rows[-1]
                        cur.execute("""INSERT INTO analytics.entry_exit_runtime_profile_v1(
                            strategy_code,symbol_group,side_code,candidate_code,execution_mode,
                            status,entry_mode,stop_atr,take_atr,trail_after_r,trail_atr,
                            source_metrics,activated_by)
                          VALUES(%s,%s,%s,%s,'paper','ACTIVE',%s,%s,%s,NULL,NULL,%s,'ADAPTIVE_REGIME_PILOT_V2')""",
                          (strategy, symbol_group, side, code, selected["entry_mode"],
                           selected["stop_atr"], selected["take_atr"],
                           psycopg2.extras.Json({
                               "pilot_id": str(pilot_id), "regime": regime,
                               "shadow_expectancy_r": str(metric["expectancy"]),
                               "placebo_expectancy_r": str(placebo_metric["expectancy"]),
                           })))
                    activated_at = rows[-1]["label_end_ts"]
                    activated += 1
            paper_values = []
            if activated_at and status in {"PILOT_ACTIVE", "PAPER_CONFIRMED"}:
                cur.execute("""SELECT coalesce(
                        nullif(payload->>'net_pnl_r','')::numeric,
                        nullif(payload->'context'->>'net_pnl_r','')::numeric
                      ) net_r
                    FROM public.closed_trades
                    WHERE symbol=%s AND upper(side)=%s AND strategy=%s
                      AND coalesce(trade_source,'')='paper' AND entry_ts>=%s
                      AND coalesce(
                        payload->'features'->>'entry_exit_candidate_code',
                        payload->'context'->>'entry_exit_candidate_code',''
                      )=%s
                    ORDER BY exit_ts,id""", (symbol, side, strategy, activated_at, code))
                paper_values = [dec(row["net_r"]) for row in cur.fetchall()
                                if row["net_r"] is not None]
                status, reason = paper_decision(paper_values, metric["loss_scale"])
                rolled_back += status == "ROLLED_BACK"
                confirmed += status == "PAPER_CONFIRMED"
                if status == "ROLLED_BACK":
                    cur.execute("""UPDATE analytics.entry_exit_runtime_profile_v1
                        SET status='ROLLED_BACK',deactivated_at=clock_timestamp()
                        WHERE strategy_code=%s AND symbol_group=%s AND side_code=%s
                          AND candidate_code=%s AND status='ACTIVE'
                          AND activated_by='ADAPTIVE_REGIME_PILOT_V2'""",
                        (strategy, symbol_group, side, code))
            paper_metric = performance(paper_values)
            evidence = {
                "lookback_days": LOOKBACK_DAYS, "regime": regime,
                "independence_bucket_minutes": 15,
                "shadow_r": {key: str(value) for key, value in metric.items()},
                "placebo_r": {key: str(value) for key, value in placebo_metric.items()},
                "placebo_coverage": str(placebo_coverage), "decision_reason": reason,
                "paper_r": {key: str(value) for key, value in paper_metric.items()},
                "real_trading_allowed": False,
            }
            cur.execute("""INSERT INTO analytics.adaptive_regime_paper_pilot_v1(
                pilot_id,shadow_candidate_id,symbol,side_code,strategy_code,regime_code,
                candidate_code,entry_mode,stop_atr,take_atr,status_code,
                shadow_observations,shadow_profit_factor,
                shadow_expectancy,shadow_max_drawdown,paper_observations,paper_profit_factor,
                paper_expectancy,rollback_reason,activated_at,evidence,source_version)
              VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
              ON CONFLICT(pilot_id) DO UPDATE SET
                status_code=EXCLUDED.status_code,shadow_observations=EXCLUDED.shadow_observations,
                shadow_profit_factor=EXCLUDED.shadow_profit_factor,
                shadow_expectancy=EXCLUDED.shadow_expectancy,
                shadow_max_drawdown=EXCLUDED.shadow_max_drawdown,
                paper_observations=EXCLUDED.paper_observations,
                paper_profit_factor=EXCLUDED.paper_profit_factor,
                paper_expectancy=EXCLUDED.paper_expectancy,
                rollback_reason=EXCLUDED.rollback_reason,
                activated_at=coalesce(analytics.adaptive_regime_paper_pilot_v1.activated_at,
                                      EXCLUDED.activated_at),
                evaluated_at=clock_timestamp(),evidence=EXCLUDED.evidence,
                source_version=EXCLUDED.source_version""",
              (str(pilot_id), str(pilot_id), symbol, side, strategy, regime, code,
               rows[-1]["entry_mode"], rows[-1]["stop_atr"], rows[-1]["take_atr"], status,
               metric["observations"], metric["profit_factor"], metric["expectancy"],
               metric["max_drawdown"], paper_metric["observations"],
               paper_metric["profit_factor"], paper_metric["expectancy"],
               reason if status == "ROLLED_BACK" else None, activated_at,
               psycopg2.extras.Json(evidence), SOURCE_VERSION))
            assessed += 1
    print(f"candidates_assessed={assessed}")
    print(f"pilots_activated={activated}")
    print(f"pilots_rolled_back={rolled_back}")
    print(f"paper_confirmed={confirmed}")
    print("real_trading_allowed=0")
    print("VERDICT=ADAPTIVE_REGIME_PILOT_V2_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
