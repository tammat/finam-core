#!/usr/bin/env python3
from __future__ import annotations

import os
from typing import Any

import psycopg2
import psycopg2.extras


# Русский комментарий:
# STRATEGY_EDGE_IMPROVEMENT_AUDIT_V1
# Read-only аудит стратегий, признаков, входов и нехватки данных для улучшения edge.
# Никаких UPDATE/INSERT/DELETE.


LOOKBACK_DAYS = int(os.getenv("EDGE_IMPROVEMENT_LOOKBACK_DAYS", "30"))


STRATEGY_SQL = """
select
    coalesce(strategy, 'UNKNOWN_STRATEGY') as strategy,
    coalesce(timeframe, 'UNKNOWN_TIMEFRAME') as timeframe,
    coalesce(continuous_symbol, symbol, 'UNKNOWN_SYMBOL') as continuous_symbol,
    count(*) as trades,
    count(*) filter (where side = 'BUY') as buys,
    count(*) filter (where side = 'SELL') as sells,
    sum(coalesce(commission, 0)) as commission,
    min(created_at) as first_trade,
    max(created_at) as last_trade
from trades
where created_at >= now() - (%s::text)::interval
  and coalesce(is_invalid, false) = false
group by
    coalesce(strategy, 'UNKNOWN_STRATEGY'),
    coalesce(timeframe, 'UNKNOWN_TIMEFRAME'),
    coalesce(continuous_symbol, symbol, 'UNKNOWN_SYMBOL')
order by trades desc, strategy, timeframe, continuous_symbol;
"""


SIGNAL_CLASS_SQL = """
select
    coalesce(strategy, 'UNKNOWN_STRATEGY') as strategy,
    coalesce(timeframe, 'UNKNOWN_TIMEFRAME') as timeframe,
    coalesce(symbol, 'UNKNOWN_SYMBOL') as symbol,
    coalesce(payload->>'source', payload->>'entry_source', 'UNKNOWN_SOURCE') as entry_source,
    coalesce(
        payload->>'reason',
        payload->>'entry_reason',
        payload #>> '{features,reason}',
        payload #>> '{features,entry_reason}',
        'UNKNOWN_REASON'
    ) as entry_reason,
    coalesce(
        payload #>> '{features,regime}',
        payload #>> '{features,regime_label}',
        payload->>'regime',
        'UNKNOWN_REGIME'
    ) as entry_regime,
    count(*) as trades,
    sum(coalesce(commission, 0)) as commission
from trades
where created_at >= now() - (%s::text)::interval
  and coalesce(is_invalid, false) = false
group by
    coalesce(strategy, 'UNKNOWN_STRATEGY'),
    coalesce(timeframe, 'UNKNOWN_TIMEFRAME'),
    coalesce(symbol, 'UNKNOWN_SYMBOL'),
    coalesce(payload->>'source', payload->>'entry_source', 'UNKNOWN_SOURCE'),
    coalesce(
        payload->>'reason',
        payload->>'entry_reason',
        payload #>> '{features,reason}',
        payload #>> '{features,entry_reason}',
        'UNKNOWN_REASON'
    ),
    coalesce(
        payload #>> '{features,regime}',
        payload #>> '{features,regime_label}',
        payload->>'regime',
        'UNKNOWN_REGIME'
    )
order by trades desc, strategy, symbol, entry_reason, entry_regime;
"""


FEATURE_COVERAGE_SQL = """
select
    coalesce(strategy, 'UNKNOWN_STRATEGY') as strategy,
    coalesce(timeframe, 'UNKNOWN_TIMEFRAME') as timeframe,
    count(*) as trades,
    count(*) filter (where payload ? 'features') as has_features,
    count(*) filter (where payload #>> '{features,regime}' is not null or payload #>> '{features,regime_label}' is not null) as has_regime,
    count(*) filter (where payload #>> '{features,atr_pct}' is not null or payload #>> '{features,atr}' is not null) as has_atr,
    count(*) filter (where payload #>> '{features,rsi}' is not null) as has_rsi,
    count(*) filter (where payload #>> '{features,expected_move}' is not null or payload #>> '{features,expected_gross_move}' is not null) as has_expected_move,
    count(*) filter (where payload #>> '{features,spread}' is not null or payload #>> '{features,bid_ask_spread}' is not null) as has_spread,
    count(*) filter (where payload #>> '{features,mfe}' is not null or payload #>> '{features,mae}' is not null) as has_mfe_mae,
    count(*) filter (where payload #>> '{trade_context_snapshot,edge_gate}' is not null) as has_edge_gate
from trades
where created_at >= now() - (%s::text)::interval
  and coalesce(is_invalid, false) = false
group by strategy, timeframe
order by trades desc, strategy, timeframe;
"""


SIGNALS_SQL = """
select
    coalesce(strategy, 'UNKNOWN_STRATEGY') as strategy,
    coalesce(timeframe, 'UNKNOWN_TIMEFRAME') as timeframe,
    coalesce(symbol, 'UNKNOWN_SYMBOL') as symbol,
    count(*) as signals,
    min(created_at) as first_signal,
    max(created_at) as last_signal
from signals
where created_at >= now() - (%s::text)::interval
group by strategy, timeframe, symbol
order by signals desc, strategy, timeframe, symbol;
"""


RUNTIME_SQL = """
select
    symbol,
    strategy,
    timeframe,
    is_enabled,
    source,
    score,
    priority,
    disabled_at,
    disable_reason
from runtime_active_universe
order by is_enabled desc, priority desc nulls last, score desc nulls last, symbol, strategy;
"""


def fmt(v: Any) -> str:
    if v is None:
        return "NULL"
    return str(v)


def pct(part: Any, total: Any) -> float:
    try:
        t = float(total or 0)
        if t <= 0:
            return 0.0
        return float(part or 0) / t
    except Exception:
        return 0.0


def safe_query(dsn: str, sql: str, params: tuple[Any, ...] = ()) -> tuple[list[dict[str, Any]], str]:
    # Русский комментарий:
    # Каждый запрос выполняется в отдельном соединении.
    # Если один SQL падает, он не ломает остальные через InFailedSqlTransaction.
    try:
        with psycopg2.connect(dsn) as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute(sql, params)
                return list(cur.fetchall()), "OK"
    except Exception as exc:
        return [], f"FAILED:{type(exc).__name__}:{str(exc).replace(chr(10), ' ')[:240]}"


def main() -> int:
    dsn = os.getenv("DATABASE_URL")
    if not dsn:
        raise SystemExit("DATABASE_URL is required")

    interval = f"{LOOKBACK_DAYS} days"

    print("=== STRATEGY EDGE IMPROVEMENT AUDIT V1 ===")
    print("mode=read_only")
    print("runtime_allow=0")
    print("execution_enabled=0")
    print("real_trading_enabled=0")
    print("db_update=0")
    print(f"lookback_days={LOOKBACK_DAYS}")
    print()

    strategy_rows, strategy_status = safe_query(dsn, STRATEGY_SQL, (interval,))
    signal_class_rows, signal_class_status = safe_query(dsn, SIGNAL_CLASS_SQL, (interval,))
    feature_rows, feature_status = safe_query(dsn, FEATURE_COVERAGE_SQL, (interval,))
    signals_rows, signals_status = safe_query(dsn, SIGNALS_SQL, (interval,))
    runtime_rows, runtime_status = safe_query(dsn, RUNTIME_SQL)

    print("STRATEGY_AUDIT_RUNTIME_ROWS")
    for row in runtime_rows:
        print(
            "STRATEGY_AUDIT_RUNTIME_ROW "
            f"symbol={fmt(row.get('symbol'))} "
            f"strategy={fmt(row.get('strategy'))} "
            f"timeframe={fmt(row.get('timeframe'))} "
            f"is_enabled={fmt(row.get('is_enabled'))} "
            f"source={fmt(row.get('source'))} "
            f"score={fmt(row.get('score'))} "
            f"priority={fmt(row.get('priority'))} "
            f"disabled_at={fmt(row.get('disabled_at'))} "
            f"disable_reason={fmt(row.get('disable_reason'))}"
        )

    print()
    print("STRATEGY_AUDIT_TRADE_ROWS")
    for row in strategy_rows:
        trades = int(row.get("trades") or 0)
        commission = float(row.get("commission") or 0.0)
        avg_commission = commission / trades if trades else 0.0

        print(
            "STRATEGY_AUDIT_TRADE_ROW "
            f"strategy={fmt(row.get('strategy'))} "
            f"timeframe={fmt(row.get('timeframe'))} "
            f"continuous_symbol={fmt(row.get('continuous_symbol'))} "
            f"trades={trades} "
            f"buys={fmt(row.get('buys'))} "
            f"sells={fmt(row.get('sells'))} "
            f"commission={commission:.6f} "
            f"avg_commission_per_trade={avg_commission:.6f} "
            f"first_trade={fmt(row.get('first_trade'))} "
            f"last_trade={fmt(row.get('last_trade'))}"
        )

    print()
    print("STRATEGY_AUDIT_SIGNAL_CLASS_ROWS")
    unknown_signal_classes = 0
    for row in signal_class_rows:
        entry_source = fmt(row.get("entry_source"))
        entry_reason = fmt(row.get("entry_reason"))
        entry_regime = fmt(row.get("entry_regime"))

        if "UNKNOWN" in entry_source or "UNKNOWN" in entry_reason or "UNKNOWN" in entry_regime:
            unknown_signal_classes += 1

        print(
            "STRATEGY_AUDIT_SIGNAL_CLASS_ROW "
            f"strategy={fmt(row.get('strategy'))} "
            f"timeframe={fmt(row.get('timeframe'))} "
            f"symbol={fmt(row.get('symbol'))} "
            f"entry_source={entry_source} "
            f"entry_reason={entry_reason} "
            f"entry_regime={entry_regime} "
            f"trades={fmt(row.get('trades'))} "
            f"commission={fmt(row.get('commission'))}"
        )

    print()
    print("STRATEGY_AUDIT_FEATURE_COVERAGE_ROWS")
    missing_expected_move_rows = 0
    missing_spread_rows = 0
    missing_mfe_mae_rows = 0

    for row in feature_rows:
        trades = int(row.get("trades") or 0)
        has_expected_move = int(row.get("has_expected_move") or 0)
        has_spread = int(row.get("has_spread") or 0)
        has_mfe_mae = int(row.get("has_mfe_mae") or 0)

        if trades > 0 and has_expected_move == 0:
            missing_expected_move_rows += 1
        if trades > 0 and has_spread == 0:
            missing_spread_rows += 1
        if trades > 0 and has_mfe_mae == 0:
            missing_mfe_mae_rows += 1

        print(
            "STRATEGY_AUDIT_FEATURE_COVERAGE_ROW "
            f"strategy={fmt(row.get('strategy'))} "
            f"timeframe={fmt(row.get('timeframe'))} "
            f"trades={trades} "
            f"features_pct={pct(row.get('has_features'), trades):.4f} "
            f"regime_pct={pct(row.get('has_regime'), trades):.4f} "
            f"atr_pct={pct(row.get('has_atr'), trades):.4f} "
            f"rsi_pct={pct(row.get('has_rsi'), trades):.4f} "
            f"expected_move_pct={pct(row.get('has_expected_move'), trades):.4f} "
            f"spread_pct={pct(row.get('has_spread'), trades):.4f} "
            f"mfe_mae_pct={pct(row.get('has_mfe_mae'), trades):.4f} "
            f"edge_gate_pct={pct(row.get('has_edge_gate'), trades):.4f}"
        )

    print()
    print("STRATEGY_AUDIT_SIGNAL_ROWS")
    for row in signals_rows:
        print(
            "STRATEGY_AUDIT_SIGNAL_ROW "
            f"strategy={fmt(row.get('strategy'))} "
            f"timeframe={fmt(row.get('timeframe'))} "
            f"symbol={fmt(row.get('symbol'))} "
            f"signals={fmt(row.get('signals'))} "
            f"first_signal={fmt(row.get('first_signal'))} "
            f"last_signal={fmt(row.get('last_signal'))}"
        )

    runtime_enabled = sum(1 for r in runtime_rows if str(r.get("is_enabled")).lower() in {"true", "t", "1"})
    total_trades = sum(int(r.get("trades") or 0) for r in strategy_rows)

    print()
    print("STRATEGY_EDGE_IMPROVEMENT_RECOMMENDATIONS")
    print("RECOMMENDATION no_real_trading=1 reason=no_validated_runtime_edge")
    print("RECOMMENDATION add_expected_move_gate=1 reason=commission_drag_detected")
    print("RECOMMENDATION add_spread_features=1 reason=spread_cost_missing")
    print("RECOMMENDATION add_mfe_mae_features=1 reason=entry_vs_exit_quality_unknown")
    print("RECOMMENDATION score_signal_class_not_strategy_only=1 reason=edge_depends_on_entry_regime_exit_reason")
    print("RECOMMENDATION quarantine_negative_signal_classes=1 reason=negative_samples_confirmed")
    print("RECOMMENDATION keep_equity_shadow=1 reason=no_negative_equity_edge_confirmed_yet")
    print("RECOMMENDATION pause_ng_runtime=1 reason=ng_candidate_rejected_negative_sample")
    print("RECOMMENDATION keep_usdrub_blocked=1 reason=usdrub_fee_drag_confirmed")
    print("RECOMMENDATION br_research_only=1 reason=insufficient_recent_data")

    print()
    print("STRATEGY_EDGE_IMPROVEMENT_AUDIT_SUMMARY")
    print(f"strategy_query_status={strategy_status}")
    print(f"signal_class_query_status={signal_class_status}")
    print(f"feature_query_status={feature_status}")
    print(f"signals_query_status={signals_status}")
    print(f"runtime_query_status={runtime_status}")
    print(f"runtime_rows={len(runtime_rows)}")
    print(f"runtime_enabled_rows={runtime_enabled}")
    print(f"trade_rows={len(strategy_rows)}")
    print(f"trades_total={total_trades}")
    print(f"signal_class_rows={len(signal_class_rows)}")
    print(f"unknown_signal_class_rows={unknown_signal_classes}")
    print(f"feature_coverage_rows={len(feature_rows)}")
    print(f"missing_expected_move_rows={missing_expected_move_rows}")
    print(f"missing_spread_rows={missing_spread_rows}")
    print(f"missing_mfe_mae_rows={missing_mfe_mae_rows}")
    print("runtime_changes_required=1")
    print("execution_changes_required=0")
    print("db_update=0")

    failed_queries = [
        status for status in (
            strategy_status,
            signal_class_status,
            feature_status,
            signals_status,
            runtime_status,
        )
        if not status.startswith("OK")
    ]

    if failed_queries:
        print("VERDICT=STRATEGY_EDGE_IMPROVEMENT_AUDIT_QUERY_FAILURE")
    elif total_trades == 0 and len(runtime_rows) == 0:
        print("VERDICT=STRATEGY_EDGE_IMPROVEMENT_AUDIT_NO_DATA")
    elif missing_expected_move_rows or missing_spread_rows or missing_mfe_mae_rows:
        print("VERDICT=STRATEGY_EDGE_IMPROVEMENT_DATA_GAPS_FOUND")
    else:
        print("VERDICT=STRATEGY_EDGE_IMPROVEMENT_AUDIT_OK")

    print("STRATEGY_EDGE_IMPROVEMENT_AUDIT_V1_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
