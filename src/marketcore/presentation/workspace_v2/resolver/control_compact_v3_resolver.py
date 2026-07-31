from __future__ import annotations

from datetime import datetime, timezone
from zoneinfo import ZoneInfo

import psycopg2
import psycopg2.extras

from finam_core.session.session_manager import SessionManager


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
                    WITH latest AS (
                      SELECT signal_funnel_snapshot_id
                      FROM analytics.signal_funnel_snapshot_v1
                      ORDER BY created_at DESC LIMIT 1
                    )
                    SELECT stage_code,stage_name,stage_count,previous_stage_count,
                           pass_rate_pct,stage_status,evidence_json,created_at
                    FROM analytics.signal_funnel_stage_v1
                    WHERE signal_funnel_snapshot_id=(SELECT signal_funnel_snapshot_id FROM latest)
                    ORDER BY stage_order
                """)
                signal_funnel_stages = [dict(row) for row in cursor.fetchall()]
                cursor.execute("""
                    WITH latest AS (
                      SELECT signal_funnel_reason_snapshot_id
                      FROM analytics.signal_funnel_reason_snapshot_v1
                      ORDER BY created_at DESC LIMIT 1
                    )
                    SELECT reason_group,sum(rows_total)::int AS rows_total,
                           count(*)::int AS reason_values,max(created_at) AS updated_at
                    FROM analytics.signal_funnel_reason_v1
                    WHERE signal_funnel_reason_snapshot_id=(
                      SELECT signal_funnel_reason_snapshot_id FROM latest
                    )
                    GROUP BY reason_group
                    ORDER BY sum(rows_total) DESC
                """)
                signal_funnel_reasons = [dict(row) for row in cursor.fetchall()]
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
                    SELECT
                      (SELECT count(*)::int
                       FROM analytics.edge_oos_result_v1
                       WHERE verdict_code='OOS_PASS'
                         AND coalesce(promotion_allowed,false)) AS promoted_oos,
                      (SELECT count(*)::int
                       FROM strategy_promotion_runtime_feed
                       WHERE coalesce(allow_paper_signal,false)) AS paper_admitted
                """)
                promotion_summary = dict(cursor.fetchone() or {})

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
                now_msk = datetime.now(ZoneInfo("Europe/Moscow"))
                session_manager = SessionManager()
                session_regime = session_manager.get_regime(
                    "BRQ6@RTSX", market_data_live=False, now=now_msk
                )
                session_status = {
                    **session_regime,
                    "next_open": session_manager.next_entry_session(
                        symbol="BRQ6@RTSX", now=now_msk
                    ),
                }
                cursor.execute("""
                    SELECT event_code,title_ru,category_code,risk_level,symbol_patterns,
                           starts_at,expires_at,source_url,source_note,updated_at
                    FROM analytics.market_event_risk_v1
                    WHERE is_active AND starts_at<=clock_timestamp()
                      AND (expires_at IS NULL OR expires_at>clock_timestamp())
                    ORDER BY CASE risk_level WHEN 'SHOCK' THEN 1 WHEN 'ELEVATED' THEN 2
                             WHEN 'RECOVERY' THEN 3 ELSE 4 END,updated_at DESC LIMIT 1
                """)
                market_event_risk = dict(cursor.fetchone() or {})
                cursor.execute("""
                    SELECT evaluated_at,symbol,state_code,mode_code,allowed,reason_code,
                           completed_m15_bars,gap_atr,spread_atr,relative_volume,
                           market_context_fresh,event_code
                    FROM analytics.market_shock_gate_audit_v1
                    ORDER BY evaluated_at DESC LIMIT 1
                """)
                market_shock_gate = dict(cursor.fetchone() or {})

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
                      SELECT portfolio_scope AS scope_code,
                             upper(side) AS side_code,count(*)::int AS closed_trades
                      FROM analytics.closed_trades_fresh_v5_confirmed
                      WHERE portfolio_scope LIKE 'FRESH_V5%'
                      GROUP BY 1,2
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
                    LEFT JOIN exact e ON e.scope_code=p.scope_code AND e.side_code=p.side_code
                    LEFT JOIN runtime_active_universe u ON u.symbol=p.symbol AND u.is_enabled
                    LEFT JOIN LATERAL (
                      SELECT buy_sell_fee,scalper_fee,fee_currency,verified_at,source_payload
                      FROM analytics.market_contract_cost_spec_v1 cost
                      WHERE cost.symbol=p.symbol ORDER BY verified_at DESC NULLS LAST LIMIT 1
                    ) c ON true
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
                             c.net_pnl AS net_pnl,
                             coalesce(c.holding_seconds,c.hold_seconds)::bigint AS holding_seconds,
                             c.strategy AS entry_signal,
                             coalesce(c.payload->'context'->>'actual_exit_reason',
                                      c.payload->'context'->>'exit_rule', 'unknown') AS exit_reason,
                             coalesce(c.entry_ts,c.opened_at,c.created_at) AS opened_at,
                             coalesce(c.exit_ts,c.closed_at,c.created_at) AS quote_ts
                      FROM closed_trades c
                      LEFT JOIN LATERAL (
                        SELECT buy_sell_fee,source_payload
                        FROM analytics.market_contract_cost_spec_v1 cost
                        WHERE cost.symbol=c.symbol ORDER BY verified_at DESC NULLS LAST LIMIT 1
                      ) s ON true
                      WHERE coalesce(c.closed_at,c.exit_ts,c.created_at)
                            >= clock_timestamp() - interval '24 hours'
                        AND c.payload->'pnl_units'->>'version'='PNL_UNITS_V2_RUB'
                      UNION ALL
                      SELECT coalesce(l.created_at,p.updated_at) AS event_ts,p.symbol,'ACTIVE'::text AS event_status,
                             CASE WHEN position.net_qty>0 THEN 'LONG' ELSE 'SHORT' END AS direction,
                             position.avg_price AS entry_price,
                             coalesce(b.close,position.avg_price) AS exit_price,
                             CASE WHEN ms.lot_size > 0
                                        AND (p.symbol NOT LIKE '%@RTSX'
                                             OR (ms.tick_size > 0 AND ms.tick_value > 0))
                                  THEN ((CASE WHEN position.net_qty>0
                                              THEN coalesce(b.close,position.avg_price)-position.avg_price
                                              ELSE position.avg_price-coalesce(b.close,position.avg_price) END)
                                        * abs(position.net_qty)
                                        * CASE WHEN p.symbol LIKE '%@RTSX'
                                               THEN ms.tick_value/ms.tick_size
                                               ELSE ms.lot_size END)
                                       - CASE WHEN p.symbol LIKE '%@RTSX'
                                              THEN 2 * coalesce(cs.buy_sell_fee,0) * abs(position.net_qty)
                                              ELSE 0 END
                                  ELSE NULL END AS net_pnl,
                             extract(epoch FROM clock_timestamp()-coalesce(l.created_at,p.updated_at))::bigint AS holding_seconds,
                             coalesce(signal.strategy,'UNASSIGNED') AS entry_signal,
                             'position_open'::text AS exit_reason,
                             coalesce(l.created_at,p.updated_at) AS opened_at,
                             b.ts AS quote_ts
                      FROM analytics.paper_research_position_projection_v1 p
                      CROSS JOIN LATERAL (
                        SELECT coalesce(nullif(p.state->>'net_qty','')::numeric,
                                        nullif(p.state->>'qty','')::numeric,0) AS net_qty,
                               coalesce(nullif(p.state->>'avg_price','')::numeric,0) AS avg_price
                      ) position
                      LEFT JOIN LATERAL (
                        SELECT s.strategy
                        FROM signal_fills sf JOIN signals s ON s.signal_id=sf.signal_id
                        WHERE sf.portfolio_scope=p.portfolio_scope AND sf.symbol=p.symbol
                          AND ((position.net_qty>0 AND sf.side='BUY') OR
                               (position.net_qty<0 AND sf.side='SELL'))
                        ORDER BY sf.created_at DESC LIMIT 1
                      ) signal ON true
                      LEFT JOIN LATERAL (
                        SELECT created_at
                        FROM analytics.paper_research_position_lifecycle_v1 lifecycle
                        WHERE lifecycle.portfolio_scope=p.portfolio_scope
                          AND lifecycle.symbol=p.symbol AND lifecycle.remaining_qty>0
                        LIMIT 1
                      ) l ON true
                      LEFT JOIN LATERAL (
                        SELECT buy_sell_fee,source_payload
                        FROM analytics.market_contract_cost_spec_v1 cost
                        WHERE cost.symbol=p.symbol ORDER BY verified_at DESC NULLS LAST LIMIT 1
                      ) cs ON true
                      LEFT JOIN LATERAL (
                        SELECT lot_size::numeric,tick_size::numeric,tick_value::numeric
                        FROM analytics.market_contract_spec_v1 spec
                        WHERE spec.symbol=p.symbol AND spec.is_active
                        ORDER BY spec.valid_from DESC LIMIT 1
                      ) ms ON true
                      LEFT JOIN LATERAL (
                        SELECT close, ts
                        FROM market_bars mb
                        WHERE mb.symbol=p.symbol
                        ORDER BY mb.ts DESC LIMIT 1
                      ) b ON true
                      WHERE p.portfolio_scope LIKE 'FRESH_V5%'
                        AND p.symbol NOT LIKE 'TEST@%'
                        AND abs(position.net_qty)>0.000000001
                        AND position.avg_price>0
                    ), ranked AS (
                      SELECT e.*,
                             CASE WHEN e.symbol LIKE '%@RTSX' THEN true ELSE false END AS is_futures,
                             row_number() OVER (ORDER BY e.event_ts DESC) AS overall_rank,
                             row_number() OVER (
                               PARTITION BY (e.symbol LIKE '%@RTSX') ORDER BY e.event_ts DESC
                             ) AS class_rank,
                             sum(e.net_pnl) FILTER (
                               WHERE e.event_ts>=date_trunc('day',clock_timestamp())
                             ) OVER (PARTITION BY (e.symbol LIKE '%@RTSX')) AS daily_net_pnl
                             ,sum(e.net_pnl) FILTER (
                               WHERE e.event_status='CLOSED'
                                 AND e.event_ts>=date_trunc('day',clock_timestamp())
                             ) OVER (PARTITION BY (e.symbol LIKE '%@RTSX')) AS daily_realized_net_pnl
                             ,sum(e.net_pnl) FILTER (
                               WHERE e.event_status='ACTIVE'
                             ) OVER (PARTITION BY (e.symbol LIKE '%@RTSX')) AS active_unrealized_net_pnl
                      FROM recent_events e
                    )
                    SELECT x.event_ts,x.symbol,x.event_status,x.direction,
                           x.entry_price,x.exit_price,x.net_pnl,x.holding_seconds,x.entry_signal,x.exit_reason,
                           x.is_futures,x.daily_net_pnl,x.daily_realized_net_pnl,
                           x.active_unrealized_net_pnl,x.opened_at,x.quote_ts,
                           CASE WHEN r.display_name IS DISTINCT FROM x.symbol
                                THEN r.display_name END AS instrument_name
                    FROM ranked x
                    LEFT JOIN marketcore.instrument_reference_v1 r ON r.symbol=x.symbol
                    WHERE x.event_status='ACTIVE'
                       OR x.overall_rank <= 16
                       OR (x.is_futures AND x.class_rank <= 4)
                    ORDER BY event_ts DESC
                    LIMIT 24
                """)
                recent_trade_events = [dict(row) for row in cursor.fetchall()]

                cursor.execute("""
                    SELECT DISTINCT ON (r.strategy_code,r.symbol_group,r.side_code)
                           r.strategy_code,r.symbol_group,r.side_code,r.candidate_code,
                           r.recommendation_status,r.pairs,r.oos_pairs,r.entry_mode,
                           r.stop_atr,r.take_atr,r.trail_after_r,r.trail_atr,r.metrics,r.generated_at,
                           r.operator_decision,r.operator_decided_at,
                           cc.champion_candidate_code,cc.challenger_candidate_code,
                           cc.challenger_status,cc.challenger_selected_at,
                           cc.paper_metrics AS challenger_paper_metrics,
                           cc.champion_metrics,cc.consecutive_degraded_cycles,
                           cc.rollback_reason,cc.last_transition_at,
                           paper.entry_mode AS paper_entry_mode,
                           paper.stop_atr AS paper_stop_atr,
                           paper.take_atr AS paper_take_atr,
                           paper.trail_after_r AS paper_trail_after_r,
                           paper.trail_atr AS paper_trail_atr,
                           adaptive.candidate_code AS adaptive_candidate_code,
                           adaptive.recommendation_status AS adaptive_status,
                           adaptive.pairs AS adaptive_pairs,
                           adaptive.oos_pairs AS adaptive_oos_pairs,
                           adaptive.metrics AS adaptive_metrics,
                           family.family_code AS family_code,
                           family.evidence_status AS family_evidence_status,
                           family.pairs AS family_pairs,
                           family.oos_pairs AS family_oos_pairs,
                           family.metrics AS family_metrics,
                           EXISTS(SELECT 1 FROM analytics.entry_exit_runtime_profile_v1 p
                             WHERE p.strategy_code=r.strategy_code AND p.symbol_group=r.symbol_group
                               AND p.side_code=r.side_code AND p.candidate_code=r.candidate_code
                               AND p.execution_mode='paper' AND p.status='ACTIVE') AS is_active_paper
                    FROM analytics.entry_exit_recommendation_v1 r
                    LEFT JOIN analytics.entry_exit_champion_challenger_v1 cc
                      ON cc.strategy_code=r.strategy_code AND cc.symbol_group=r.symbol_group
                     AND cc.side_code=r.side_code
                    LEFT JOIN analytics.entry_exit_runtime_profile_v1 paper
                      ON paper.profile_id=cc.champion_profile_id
                     AND paper.execution_mode='paper' AND paper.status='ACTIVE'
                    LEFT JOIN LATERAL (
                      SELECT ar.candidate_code,ar.recommendation_status,ar.pairs,
                             ar.oos_pairs,ar.metrics
                      FROM analytics.entry_exit_recommendation_v1 ar
                      WHERE ar.strategy_code=r.strategy_code
                        AND ar.symbol_group=r.symbol_group
                        AND ar.side_code=r.side_code
                        AND ar.entry_mode='ADAPTIVE'
                      ORDER BY ar.pairs DESC,ar.generated_at DESC
                      LIMIT 1
                    ) adaptive ON true
                    LEFT JOIN LATERAL (
                      SELECT fe.family_code,fe.evidence_status,fe.pairs,fe.oos_pairs,fe.metrics
                      FROM analytics.entry_exit_family_evidence_v1 fe
                      WHERE fe.family_code=CASE
                              WHEN r.strategy_code IN ('MEAN_REVERSION_EQUITY','VOLATILITY_BREAKOUT_EQUITY') THEN 'EQUITIES'
                              WHEN r.strategy_code='BR_CONSERVATIVE_BREAKOUT' THEN 'OIL'
                              WHEN r.strategy_code='NG_CONSERVATIVE_BREAKOUT_M1' THEN 'GAS'
                              WHEN r.strategy_code IN ('CNY_REGIME_FUTURES','USD_REGIME_FUTURES') THEN 'FX'
                              WHEN r.strategy_code='GOLD_TREND_BREAKOUT' THEN 'METALS'
                              ELSE 'OTHER' END
                        AND fe.side_code=r.side_code
                        AND fe.candidate_code=r.candidate_code
                      LIMIT 1
                    ) family ON true
                    ORDER BY r.strategy_code,r.symbol_group,r.side_code,
                             (r.candidate_code=cc.challenger_candidate_code) DESC,
                             CASE r.recommendation_status
                               WHEN 'READY_FOR_PAPER_CONFIRMATION' THEN 0
                               WHEN 'KEEP_SHADOW' THEN 1 ELSE 2 END,
                             coalesce((r.metrics->>'shadow_oos_r')::numeric,-999) DESC,
                             r.generated_at DESC
                    LIMIT 24
                """)
                entry_exit_recommendations = [dict(row) for row in cursor.fetchall()]

                cursor.execute("""
                    SELECT symbol,side_code,strategy_code,regime_code,
                           CASE entry_mode
                             WHEN 'ADAPTIVE' THEN 'ADAPTIVE_OR_SKIP'
                             ELSE entry_mode
                           END policy_family,
                           candidate_code,status_code,shadow_observations,
                           shadow_expectancy,shadow_profit_factor,
                           paper_observations,paper_expectancy,paper_profit_factor,
                           evidence,evaluated_at
                    FROM analytics.adaptive_regime_paper_pilot_v1
                    WHERE status_code<>'SUPERSEDED'
                    ORDER BY CASE status_code
                               WHEN 'PAPER_CONFIRMED' THEN 0
                               WHEN 'PILOT_ACTIVE' THEN 1
                               WHEN 'SHADOW_COLLECTING' THEN 2
                               ELSE 3 END,
                             shadow_observations DESC,evaluated_at DESC
                    LIMIT 12
                """)
                adaptive_policy_families = [dict(row) for row in cursor.fetchall()]

                cursor.execute("SELECT * FROM analytics.v5_oos_evidence_panel_v1")
                v5_oos_evidence = dict(cursor.fetchone() or {})
                cursor.execute("""SELECT r.status_code,r.reason_code,r.observations_included,
                           r.observations_excluded,r.minimum_observations,r.expectancy,
                           r.profit_factor,r.confirmation_after_ts,r.updated_at,
                           a.symbol,a.oos_request->>'paper_strategy_code' AS strategy_code,
                           a.oos_request->>'side_code' AS side_code
                    FROM analytics.v5_oos_run_v1 r
                    JOIN analytics.trade_outcome_oos_admission_v1 a USING(admission_id)
                    ORDER BY CASE r.status_code WHEN 'OOS_PASS' THEN 0
                              WHEN 'COLLECTING' THEN 1 ELSE 2 END,
                             r.updated_at DESC LIMIT 12""")
                v5_oos_runs = [dict(row) for row in cursor.fetchall()]

                cursor.execute("""SELECT * FROM analytics.market_regime_context_v1
                    ORDER BY context_ts DESC LIMIT 1""")
                market_regime_context = dict(cursor.fetchone() or {})
                cursor.execute("""SELECT parent_signal_id,symbol,strategy,side,signal_ts,
                    variant_code,decision_code,risk_multiplier,reason_code,market_context
                    FROM analytics.market_regime_shadow_variant_v1
                    ORDER BY signal_ts DESC,id DESC LIMIT 18""")
                market_regime_shadow_variants = [dict(row) for row in cursor.fetchall()]

                cursor.execute("""
                    WITH ranked AS (
                      SELECT symbol_code,side_code,candidate_code,shadow_net_r,
                             label_end_ts,generated_at,
                             row_number() OVER (
                               PARTITION BY symbol_code,side_code,candidate_code
                               ORDER BY label_end_ts DESC NULLS LAST,generated_at DESC
                             ) AS rn
                      FROM analytics.entry_exit_signal_shadow_pair_v2
                      WHERE shadow_entered
                        AND shadow_net_r IS NOT NULL
                    ), aggregated AS (
                    SELECT symbol_code,side_code,candidate_code,
                           count(*)::int AS evaluated,
                           count(*) FILTER (WHERE shadow_net_r>0)::int AS wins,
                           avg(shadow_net_r) AS expectancy_r,
                           sum(shadow_net_r) AS net_r,
                           avg(shadow_net_r) FILTER (WHERE rn<=20) AS recent_expectancy_r,
                           avg(shadow_net_r) FILTER (WHERE rn>20 AND rn<=40) AS previous_expectancy_r,
                           max(label_end_ts) AS latest_result_ts,
                           max(generated_at) AS updated_at
                    FROM ranked
                    GROUP BY symbol_code,side_code,candidate_code
                    ), best_per_direction AS (
                      SELECT aggregated.*,
                             max(latest_result_ts) OVER () AS stream_latest_result_ts,
                             row_number() OVER (
                               PARTITION BY symbol_code,side_code
                               ORDER BY recent_expectancy_r DESC NULLS LAST,
                                        evaluated DESC,candidate_code
                             ) AS candidate_rank
                      FROM aggregated
                    )
                    SELECT *
                    FROM best_per_direction
                    WHERE candidate_rank=1
                    ORDER BY recent_expectancy_r DESC NULLS LAST,evaluated DESC
                    LIMIT 12
                """)
                raw_shadow_dynamics = [dict(row) for row in cursor.fetchall()]
                cursor.execute("""
                    WITH evidence AS (
                      SELECT r.*,
                             nullif(r.metrics #>> '{negative_control,candidate_expectancy_r}','')::numeric
                               AS candidate_expectancy_r,
                             nullif(r.metrics #>> '{negative_control,placebo_expectancy_r}','')::numeric
                               AS placebo_expectancy_r,
                             nullif(r.metrics #>> '{negative_control,delta_expectancy_r}','')::numeric
                               AS delta_expectancy_r,
                             nullif(r.metrics #>> '{negative_control,delta_lower_bound_r}','')::numeric
                               AS delta_lower_bound_r,
                             coalesce((r.metrics #>> '{negative_control,passed}')::boolean,false)
                               AS placebo_passed,
                             coalesce((r.metrics #>> '{parameter_plateau,passed}')::boolean,false)
                               AS plateau_passed
                      FROM analytics.entry_exit_recommendation_v1 r
                    ), ranked AS (
                      SELECT evidence.*,
                             row_number() OVER (
                               PARTITION BY symbol_group,side_code
                               ORDER BY (pairs >= 10) DESC,
                                        placebo_passed DESC,
                                        delta_lower_bound_r DESC NULLS LAST,
                                        pairs DESC,candidate_code
                             ) AS evidence_rank
                      FROM evidence
                    )
                    SELECT CASE symbol_group
                             WHEN 'BR' THEN 'BRQ6'
                             WHEN 'NG' THEN 'NGQ6'
                             WHEN 'CNY' THEN 'CNYRUBF'
                             WHEN 'USD' THEN 'USDRUBF'
                             WHEN 'GOLD' THEN 'GDU6'
                             ELSE symbol_group
                           END AS symbol_code,
                           CASE symbol_group
                             WHEN 'BR' THEN 'Нефть Brent'
                             WHEN 'NG' THEN 'Природный газ'
                             WHEN 'CNY' THEN 'Юань'
                             WHEN 'USD' THEN 'Доллар'
                             WHEN 'GOLD' THEN 'Золото'
                           END AS instrument_name,
                           symbol_group,side_code,candidate_code,pairs,oos_pairs,
                           candidate_expectancy_r,placebo_expectancy_r,
                           delta_expectancy_r,delta_lower_bound_r,
                           placebo_passed,plateau_passed,recommendation_status,generated_at
                    FROM ranked
                    WHERE evidence_rank=1
                    ORDER BY (pairs >= 10) DESC,placebo_passed DESC,
                             delta_lower_bound_r DESC NULLS LAST,
                             pairs DESC,symbol_group,side_code
                    LIMIT 12
                """)
                shadow_dynamics = [dict(row) for row in cursor.fetchall()]

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
            "promotion_summary": promotion_summary,
            "process": process,
            "constraint": constraint,
            "next_action": next_action,
            "nearest": nearest,
            "branch_plan": branch_plan,
            "command_state": command_state,
            "recent_jobs": recent_jobs,
            "freshness": freshness,
            "data_quality_summary": data_quality_summary,
            "session_status": session_status,
            "market_event_risk": market_event_risk,
            "market_shock_gate": market_shock_gate,
            "manual_symbol": str((nearest or {}).get("symbol") or "BRQ6@RTSX"),
            "hierarchy": hierarchy,
            "hierarchy_nearest": hierarchy_nearest,
            "hierarchy_top_exact": hierarchy_top_exact,
            "asset_branches": asset_branches,
            "cny_spot_controls": cny_spot_controls,
            "universe_summary": universe_summary,
            "recent_trade_events": recent_trade_events,
            "entry_exit_recommendations": entry_exit_recommendations,
            "adaptive_policy_families": adaptive_policy_families,
            "v5_oos_evidence": v5_oos_evidence,
            "v5_oos_runs": v5_oos_runs,
            "market_regime_context": market_regime_context,
            "market_regime_shadow_variants": market_regime_shadow_variants,
            "shadow_dynamics": shadow_dynamics,
            "raw_shadow_dynamics": raw_shadow_dynamics,
            "signal_funnel_stages": signal_funnel_stages,
            "signal_funnel_reasons": signal_funnel_reasons,
        }
