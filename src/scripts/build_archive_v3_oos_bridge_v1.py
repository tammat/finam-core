from __future__ import annotations

import hashlib
import json
import os
import re
import uuid

import psycopg2
import psycopg2.extras


DB = os.getenv("DATABASE_URL", "postgresql:///finam_core")
SOURCE = "ARCHIVE_V3_OOS_BRIDGE_V1"
TARGET = int(os.getenv("FRESH_V3_OOS_MIN_TRADES", "80"))
MIN_PF = float(os.getenv("FRESH_V3_OOS_MIN_PROFIT_FACTOR", "1.15"))
NAMESPACE = uuid.UUID("e75c643f-265c-493c-8ac2-579930bc06cf")


def norm(value: object) -> str:
    return re.sub(r"[^A-Z0-9]+", "_", str(value or "").strip().upper()).strip("_")


def root_symbol(value: object) -> str:
    raw = norm(str(value or "").split("@")[0])
    if "@RTSX" in str(value or "").upper():
        match = re.match(r"^([A-Z]+)[A-Z]\d+$", raw)
        return match.group(1) if match else raw
    return raw


def linkage_key(row: dict) -> str:
    parts = (
        row["scope_code"], root_symbol(row["symbol"]), norm(row["strategy_code"]),
        norm(row["side_code"]), norm(row["session_code"]), norm(row["regime_code"]),
        norm(row["exit_rule"]),
    )
    return hashlib.sha256("|".join(parts).encode()).hexdigest()


def archive_match(link: dict, hypotheses: list[dict]) -> tuple[dict | None, str]:
    candidates: list[tuple[int, float, dict]] = []
    for hypothesis in hypotheses:
        if norm(hypothesis["strategy_code"]) != norm(link["strategy_code"]):
            continue
        score = 25
        exact = True
        comparisons = (
            (root_symbol(hypothesis.get("symbol")), root_symbol(link["symbol"]), 25),
            (norm(hypothesis.get("side_code")), norm(link["side_code"]), 20),
            (norm(hypothesis.get("session_code")), norm(link["session_code"]), 10),
            (norm(hypothesis.get("regime_code")), norm(link["regime_code"]), 10),
            (norm(hypothesis.get("holding_code")), norm(link["exit_rule"]), 10),
        )
        for archived, fresh, weight in comparisons:
            if archived in {"", "UNKNOWN", "UNSPECIFIED"}:
                exact = False
            elif archived == fresh:
                score += weight
            else:
                exact = False
        candidates.append((score, float(hypothesis.get("priority_score") or 0), hypothesis))
        if exact:
            candidates[-1] = (100, candidates[-1][1], hypothesis)
    if not candidates:
        return None, "V3_ONLY"
    score, _, selected = max(candidates, key=lambda item: (item[0], item[1]))
    return selected, "EXACT" if score == 100 else "RELATED"


def _fresh_groups(cursor) -> list[dict]:
    cursor.execute("""
        SELECT coalesce(payload->'context'->>'portfolio_scope',payload->'context'->>'cohort','') scope_code,
               symbol,coalesce(nullif(strategy,''),'UNKNOWN') strategy_code,
               coalesce(nullif(side,''),'UNKNOWN') side_code,
               coalesce(nullif(payload->'context'->>'entry_session_msk',''),'UNKNOWN') session_code,
               coalesce(nullif(payload->'context'->>'entry_regime',''),nullif(regime,''),'UNKNOWN') regime_code,
               coalesce(nullif(payload->'context'->>'exit_rule',''),'UNSPECIFIED') exit_rule,
               count(*)::int v3_closed_trades,
               count(*) FILTER (WHERE nullif(symbol,'') IS NOT NULL AND nullif(strategy,'') IS NOT NULL
                 AND nullif(side,'') IS NOT NULL AND nullif(payload->'context'->>'entry_session_msk','') IS NOT NULL
                 AND coalesce(nullif(payload->'context'->>'entry_regime',''),nullif(regime,'')) IS NOT NULL
                 AND nullif(payload->'context'->>'exit_rule','') IS NOT NULL)::int v3_context_complete,
               coalesce(sum(net_pnl) FILTER(WHERE net_pnl>0),0) gross_profit,
               abs(coalesce(sum(net_pnl) FILTER(WHERE net_pnl<0),0)) gross_loss,
               coalesce(sum(net_pnl),0) v3_net_pnl,
               coalesce(avg(net_pnl),0) v3_expectancy
        FROM analytics.closed_trades_active_v3
        WHERE coalesce(payload->'context'->>'portfolio_scope',payload->'context'->>'cohort','')
              IN ('FRESH_V3_EQUITY','FRESH_V3_FUTURES')
        GROUP BY 1,2,3,4,5,6,7
    """)
    rows = [dict(row) for row in cursor.fetchall()]
    for row in rows:
        loss = float(row.pop("gross_loss") or 0)
        profit = float(row.pop("gross_profit") or 0)
        # PF is mathematically undefined until at least one loss is observed.
        # Never encode that state as the artificial numeric sentinel 999.
        row["v3_profit_factor"] = profit / loss if loss else None
    return rows


def main() -> int:
    with psycopg2.connect(DB) as connection:
        with connection.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cursor:
            cursor.execute("SELECT pg_try_advisory_lock(193001) locked")
            if not cursor.fetchone()["locked"]:
                print("VERDICT=ARCHIVE_V3_OOS_BRIDGE_ALREADY_RUNNING")
                return 0
            cursor.execute("SELECT * FROM analytics.trade_outcome_hypothesis_v1 ORDER BY priority_score DESC")
            hypotheses = [dict(row) for row in cursor.fetchall()]
            cursor.execute("SELECT run_id FROM analytics.trade_outcome_pattern_run_v1 ORDER BY created_at DESC LIMIT 1")
            source = cursor.fetchone()
            groups = _fresh_groups(cursor)
            cursor.execute("""SELECT portfolio_scope,symbol,strategy_code,side_code,reason_code
                              FROM analytics.v3_link_quarantine_v1 WHERE enabled""")
            quarantines = [dict(row) for row in cursor.fetchall()]
            counts: dict[str, int] = {}
            for link in groups:
                key = linkage_key(link)
                archived, match_code = archive_match(link, hypotheses)
                trades = int(link["v3_closed_trades"])
                complete = int(link["v3_context_complete"])
                expectancy = float(link["v3_expectancy"] or 0)
                profit_factor = float(link["v3_profit_factor"] or 0)
                quarantine = next((row for row in quarantines if
                    row["portfolio_scope"] == link["scope_code"] and row["symbol"] == link["symbol"] and
                    row["strategy_code"] == link["strategy_code"] and
                    row["side_code"] in ("*", link["side_code"])), None)
                if quarantine:
                    readiness, reason = "QUARANTINED", str(quarantine["reason_code"])
                elif trades < TARGET:
                    readiness, reason = "WAITING_SAMPLE", "FRESH_V3_SAMPLE_BELOW_TARGET"
                elif complete < trades:
                    readiness, reason = "WAITING_CONTEXT", "FRESH_V3_CONTEXT_INCOMPLETE"
                elif expectancy <= 0 or profit_factor < MIN_PF:
                    readiness, reason = "FAILED_FRESH_EVIDENCE", "FRESH_V3_EXPECTANCY_OR_PF_FAILED"
                else:
                    readiness, reason = "READY_FOR_OOS", "FRESH_V3_CONFIRMED"
                oos_hypothesis_id = None
                if readiness == "READY_FOR_OOS" and source:
                    oos_hypothesis_id = uuid.uuid5(NAMESPACE, key)
                    hypothesis_key = "FRESH_V3|" + key
                    evidence = {
                        "source": SOURCE, "archive_match_code": match_code,
                        "archive_hypothesis_id": str(archived["hypothesis_id"]) if archived else None,
                        "portfolio_scope": link["scope_code"], "minimum_trades": TARGET,
                        "minimum_profit_factor": MIN_PF, "promotion_allowed": False,
                    }
                    cursor.execute("""INSERT INTO analytics.trade_outcome_hypothesis_v1(
                        hypothesis_id,hypothesis_key,source_run_id,hypothesis_type,strategy_code,side_code,
                        session_code,holding_code,trades,context_complete_trades,profit_factor,expectancy,
                        priority_score,lifecycle_state,recommendation_code,evidence,regime_code,symbol
                    ) VALUES(%s,%s,%s,'FILTER_OOS_CANDIDATE',%s,%s,%s,%s,%s,%s,%s,%s,%s,'READY_FOR_OOS',
                             'BUILD_ISOLATED_OOS_COHORT',%s,%s,%s)
                    ON CONFLICT(hypothesis_key) DO UPDATE SET trades=excluded.trades,
                        context_complete_trades=excluded.context_complete_trades,
                        profit_factor=excluded.profit_factor,expectancy=excluded.expectancy,
                        lifecycle_state='READY_FOR_OOS',evidence=excluded.evidence,updated_at=clock_timestamp()
                    RETURNING hypothesis_id""",
                        (str(oos_hypothesis_id),hypothesis_key,str(source["run_id"]),link["strategy_code"],
                         link["side_code"],link["session_code"],link["exit_rule"],trades,complete,
                         profit_factor,expectancy,float(archived.get("priority_score") or 0) if archived else expectancy,
                         psycopg2.extras.Json(evidence),link["regime_code"],root_symbol(link["symbol"])))
                    oos_hypothesis_id = cursor.fetchone()["hypothesis_id"]
                    cursor.execute("""INSERT INTO analytics.trade_outcome_oos_admission_v1(
                        admission_id,hypothesis_id,symbol,fresh_closed_trades,context_complete_trades,
                        microstructure_coverage_ratio,required_microstructure_coverage,status_code,reason_code,oos_request
                    ) VALUES(%s,%s,%s,%s,%s,0,0,'QUEUED','READY_FOR_ISOLATED_OOS',%s)
                    ON CONFLICT(hypothesis_id) DO UPDATE SET fresh_closed_trades=excluded.fresh_closed_trades,
                        context_complete_trades=excluded.context_complete_trades,status_code='QUEUED',
                        reason_code=excluded.reason_code,oos_request=excluded.oos_request,updated_at=clock_timestamp()""",
                        (str(uuid.uuid4()),str(oos_hypothesis_id),link["symbol"],trades,complete,
                         psycopg2.extras.Json({"source": SOURCE,"linkage_key": key,"fresh_cohort": link["scope_code"],
                          "strategy_code":link["strategy_code"],"symbol":link["symbol"],"side_code":link["side_code"],
                          "session_code":link["session_code"],"regime_code":link["regime_code"],
                          "holding_code":link["exit_rule"],"promotion_allowed":False})))
                    readiness = "QUEUED"
                cursor.execute("""INSERT INTO analytics.archive_v3_oos_bridge_v1(
                    linkage_key,portfolio_scope,symbol,strategy_code,side_code,session_code,regime_code,exit_rule,
                    archive_hypothesis_id,archive_match_code,archive_priority,archive_trades,archive_profit_factor,
                    v3_closed_trades,v3_context_complete,v3_profit_factor,v3_expectancy,v3_net_pnl,target_trades,
                    readiness_code,reason_code,oos_hypothesis_id
                ) VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                ON CONFLICT(linkage_key) DO UPDATE SET archive_hypothesis_id=excluded.archive_hypothesis_id,
                    archive_match_code=excluded.archive_match_code,archive_priority=excluded.archive_priority,
                    archive_trades=excluded.archive_trades,archive_profit_factor=excluded.archive_profit_factor,
                    v3_closed_trades=excluded.v3_closed_trades,v3_context_complete=excluded.v3_context_complete,
                    v3_profit_factor=excluded.v3_profit_factor,v3_expectancy=excluded.v3_expectancy,
                    v3_net_pnl=excluded.v3_net_pnl,
                    readiness_code=excluded.readiness_code,reason_code=excluded.reason_code,
                    oos_hypothesis_id=excluded.oos_hypothesis_id,updated_at=clock_timestamp()""",
                    (key,link["scope_code"],link["symbol"],link["strategy_code"],link["side_code"],
                     link["session_code"],link["regime_code"],link["exit_rule"],
                     archived["hypothesis_id"] if archived else None,match_code,
                     archived.get("priority_score") if archived else None,int(archived.get("trades") or 0) if archived else 0,
                     archived.get("profit_factor") if archived else None,trades,complete,profit_factor,expectancy,
                     link["v3_net_pnl"],TARGET,
                     readiness,reason,str(oos_hypothesis_id) if oos_hypothesis_id else None))
                counts[readiness] = counts.get(readiness, 0) + 1
    print(" ".join(f"{key}={value}" for key, value in sorted(counts.items())))
    print(f"VERDICT={SOURCE}_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
