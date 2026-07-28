from __future__ import annotations

import hashlib
import os
from collections import defaultdict

import psycopg2
import psycopg2.extras


DB = os.getenv("DATABASE_URL", "postgresql:///finam_core")
TARGET = 80
EARLY_STOP_MIN = int(os.getenv("HIERARCHY_EARLY_STOP_MIN_TRADES", "20"))
EARLY_STOP_PF = float(os.getenv("HIERARCHY_EARLY_STOP_MAX_PF", "0.85"))


def norm(value: object, fallback: str = "UNKNOWN") -> str:
    text = str(value or "").strip().upper().replace(" ", "_")
    return text or fallback


def compatible_regime(value: object, mapping: dict[tuple[str, str], str]) -> str:
    raw = norm(value)
    return mapping.get(("REGIME", raw), raw)


def compatible_session(value: object, mapping: dict[tuple[str, str], str]) -> str:
    raw = norm(value)
    aliases = {
        "ОСНОВНАЯ_СЕССИЯ": "MAIN", "MAIN_SESSION": "MAIN",
        "ВЕЧЕРНЯЯ_СЕССИЯ": "EVENING", "EVENING_SESSION": "EVENING",
        "ВНЕ_ОСНОВНОЙ_СЕССИИ": "OFF_MAIN", "OUTSIDE_MAIN_SESSION": "OFF_MAIN",
    }
    raw = aliases.get(raw, raw)
    return mapping.get(("SESSION", raw), raw)


def evidence_decision(*, level: str, cohort: str, trades: int, expectancy: float,
                      profit_factor: float, cost_ratio: float) -> tuple[str, str]:
    if trades == 0:
        return "NO_EVIDENCE", "NO_CLOSED_TRADES"
    if trades >= EARLY_STOP_MIN and expectancy < 0 and profit_factor < EARLY_STOP_PF:
        return "EARLY_STOP", "NEGATIVE_EXPECTANCY_AND_PF"
    if trades >= EARLY_STOP_MIN and cost_ratio >= 0.75:
        return "EARLY_STOP", "COST_DOMINATED"
    # Общие и совместимые уровни дают только направление поиска, но никогда PASS.
    if level != "EXACT_CONTEXT" or cohort != "FRESH_V5_CONFIRM":
        return "DISCOVERY_ONLY", "LOWER_HIERARCHY_GUIDES_PRIORITY_ONLY"
    if trades < TARGET:
        return "COLLECT", "EXACT_V5_SAMPLE_BELOW_80"
    if expectancy <= 0 or profit_factor < 1.15:
        return "EARLY_STOP", "EXACT_V5_ECONOMICS_FAILED"
    return "READY_FOR_OOS", "EXACT_V5_SAMPLE_AND_ECONOMICS_READY"


def priority_score(*, trades: int, expectancy: float, profit_factor: float,
                   archive_weight: float = 0.0) -> float:
    # Предпочитаем положительные, близкие к цели, но ещё недозаполненные ветки.
    fill = min(trades, TARGET) / TARGET
    deficit_focus = 1.0 - abs(0.75 - fill)
    economics = max(-2.0, min(3.0, expectancy)) + min(2.0, profit_factor) * 2
    return round(100 * deficit_focus + 25 * economics + archive_weight, 6)


def _aggregate(rows: list[dict], key_fields: tuple[str, ...]) -> list[dict]:
    groups: dict[tuple, list[dict]] = defaultdict(list)
    for row in rows:
        groups[tuple(row[field] for field in key_fields)].append(row)
    result = []
    for key, items in groups.items():
        trades = sum(int(item["closed_trades"]) for item in items)
        gross_profit = sum(float(item["gross_profit"]) for item in items)
        gross_loss = sum(float(item["gross_loss"]) for item in items)
        net_pnl = sum(float(item["net_pnl"]) for item in items)
        commission = sum(float(item["commission"]) for item in items)
        gross_abs = sum(float(item["gross_abs"]) for item in items)
        result.append({
            **dict(zip(key_fields, key)), "closed_trades": trades, "net_pnl": net_pnl,
            "expectancy": net_pnl / trades if trades else 0.0,
            "profit_factor": 999.0 if gross_loss == 0 and gross_profit > 0 else
                (gross_profit / gross_loss if gross_loss else 0.0),
            "cost_ratio": commission / gross_abs if gross_abs else 0.0,
        })
    return result


def main() -> int:
    with psycopg2.connect(DB) as connection:
        with connection.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cursor:
            cursor.execute("SELECT pg_try_advisory_lock(200001) locked")
            if not cursor.fetchone()["locked"]:
                print("VERDICT=HIERARCHICAL_EVIDENCE_ROUTER_ALREADY_RUNNING")
                return 0
            cursor.execute("""SELECT dimension_code,raw_code,compatible_group
                FROM analytics.evidence_compatibility_group_v1 WHERE enabled""")
            mapping = {(r["dimension_code"], r["raw_code"]): r["compatible_group"] for r in cursor.fetchall()}
            cursor.execute("""
                SELECT CASE WHEN portfolio_scope LIKE 'FRESH_V5%%' THEN 'FRESH_V5_CONFIRM'
                            ELSE 'FRESH_V3_BASE' END cohort_code,
                       symbol,coalesce(nullif(strategy,''),'UNKNOWN') strategy_code,
                       coalesce(nullif(side,''),'UNKNOWN') side_code,
                       coalesce(nullif(payload->'context'->>'entry_session_msk',''),'UNKNOWN') session_code,
                       coalesce(nullif(payload->'context'->>'entry_regime',''),nullif(regime,''),'UNKNOWN') regime_code,
                       coalesce(nullif(payload->'context'->>'exit_rule',''),'UNKNOWN') exit_rule,
                       count(*)::int closed_trades,
                       coalesce(sum(gross_pnl) FILTER(WHERE gross_pnl>0),0) gross_profit,
                       abs(coalesce(sum(gross_pnl) FILTER(WHERE gross_pnl<0),0)) gross_loss,
                       coalesce(sum(net_pnl),0) net_pnl,coalesce(sum(commission),0) commission,
                       coalesce(sum(abs(gross_pnl)),0) gross_abs
                FROM public.closed_trades
                WHERE portfolio_scope IN ('FRESH_V3_EQUITY','FRESH_V3_FUTURES',
                    'FRESH_V5_CONFIRMED_EQUITY','FRESH_V5_CONFIRMED_FUTURES')
                GROUP BY 1,2,3,4,5,6,7
            """)
            exact = [dict(row) for row in cursor.fetchall()]
            for row in exact:
                row["session_group"] = compatible_session(row["session_code"], mapping)
                row["regime_group"] = compatible_regime(row["regime_code"], mapping)

            levels = (
                ("STRATEGY", ("cohort_code", "strategy_code")),
                ("INSTRUMENT_SIDE", ("cohort_code", "strategy_code", "symbol", "side_code")),
                ("COMPATIBLE_CONTEXT", ("cohort_code", "strategy_code", "symbol", "side_code", "session_group", "regime_group", "exit_rule")),
                ("EXACT_CONTEXT", ("cohort_code", "strategy_code", "symbol", "side_code", "session_code", "regime_code", "exit_rule")),
            )
            written = 0
            cursor.execute("DELETE FROM analytics.hierarchical_evidence_v1")
            for level, fields in levels:
                for row in _aggregate(exact, fields):
                    cohort = row["cohort_code"]
                    decision, reason = evidence_decision(
                        level=level, cohort=cohort, trades=row["closed_trades"],
                        expectancy=row["expectancy"], profit_factor=row["profit_factor"],
                        cost_ratio=row["cost_ratio"],
                    )
                    values = {
                        "strategy_code": row.get("strategy_code", "*"), "symbol_code": row.get("symbol", "*"),
                        "side_code": row.get("side_code", "*"),
                        "session_code": row.get("session_code", row.get("session_group", "*")),
                        "regime_code": row.get("regime_code", row.get("regime_group", "*")),
                        "exit_rule": row.get("exit_rule", "*"),
                    }
                    raw_key = "|".join([cohort, level, *(str(values[k]) for k in values)])
                    key = hashlib.sha256(raw_key.encode()).hexdigest()
                    score = priority_score(trades=row["closed_trades"],expectancy=row["expectancy"],
                                           profit_factor=row["profit_factor"])
                    cursor.execute("""INSERT INTO analytics.hierarchical_evidence_v1(
                        evidence_key,cohort_code,level_code,strategy_code,symbol_code,side_code,
                        session_code,regime_code,exit_rule,closed_trades,target_trades,net_pnl,
                        expectancy,profit_factor,cost_ratio,priority_score,decision_code,reason_code
                    ) VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,80,%s,%s,%s,%s,%s,%s,%s)""",
                    (key,cohort,level,values["strategy_code"],values["symbol_code"],values["side_code"],
                     values["session_code"],values["regime_code"],values["exit_rule"],row["closed_trades"],
                     row["net_pnl"],row["expectancy"],row["profit_factor"],row["cost_ratio"],score,decision,reason))
                    written += 1
    print(f"evidence_rows={written}")
    print("VERDICT=HIERARCHICAL_EVIDENCE_ROUTER_V1_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
