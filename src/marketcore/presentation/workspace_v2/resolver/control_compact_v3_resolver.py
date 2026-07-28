from __future__ import annotations

from datetime import datetime, timezone

import psycopg2
import psycopg2.extras


TARGET_TRADES = 80
ACTIVE_SCOPES = ("FRESH_V5_CONFIRMED_EQUITY", "FRESH_V5_CONFIRMED_FUTURES")


class ControlCompactV3Resolver:
    """Small, source-backed operator snapshot for the unified Control screen."""

    def resolve(self) -> dict:
        with psycopg2.connect("postgresql:///finam_core") as connection:
            with connection.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cursor:
                cursor.execute("""
                    SELECT portfolio_scope AS scope_code,
                           count(*)::int AS closed_total,
                           count(*) FILTER (WHERE coalesce(closed_at, created_at) >= clock_timestamp() - interval '1 hour')::int AS closed_hour,
                           max(coalesce(closed_at, created_at)) AS last_closed_at
                    FROM analytics.closed_trades_fresh_v5_confirmed
                    GROUP BY 1
                """)
                summaries = {row["scope_code"]: dict(row) for row in cursor.fetchall()}

                cursor.execute("""
                    SELECT count(*) FILTER (WHERE portfolio_scope LIKE 'FRESH_V5%%')::int AS v5_audit_total
                    FROM closed_trades WHERE source='paper_fill_materializer_v2'
                """)
                audit = dict(cursor.fetchone() or {})
                cursor.execute("""
                    SELECT count(*)::int AS open_positions
                    FROM analytics.paper_research_position_projection_v1
                    WHERE portfolio_scope IN %s
                      AND coalesce(nullif(state->>'qty','')::numeric,0) <> 0
                """, (ACTIVE_SCOPES,))
                open_positions = int((cursor.fetchone() or {}).get("open_positions") or 0)

                cursor.execute("""
                    WITH grouped AS (
                        SELECT portfolio_scope AS scope_code,
                               symbol,
                               COALESCE(NULLIF(strategy,''), 'UNASSIGNED') AS strategy,
                               upper(COALESCE(NULLIF(side,''), payload->>'side', 'UNKNOWN')) AS side,
                               COALESCE(payload->'context'->>'entry_session_msk', 'unknown') AS session_code,
                               concat_ws('_',
                                   payload->'context'->>'regime_trend',
                                   payload->'context'->>'regime_vol'
                               ) AS regime_code,
                               COALESCE(
                                   payload->'context'->>'actual_exit_reason',
                                   payload->'context'->>'exit_rule',
                                   'UNKNOWN'
                               ) AS exit_rule,
                               count(*)::int AS accumulated,
                               max(coalesce(closed_at,created_at)) AS updated_at,
                               sum(COALESCE(net_pnl,0))::double precision AS fresh_net_pnl,
                               sum(CASE WHEN COALESCE(net_pnl,0)>0 THEN COALESCE(net_pnl,0) ELSE 0 END)::double precision AS gross_profit,
                               abs(sum(CASE WHEN COALESCE(net_pnl,0)<0 THEN COALESCE(net_pnl,0) ELSE 0 END))::double precision AS gross_loss
                        FROM analytics.closed_trades_fresh_v5_confirmed
                        GROUP BY 1,2,3,4,5,6,7
                    )
                    SELECT *,
                           CASE WHEN gross_loss > 0 THEN gross_profit/gross_loss END AS fresh_profit_factor,
                           CASE WHEN accumulated >= 80 THEN 'READY_FOR_OOS' ELSE 'WAITING_SAMPLE' END AS readiness_code,
                           CASE WHEN accumulated >= 80 THEN 'V5_SAMPLE_READY' ELSE 'FRESH_V5_SAMPLE_BELOW_80' END AS reason_code
                    FROM grouped
                    ORDER BY accumulated DESC,updated_at DESC
                    LIMIT 120
                """)
                links = [dict(row) for row in cursor.fetchall()]

                cursor.execute("""
                    SELECT symbol,strategy_code,side_code,session_code,regime_code,exit_rule,
                           accumulated_trades,target_trades,status_code,reason_code,priority_score,updated_at
                    FROM analytics.archive_exact_v3_branch_plan_v1
                    ORDER BY priority_score DESC NULLS LAST,updated_at DESC
                    LIMIT 20
                """)
                branch_plan = [dict(row) for row in cursor.fetchall()]

                cursor.execute("""
                    SELECT symbol FROM fills
                    WHERE symbol LIKE 'NG%%@RTSX'
                    GROUP BY symbol ORDER BY max(ts) DESC LIMIT 1
                """)
                active_futures = {str(row["symbol"]) for row in cursor.fetchall()}

                cursor.execute("""
                    SELECT status_code, current_step, progress_pct, markets_evaluated,
                           combinations_evaluated, oos_pass, started_at, finished_at
                    FROM analytics.edge_search_cycle_status_v1
                    ORDER BY started_at DESC LIMIT 1
                """)
                process = dict(cursor.fetchone() or {})

                cursor.execute("""
                    SELECT count(*)::int AS oos_pass
                    FROM analytics.hypothesis_trial_registry_v2
                    WHERE verdict_code='OOS_PASS' AND coalesce(promotion_allowed,false)
                """)
                oos_pass = int((cursor.fetchone() or {}).get("oos_pass") or 0)

                cursor.execute("""
                    SELECT stream_code, caption_ru, state_code, allocation_share, updated_at
                    FROM analytics.research_stream_v1
                    WHERE stream_code IN ('FRESH_V5_CONFIRMED_EQUITY','FRESH_V5_CONFIRMED_FUTURES')
                    ORDER BY stream_code
                """)
                streams = {row["stream_code"]: dict(row) for row in cursor.fetchall()}

        for row in links:
            count = int(row["accumulated"] or 0)
            row["target"] = TARGET_TRADES
            row["missing"] = max(0, TARGET_TRADES - count)
            row["progress_pct"] = min(100.0, 100.0 * count / TARGET_TRADES)
            row["status"] = "Готово к OOS" if count >= TARGET_TRADES else "Накапливается"
            row["archive_match_code"] = "V5_ONLY"
            row["archive_trades"] = 0
            row["archive_profit_factor"] = None

        by_scope = {
            code: [row for row in links if row["scope_code"] == code]
            for code in ACTIVE_SCOPES
        }
        total_closed = sum(int(row.get("closed_total") or 0) for row in summaries.values())
        excluded_closed = max(0, int(audit.get("v5_audit_total") or 0) - total_closed)
        closed_hour = sum(int(row.get("closed_hour") or 0) for row in summaries.values())
        ready = sum(1 for row in links if row["accumulated"] >= TARGET_TRADES)
        nearest = max(links, key=lambda row: row["accumulated"], default=None)
        if total_closed == 0:
            constraint = f"Чистых V5-закрытий нет; исключено методологией: {excluded_closed}; открытых Paper-позиций: {open_positions}"
            next_action = "Продолжать текущую сессию; принимать только режимно совместимые входы"
        elif ready == 0 and nearest:
            constraint = (
                f"Всего V5: {total_closed}; лучшая связка: {nearest['accumulated']} из {TARGET_TRADES}; "
                f"осталось: {nearest['missing']}"
            )
            next_action = "Продолжать накопление без смены методологии"
        else:
            constraint = "Блокирующих ограничений накопления нет"
            next_action = "Готовые связки автоматически поставить в OOS"

        for row in branch_plan:
            side, regime, symbol = str(row.get("side_code") or "").upper(), str(row.get("regime_code") or "").lower(), str(row.get("symbol") or "")
            if symbol.startswith("NG") and symbol not in active_futures:
                row["operator_status"] = "STALE_CONTRACT"
            elif (side in {"LONG", "BUY"} and regime.startswith("trend_down")) or (side in {"SHORT", "SELL"} and regime.startswith("trend_up")):
                row["operator_status"] = "BLOCKED_DIRECTION"
            elif regime in {"", "unknown", "unspecified"} or str(row.get("session_code") or "").lower() in {"", "unknown"}:
                row["operator_status"] = "WAITING_CONTEXT"
            else:
                row["operator_status"] = str(row.get("status_code") or "WAITING")

        return {
            "generated_at": datetime.now(timezone.utc),
            "target_trades": TARGET_TRADES,
            "summaries": summaries,
            "streams": streams,
            "links": by_scope,
            "closed_total": total_closed,
            "closed_hour": closed_hour,
            "excluded_closed": excluded_closed,
            "open_positions": open_positions,
            "ready_links": ready,
            "oos_pass": oos_pass,
            "process": process,
            "constraint": constraint,
            "next_action": next_action,
            "nearest": nearest,
            "branch_plan": branch_plan,
        }
