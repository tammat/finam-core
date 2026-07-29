from __future__ import annotations

from datetime import datetime, timezone

import psycopg2
import psycopg2.extras


TARGET_TRADES = 80
ACTIVE_SCOPES = (
    "FRESH_V5_CONFIRMED_EQUITY",
    "FRESH_V5_CONFIRMED_FUTURES",
    "FRESH_V5_USD_PERPETUAL",
    "FRESH_V5_GOLD_FUTURES",
    "FRESH_V5_CNY_PERPETUAL",
)


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
                    SELECT p.portfolio_scope AS scope_code,
                           p.symbol,
                           COALESCE(u.strategy, lifecycle.strategy, 'UNASSIGNED') AS strategy,
                           NULLIF(p.state->>'qty','')::numeric AS qty,
                           NULLIF(p.state->>'avg_price','')::numeric AS entry_price,
                           COALESCE(lifecycle.created_at,p.updated_at) AS opened_at,
                           COALESCE(closed_bars.bars_held,0)::int AS bars_held,
                           closed_bars.last_bar_at,
                           CASE
                             WHEN closed_bars.last_bar_at IS NULL THEN 'WAITING_FIRST_CLOSED_BAR'
                             WHEN clock_timestamp()-closed_bars.last_bar_at >
                                  CASE WHEN p.symbol LIKE 'BR%%@RTSX' OR p.symbol LIKE 'NG%%@RTSX'
                                       THEN interval '3 minutes' ELSE interval '10 minutes' END
                               THEN 'SESSION_IDLE_OR_DATA_STALE'
                             ELSE 'CANDLE_EXIT_MONITOR_ACTIVE'
                           END AS exit_monitor_code
                    FROM analytics.paper_research_position_projection_v1 p
                    LEFT JOIN runtime_active_universe u ON u.symbol=p.symbol AND u.is_enabled
                    LEFT JOIN LATERAL (
                        SELECT l.strategy,l.created_at
                        FROM analytics.paper_research_position_lifecycle_v1 l
                        WHERE l.portfolio_scope=p.portfolio_scope AND l.symbol=p.symbol
                          AND COALESCE(l.remaining_qty,0)<>0
                        ORDER BY l.created_at ASC LIMIT 1
                    ) lifecycle ON true
                    LEFT JOIN LATERAL (
                        SELECT count(*)::int AS bars_held,max(b.ts) AS last_bar_at
                        FROM market_bars b
                        WHERE b.symbol=p.symbol
                          AND b.timeframe=CASE
                              WHEN p.symbol LIKE 'BR%%@RTSX' OR p.symbol LIKE 'NG%%@RTSX'
                                THEN 'M1' ELSE 'M5' END
                          AND b.ts>COALESCE(lifecycle.created_at,p.updated_at)
                          AND b.ts+CASE
                              WHEN b.timeframe='M1' THEN interval '1 minute'
                              ELSE interval '5 minutes' END<=clock_timestamp()
                    ) closed_bars ON true
                    WHERE p.portfolio_scope IN %s
                      AND COALESCE(NULLIF(p.state->>'qty','')::numeric,0)<>0
                    ORDER BY bars_held DESC,p.symbol
                """, (ACTIVE_SCOPES,))
                open_position_diagnostics = [dict(row) for row in cursor.fetchall()]

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

                cursor.execute("""
                    SELECT
                      count(*) FILTER (WHERE request_kind='EDGE_SEARCH_RUN' AND status='PENDING')::int AS edge_pending,
                      count(*) FILTER (WHERE request_kind='EDGE_SEARCH_RUN' AND status='PENDING'
                                             AND actor_id<>'system.scheduler')::int AS edge_manual_pending,
                      count(*) FILTER (WHERE request_kind='EDGE_SEARCH_RUN' AND status='RUNNING')::int AS edge_running,
                      count(*) FILTER (WHERE request_kind='RESEARCH_REFRESH' AND status IN ('PENDING','RUNNING'))::int AS refresh_active,
                      count(*) FILTER (WHERE status='FAILED' AND requested_at >= clock_timestamp()-interval '24 hours')::int AS failed_24h,
                      max(requested_at) FILTER (WHERE request_kind='EDGE_SEARCH_RUN') AS last_edge_requested_at,
                      max(finished_at) FILTER (WHERE request_kind='EDGE_SEARCH_RUN' AND status='COMPLETED') AS last_edge_completed_at
                    FROM marketcore_action.command_request_v2
                """)
                command_state = dict(cursor.fetchone() or {})

                cursor.execute("""
                    SELECT count(*) FILTER (WHERE enabled)::int AS enabled_jobs
                    FROM analytics.system_job_schedule_v1
                    WHERE executor_code IN ('EDGE_SEARCH_AUTO_ENQUEUE_V1','EDGE_SEARCH_COMMAND_QUEUE_V1')
                """)
                command_state["autorun_enabled"] = int(
                    (cursor.fetchone() or {}).get("enabled_jobs") or 0
                ) > 0

                cursor.execute("""
                    SELECT job_code,executor_code,status_code,started_at,finished_at,
                           return_code,coalesce(stderr_tail,'') AS stderr_tail
                    FROM analytics.system_job_run_v1
                    ORDER BY started_at DESC
                    LIMIT 12
                """)
                recent_jobs = [dict(row) for row in cursor.fetchall()]

                cursor.execute("""
                    SELECT symbol,timeframe,latest_bar,age_seconds AS age_sec,
                           session_open,bar_count,maximum_gap_seconds,
                           cost_verified_at,quality_code
                    FROM analytics.runtime_market_data_quality_v1
                    ORDER BY CASE quality_code
                      WHEN 'STALE' THEN 1 WHEN 'GAP' THEN 2
                      WHEN 'NO_COMPLETED_BARS' THEN 3 WHEN 'COST_SPEC_STALE' THEN 4
                      WHEN 'READY' THEN 5 ELSE 6 END,symbol
                """)
                freshness = [dict(row) for row in cursor.fetchall()]
                data_quality_summary = {
                    "ready": sum(row.get("quality_code") == "READY" for row in freshness),
                    "attention": sum(row.get("quality_code") in {
                        "STALE", "GAP", "NO_COMPLETED_BARS", "COST_SPEC_STALE"
                    } for row in freshness),
                    "out_of_session": sum(
                        row.get("quality_code") == "OUT_OF_SESSION" for row in freshness
                    ),
                    "total": len(freshness),
                }

                cursor.execute("""
                    SELECT level_code,count(*)::int AS groups,
                           count(*) FILTER (WHERE decision_code='EARLY_STOP')::int AS early_stop,
                           count(*) FILTER (WHERE decision_code='READY_FOR_OOS')::int AS ready,
                           max(closed_trades)::int AS max_trades
                    FROM analytics.hierarchical_evidence_v1
                    WHERE cohort_code='FRESH_V5_CONFIRM'
                    GROUP BY level_code
                """)
                hierarchy = {row["level_code"]: dict(row) for row in cursor.fetchall()}
                cursor.execute("""
                    SELECT CASE WHEN h.symbol_code LIKE '%@RTSX' THEN 'FRESH_V5_CONFIRMED_FUTURES'
                                ELSE 'FRESH_V5_CONFIRMED_EQUITY' END AS scope_code,
                           max(h.timeframe_code) AS timeframe_code,
                           CASE WHEN count(DISTINCT h.strategy_code)=1 THEN max(h.strategy_code)
                                ELSE 'MULTIPLE_STRATEGIES' END AS strategy_code,
                           h.symbol_code,h.side_code,
                           'ALL'::text AS session_code,'ALL'::text AS regime_code,
                           'ALL'::text AS exit_rule,sum(h.closed_trades)::int AS closed_trades,
                           20::int AS target_trades,sum(h.net_pnl) AS net_pnl,
                           sum(h.net_pnl_r) FILTER (WHERE h.r_observable) AS net_pnl_r,
                           CASE WHEN sum(h.closed_trades) FILTER (WHERE h.r_observable)>0
                                THEN sum(h.net_pnl_r) FILTER (WHERE h.r_observable)
                                     / sum(h.closed_trades) FILTER (WHERE h.r_observable) END AS expectancy_r,
                           bool_or(h.r_observable) AS r_observable,
                           sum(h.net_pnl)/nullif(sum(h.closed_trades),0) AS expectancy,
                           NULL::numeric AS profit_factor,false AS profit_factor_observable,
                           'DISCOVERY_ONLY'::text AS decision_code,
                           'AGGREGATED_BY_INSTRUMENT_SIDE'::text AS reason_code,
                           max(h.updated_at) AS updated_at,
                           CASE WHEN r.display_name IS DISTINCT FROM h.symbol_code
                                THEN r.display_name END AS instrument_name
                    FROM analytics.hierarchical_evidence_v1 h
                    LEFT JOIN marketcore.instrument_reference_v1 r ON r.symbol=h.symbol_code
                    WHERE h.cohort_code='FRESH_V5_CONFIRM' AND h.level_code='EXACT_CONTEXT'
                      AND h.decision_code<>'EARLY_STOP'
                    GROUP BY h.symbol_code,h.side_code,r.display_name
                    ORDER BY closed_trades DESC,net_pnl DESC
                    LIMIT 5
                """)
                hierarchy_top_exact = [dict(row) for row in cursor.fetchall()]
                hierarchy_nearest = hierarchy_top_exact[0] if hierarchy_top_exact else {}

                cursor.execute("""
                    WITH exact AS (
                      SELECT scope_code,timeframe_code,side_code,max(closed_trades)::int AS closed_trades
                      FROM analytics.hierarchical_evidence_v1
                      WHERE cohort_code='FRESH_V5_CONFIRM' AND level_code='EXACT_CONTEXT'
                      GROUP BY 1,2,3
                    )
                    SELECT p.asset_code,p.symbol,p.scope_code,p.timeframe_code,p.side_code,
                           p.strategy_code,coalesce(e.closed_trades,0)::int AS closed_trades,
                           u.timeframe AS active_timeframe,
                           r.rollover_mode,r.readiness_code,r.next_symbol,
                           r.research_entry_allowed,r.oos_allowed,r.reason AS readiness_reason,
                           p.funding_cost_required,
                           c.buy_sell_fee,c.scalper_fee,c.fee_currency,c.verified_at AS cost_verified_at,
                           m.spread_bps,m.observed_at AS spread_observed_at
                    FROM analytics.v5_asset_branch_policy_v1 p
                    JOIN analytics.v5_asset_contract_readiness_v1 r ON r.asset_code=p.asset_code
                    LEFT JOIN exact e ON e.scope_code=p.scope_code
                                     AND e.timeframe_code=p.timeframe_code
                                     AND e.side_code=p.side_code
                    LEFT JOIN runtime_active_universe u ON u.symbol=p.symbol AND u.is_enabled
                    LEFT JOIN analytics.market_contract_cost_spec_v1 c ON c.symbol=p.symbol
                    LEFT JOIN LATERAL (
                      SELECT spread_bps,observed_at
                      FROM analytics.market_microstructure_snapshot_v1
                      WHERE symbol=p.symbol ORDER BY observed_at DESC LIMIT 1
                    ) m ON true
                    WHERE p.enabled
                    ORDER BY array_position(ARRAY['USD','GOLD','CNY']::text[],p.asset_code),
                             p.timeframe_code,p.side_code
                """)
                asset_branches = [dict(row) for row in cursor.fetchall()]

                cursor.execute("""
                    SELECT symbol,max(ts) AS latest_bar,
                           extract(epoch FROM clock_timestamp()-max(ts))::int AS age_sec
                    FROM market_bars
                    WHERE symbol IN ('CNYM@MISX','CNYRUB_TOM@MISX')
                    GROUP BY symbol ORDER BY symbol
                """)
                cny_spot_controls = [dict(row) for row in cursor.fetchall()]

                cursor.execute("""
                    SELECT
                      (SELECT count(DISTINCT symbol)::int
                       FROM runtime_active_universe WHERE is_enabled) AS active_instruments,
                      (SELECT count(DISTINCT symbol_code)::int
                       FROM analytics.hierarchical_evidence_v1
                       WHERE cohort_code='FRESH_V5_CONFIRM' AND level_code='EXACT_CONTEXT') AS instruments_with_closed_v5,
                      (SELECT count(*)::int
                       FROM closed_trades
                       WHERE coalesce(closed_at,exit_ts,created_at) >= current_date
                         AND coalesce(payload->'context'->>'cohort','') LIKE 'FRESH_V5%') AS closed_v5_today
                """)
                universe_summary = dict(cursor.fetchone() or {})

                cursor.execute("""
                    WITH recent_events AS (
                      SELECT coalesce(c.closed_at,c.exit_ts,c.created_at) AS event_ts,
                             c.symbol,'CLOSED'::text AS event_status,
                             c.side AS direction,
                             c.entry_price,c.exit_price,
                             CASE WHEN c.symbol LIKE '%@RTSX'
                                        AND nullif(s.source_payload->>'MINSTEP','')::numeric > 0
                                        AND nullif(s.source_payload->>'STEPPRICE','')::numeric > 0
                                  THEN ((c.exit_price-c.entry_price)
                                        * CASE WHEN c.side='LONG' THEN 1 ELSE -1 END * c.qty
                                        * nullif(s.source_payload->>'STEPPRICE','')::numeric
                                        / nullif(s.source_payload->>'MINSTEP','')::numeric)
                                       - (2 * coalesce(s.buy_sell_fee,0) * c.qty)
                                  ELSE c.net_pnl END AS net_pnl,
                             coalesce(c.holding_seconds,c.hold_seconds)::bigint AS holding_seconds,
                             c.strategy AS entry_signal,
                             coalesce(c.payload->'context'->>'actual_exit_reason',
                                      c.payload->'context'->>'exit_rule', 'unknown') AS exit_reason
                      FROM closed_trades c
                      LEFT JOIN analytics.market_contract_cost_spec_v1 s ON s.symbol=c.symbol
                      WHERE coalesce(c.closed_at,c.exit_ts,c.created_at) >= current_date
                      UNION ALL
                      SELECT s.created_at AS event_ts,s.symbol,'ACTIVE'::text AS event_status,
                             CASE WHEN s.side IN ('BUY','LONG') THEN 'LONG' ELSE 'SHORT' END AS direction,
                             coalesce(sf.price,s.entry_price) AS entry_price,
                             CASE WHEN s.side IN ('BUY','LONG')
                                  THEN coalesce(q.best_bid,b.close,sf.price,s.entry_price)
                                  ELSE coalesce(q.best_ask,b.close,sf.price,s.entry_price) END AS exit_price,
                             CASE WHEN s.symbol LIKE '%@RTSX'
                                        AND nullif(cs.source_payload->>'MINSTEP','')::numeric > 0
                                        AND nullif(cs.source_payload->>'STEPPRICE','')::numeric > 0
                                  THEN ((CASE WHEN s.side IN ('BUY','LONG')
                                              THEN coalesce(q.best_bid,b.close,sf.price,s.entry_price)-coalesce(sf.price,s.entry_price)
                                              ELSE coalesce(sf.price,s.entry_price)-coalesce(q.best_ask,b.close,sf.price,s.entry_price) END)
                                        * coalesce(sf.qty,s.qty,0)
                                        * nullif(cs.source_payload->>'STEPPRICE','')::numeric
                                        / nullif(cs.source_payload->>'MINSTEP','')::numeric)
                                       - (2 * coalesce(cs.buy_sell_fee,0) * coalesce(sf.qty,s.qty,0))
                                  ELSE (CASE WHEN s.side IN ('BUY','LONG')
                                              THEN coalesce(q.best_bid,b.close,sf.price,s.entry_price)-coalesce(sf.price,s.entry_price)
                                              ELSE coalesce(sf.price,s.entry_price)-coalesce(q.best_ask,b.close,sf.price,s.entry_price) END)
                                       * coalesce(sf.qty,s.qty,0) END AS net_pnl,
                             extract(epoch FROM clock_timestamp()-s.created_at)::bigint AS holding_seconds,
                             s.strategy AS entry_signal,
                             'position_open'::text AS exit_reason
                      FROM signals s
                      LEFT JOIN LATERAL (
                        SELECT qty,price
                        FROM signal_fills f
                        WHERE f.signal_id=s.signal_id
                        ORDER BY f.created_at DESC LIMIT 1
                      ) sf ON true
                      LEFT JOIN analytics.market_contract_cost_spec_v1 cs ON cs.symbol=s.symbol
                      LEFT JOIN LATERAL (
                        SELECT best_bid,best_ask
                        FROM analytics.market_microstructure_snapshot_v1 m
                        WHERE m.symbol=s.symbol
                          AND m.observed_at >= clock_timestamp()-interval '5 minutes'
                        ORDER BY m.observed_at DESC LIMIT 1
                      ) q ON true
                      LEFT JOIN LATERAL (
                        SELECT close
                        FROM market_bars mb
                        WHERE mb.symbol=s.symbol
                        ORDER BY mb.ts DESC LIMIT 1
                      ) b ON true
                      WHERE s.status='FILLED'
                        AND s.created_at >= current_date
                        AND coalesce(s.payload->>'intent_type','ENTRY')='ENTRY'
                        AND NOT EXISTS (
                          SELECT 1 FROM closed_trades c
                          WHERE c.signal_id=s.signal_id
                        )
                    ), ranked AS (
                      SELECT e.*,
                             CASE WHEN e.symbol LIKE '%@RTSX' THEN true ELSE false END AS is_futures,
                             row_number() OVER (ORDER BY e.event_ts DESC) AS overall_rank,
                             row_number() OVER (
                               PARTITION BY (e.symbol LIKE '%@RTSX') ORDER BY e.event_ts DESC
                             ) AS class_rank
                      FROM recent_events e
                    )
                    SELECT x.event_ts,x.symbol,x.event_status,x.direction,
                           x.entry_price,x.exit_price,x.net_pnl,x.holding_seconds,x.entry_signal,x.exit_reason,
                           x.is_futures,
                           CASE WHEN r.display_name IS DISTINCT FROM x.symbol
                                THEN r.display_name END AS instrument_name
                    FROM ranked x
                    LEFT JOIN marketcore.instrument_reference_v1 r ON r.symbol=x.symbol
                    WHERE x.overall_rank <= 16 OR (x.is_futures AND x.class_rank <= 4)
                    ORDER BY event_ts DESC
                    LIMIT 24
                """)
                recent_trade_events = [dict(row) for row in cursor.fetchall()]

                cursor.execute("""
                    SELECT DISTINCT ON (strategy_code,symbol_group,side_code)
                           strategy_code,symbol_group,side_code,candidate_code,
                           recommendation_status,pairs,oos_pairs,entry_mode,
                           stop_atr,take_atr,trail_after_r,trail_atr,metrics,generated_at,
                           operator_decision,operator_decided_at,
                           EXISTS(SELECT 1 FROM analytics.entry_exit_runtime_profile_v1 p
                             WHERE p.strategy_code=r.strategy_code AND p.symbol_group=r.symbol_group
                               AND p.side_code=r.side_code AND p.candidate_code=r.candidate_code
                               AND p.execution_mode='paper' AND p.status='ACTIVE') AS is_active_paper
                    FROM analytics.entry_exit_recommendation_v1 r
                    ORDER BY strategy_code,symbol_group,side_code,
                             CASE recommendation_status
                               WHEN 'READY_FOR_PAPER_CONFIRMATION' THEN 0
                               WHEN 'KEEP_SHADOW' THEN 1 ELSE 2 END,
                             coalesce((metrics->>'shadow_oos_r')::numeric,-999) DESC,
                             generated_at DESC
                    LIMIT 12
                """)
                entry_exit_recommendations = [dict(row) for row in cursor.fetchall()]

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
            "open_position_diagnostics": open_position_diagnostics,
            "ready_links": ready,
            "oos_pass": oos_pass,
            "process": process,
            "constraint": constraint,
            "next_action": next_action,
            "nearest": nearest,
            "branch_plan": branch_plan,
            "command_state": command_state,
            "recent_jobs": recent_jobs,
            "freshness": freshness,
            "data_quality_summary": data_quality_summary,
            "manual_symbol": str((nearest or {}).get("symbol") or "BRQ6@RTSX"),
            "hierarchy": hierarchy,
            "hierarchy_nearest": hierarchy_nearest,
            "hierarchy_top_exact": hierarchy_top_exact,
            "asset_branches": asset_branches,
            "cny_spot_controls": cny_spot_controls,
            "universe_summary": universe_summary,
            "recent_trade_events": recent_trade_events,
            "entry_exit_recommendations": entry_exit_recommendations,
        }
