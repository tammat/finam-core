#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations

import argparse
from collections import defaultdict, deque
from datetime import timezone, timedelta
import os
import re

import psycopg
from psycopg.rows import dict_row
from psycopg.types.json import Jsonb

from finam_core.analytics.pnl_units import PnlUnitSpec, gross_pnl_rub


MSK = timezone(timedelta(hours=3))


DDL = "SELECT 1"  # Структура управляется только версионированными миграциями.


def session_ru(hour: int | None) -> str:
    if hour is None:
        return "неизвестно"
    if 7 <= hour < 10:
        return "утро_мск"
    if 10 <= hour < 15:
        return "московская_середина"
    if 15 <= hour < 19:
        return "вечерняя_сессия"
    return "вне_основной_сессии"


def norm_strategy(symbol: str, raw: str | None) -> str:
    invalid = {"", "UNKNOWN", "UNKNOWN_STRATEGY", "UNASSIGNED", "DEFAULT"}
    if raw and str(raw).strip().upper() not in invalid:
        return raw
    # Назначения стратегий принадлежат БД. Материализатор не должен
    # самостоятельно подменять отсутствие контракта общим fallback.
    return "UNASSIGNED"


def is_assigned_strategy(raw: str | None) -> bool:
    return str(raw or "").strip().upper() not in {
        "", "UNKNOWN", "UNKNOWN_STRATEGY", "UNASSIGNED", "DEFAULT"
    }


def root_symbol_for(symbol: str, active_contract: str | None) -> str:
    """Корень фьючерса берётся из контракта, а не из устаревшего тикера."""
    source = str(active_contract or symbol).upper()
    token, _, board = source.partition("@")
    # Цифра в тикере акции (например X5) является частью инструмента, а не
    # кодом месяца/года фьючерса.
    if board == "MISX":
        return token
    if token.startswith("BR"):
        return "BR"
    if token.startswith("NG"):
        return "NG"
    match = re.match(r"[A-Z]+", token)
    return match.group(0) if match else token


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser()
    # Русский комментарий: общие SYMBOL/SYMBOLS принадлежат торговому контуру.
    # Планировщик материализации не должен случайно наследовать их и вечно
    # пересчитывать только один инструмент. Для ручного ограничения оставляем
    # CLI и отдельное, явно именованное окружение этого задания.
    p.add_argument("--symbol", default=os.getenv("PAPER_MATERIALIZER_SYMBOL"))
    p.add_argument("--symbols", default=os.getenv("PAPER_MATERIALIZER_SYMBOLS"))
    p.add_argument("--symbol-pattern", default=os.getenv("PAPER_MATERIALIZER_SYMBOL_PATTERN"))
    p.add_argument("--from-ts", default=os.getenv("PAPER_MATERIALIZER_FROM_TS"))
    p.add_argument("--to-ts", default=os.getenv("PAPER_MATERIALIZER_TO_TS"))
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--apply", action="store_true")
    p.add_argument("--replace", action="store_true")
    return p.parse_args()


def load_symbols(conn, args: argparse.Namespace) -> list[str]:
    # Русский комментарий: явный --symbol имеет приоритет над SYMBOLS из окружения.
    if args.symbol:
        return [args.symbol.strip()]
    if args.symbols:
        return [x.strip() for x in args.symbols.split(",") if x.strip()]

    if args.symbol_pattern:
        rows = conn.execute(
            """
            SELECT DISTINCT symbol
            FROM fills
            WHERE symbol ~ %s
            ORDER BY symbol
            """,
            (args.symbol_pattern,),
        ).fetchall()
        return [r["symbol"] for r in rows]

    rows = conn.execute(
        """
        WITH current_fill_state AS (
            SELECT f.symbol,count(*)::bigint AS fill_count,max(f.ts) AS max_fill_ts
            FROM fills f
            WHERE f.qty>0 AND f.price>0
              AND NOT EXISTS (
                SELECT 1 FROM analytics.paper_fill_anomaly_quarantine_v1 q
                WHERE q.enabled AND q.symbol=f.symbol
                  AND (q.side IS NULL OR upper(q.side)=upper(f.side))
                  AND f.ts>=q.range_start AND f.ts<q.range_end
              )
            GROUP BY f.symbol
        )
        SELECT s.symbol
        FROM current_fill_state s
        LEFT JOIN analytics.paper_closed_trade_materializer_checkpoint_v2 c
          ON c.symbol=s.symbol
        WHERE c.symbol IS NULL OR c.fill_count<>s.fill_count
           OR c.max_fill_ts IS DISTINCT FROM s.max_fill_ts
           OR EXISTS (
               SELECT 1 FROM closed_trades ct
               WHERE ct.symbol=s.symbol AND ct.source='paper_fill_materializer_v2'
                 AND ct.payload->'pnl_units'->>'version' IS DISTINCT FROM 'PNL_UNITS_V2_RUB'
           )
        ORDER BY s.symbol
        """
    ).fetchall()
    return [r["symbol"] for r in rows]


def save_checkpoint(conn, symbol: str) -> None:
    conn.execute(
        """
        INSERT INTO analytics.paper_closed_trade_materializer_checkpoint_v2(
            symbol,fill_count,max_fill_ts,last_success_at,updated_at
        )
        SELECT f.symbol,count(*)::bigint,max(f.ts),clock_timestamp(),clock_timestamp()
        FROM fills f
        WHERE f.symbol=%s AND f.qty>0 AND f.price>0
          AND NOT EXISTS (
            SELECT 1 FROM analytics.paper_fill_anomaly_quarantine_v1 q
            WHERE q.enabled AND q.symbol=f.symbol
              AND (q.side IS NULL OR upper(q.side)=upper(f.side))
              AND f.ts>=q.range_start AND f.ts<q.range_end
          )
        GROUP BY f.symbol
        ON CONFLICT(symbol) DO UPDATE SET
          fill_count=excluded.fill_count,max_fill_ts=excluded.max_fill_ts,
          last_success_at=excluded.last_success_at,updated_at=excluded.updated_at
        """,
        (symbol,),
    )


def resolve_scope_at_entry(conn, symbol: str, entry_ts):
    """Resolve the portfolio cohort that was active when the position opened."""
    row = conn.execute(
        """
        SELECT scope_code
        FROM analytics.paper_portfolio_scope_v1
        WHERE enabled
          AND asset_group = CASE
              WHEN upper(%s) LIKE '%%@MISX' THEN 'EQUITY'
              WHEN upper(%s) LIKE '%%@RTSX' THEN 'FUTURES'
              ELSE NULL
          END
          AND starts_at <= %s
        ORDER BY starts_at DESC
        LIMIT 1
        """,
        (symbol, symbol, entry_ts),
    ).fetchone()
    return (row or {}).get("scope_code") if isinstance(row, dict) else (row[0] if row else None)


def load_fills(conn, symbol: str, args: argparse.Namespace) -> list[dict]:
    params = [symbol]
    where = [
        "f.symbol = %s",
        "f.qty > 0",
        "f.price > 0",
        """NOT EXISTS (
            SELECT 1
            FROM analytics.paper_fill_anomaly_quarantine_v1 q
            WHERE q.enabled
              AND q.symbol=f.symbol
              AND (q.side IS NULL OR upper(q.side)=upper(f.side))
              AND f.ts>=q.range_start AND f.ts<q.range_end
        )""",
    ]

    if args.from_ts:
        where.append("f.ts >= %s")
        params.append(args.from_ts)
    if args.to_ts:
        where.append("f.ts < %s")
        params.append(args.to_ts)

    sql = f"""
        SELECT
            f.fill_id,
            f.ts,
            f.symbol,
            f.side,
            f.qty,
            f.price,
            COALESCE(f.commission, 0) AS commission,
            COALESCE(f.portfolio_scope, sf.portfolio_scope) AS fill_scope,
            sf.signal_id,
            sf.side AS signal_side,
            COALESCE(
                CASE WHEN upper(COALESCE(s.strategy,'')) NOT IN
                    ('','UNKNOWN','UNKNOWN_STRATEGY','UNASSIGNED','DEFAULT')
                     THEN s.strategy END,
                CASE WHEN upper(COALESCE(t.strategy,'')) NOT IN
                    ('','UNKNOWN','UNKNOWN_STRATEGY','UNASSIGNED','DEFAULT')
                     THEN t.strategy END,
                CASE WHEN upper(COALESCE(NULLIF(t.payload->>'strategy',''),'')) NOT IN
                    ('','UNKNOWN','UNKNOWN_STRATEGY','UNASSIGNED','DEFAULT')
                     THEN NULLIF(t.payload->>'strategy','') END,
                a.strategy_code
            ) AS signal_strategy,
            COALESCE(NULLIF(s.timeframe,''),NULLIF(t.timeframe,''),NULLIF(t.payload->>'timeframe','')) AS signal_timeframe,
            COALESCE(NULLIF(s.horizon,''),NULLIF(t.payload->>'horizon','')) AS signal_horizon,
            COALESCE(NULLIF(s.regime,''),NULLIF(t.payload->>'regime',''),
                     NULLIF(t.payload->'features'->>'regime','')) AS signal_regime,
            COALESCE(NULLIF(t.continuous_symbol,''),NULLIF(t.payload->>'continuous_symbol',''),
                     NULLIF(t.payload->>'root_symbol',''),f.symbol) AS signal_contract,
            COALESCE(NULLIF(s.payload->>'exit_rule',''),NULLIF(t.payload->>'exit_rule',''),
                     NULLIF(t.payload->>'position_rule',''),
                     NULLIF(t.payload->'exit_policy'->>'code',''),
                     CASE WHEN t.payload ? 'stop_price'
                                OR t.payload ? 'take_profit'
                                OR t.payload->'features' ? 'stop'
                                OR t.payload->'features' ? 'take'
                          THEN 'STOP_TAKE'
                     END,'UNSPECIFIED') AS signal_exit_rule,
            s.stop_loss AS signal_stop_loss,
            s.take_profit AS signal_take_profit,
            NULLIF(t.payload->>'reason','') AS signal_reason,
            NULLIF(t.payload->>'source','') AS signal_source,
            COALESCE(NULLIF(t.payload->>'regime_source_version',''),
                     NULLIF(s.payload->'features'->>'regime_source_version','')) AS regime_source_version,
            COALESCE(NULLIF(t.payload->>'regime_timeframe',''),
                     NULLIF(s.payload->'features'->>'regime_timeframe',''),
                     NULLIF(s.timeframe,''),NULLIF(t.timeframe,'')) AS regime_timeframe,
            COALESCE(NULLIF(t.payload->>'regime_bar_ts',''),
                     NULLIF(s.payload->'features'->>'regime_bar_ts','')) AS regime_bar_ts,
            COALESCE(NULLIF(t.payload->>'regime_atr_pct',''),
                     NULLIF(s.payload->'features'->>'regime_atr_pct','')) AS regime_atr_pct,
            COALESCE(NULLIF(t.payload->>'regime_atr_percentile',''),
                     NULLIF(s.payload->'features'->>'regime_atr_percentile','')) AS regime_atr_percentile,
            COALESCE(NULLIF(t.payload->>'regime_adx',''),
                     NULLIF(s.payload->'features'->>'regime_adx','')) AS regime_adx,
            COALESCE(NULLIF(t.payload->>'regime_normalized_slope',''),
                     NULLIF(s.payload->'features'->>'regime_normalized_slope','')) AS regime_normalized_slope,
            COALESCE(NULLIF(t.payload->>'regime_confirmed_bars',''),
                     NULLIF(s.payload->'features'->>'regime_confirmed_bars','')) AS regime_confirmed_bars,
            s.payload AS signal_payload,
            t.payload AS trade_payload
        FROM fills f
        LEFT JOIN signal_fills sf ON sf.fill_id = f.fill_id
        LEFT JOIN LATERAL (
            SELECT strategy, timeframe, horizon, regime, stop_loss, take_profit, payload
            FROM signals
            WHERE signal_id = sf.signal_id
            ORDER BY ts DESC, id DESC
            LIMIT 1
        ) s ON true
        LEFT JOIN LATERAL (
            SELECT strategy, timeframe, continuous_symbol, payload
            FROM trades
            WHERE fill_id = f.fill_id
            ORDER BY ts DESC, id DESC
            LIMIT 1
        ) t ON true
        LEFT JOIN LATERAL (
            SELECT strategy_code
            FROM analytics.runtime_strategy_assignment_v1
            WHERE symbol=f.symbol AND enabled
            ORDER BY priority DESC, updated_at DESC
            LIMIT 1
        ) a ON true
        WHERE {' AND '.join(where)}
        ORDER BY f.ts, f.fill_id
    """
    return list(conn.execute(sql, tuple(params)).fetchall())


def resolve_pnl_unit_spec(conn, symbol: str) -> PnlUnitSpec:
    symbol_u = str(symbol).upper()
    base = symbol_u.split("@", 1)[0]
    if symbol_u.endswith("@RTSX"):
        row = conn.execute(
            """SELECT tick_size::float8,tick_value::float8,source_version
               FROM analytics.market_contract_spec_v1
               WHERE is_active AND (symbol=%s OR symbol=%s)
               ORDER BY (symbol=%s) DESC,valid_from DESC LIMIT 1""",
            (symbol_u, f"{root_symbol_for(symbol_u, symbol_u)}@RTSX", symbol_u),
        ).fetchone()
        tick_size = float((row or {}).get("tick_size") or 0.0)
        tick_value = float((row or {}).get("tick_value") or 0.0)
        if tick_size <= 0 or tick_value <= 0:
            raise RuntimeError(f"PNL_UNIT_FUTURES_SPEC_MISSING:{symbol_u}")
        return PnlUnitSpec(symbol_u, "FUTURES", tick_value / tick_size,
                           source=str(row.get("source_version") or "MARKET_CONTRACT_SPEC_V1"))

    row = conn.execute(
        """SELECT lot_size::float8,source_version
           FROM analytics.market_contract_spec_v1
           WHERE symbol=%s AND is_active
           ORDER BY valid_from DESC LIMIT 1""",
        (symbol_u,),
    ).fetchone()
    lot_size = float((row or {}).get("lot_size") or 0.0)
    if lot_size <= 0:
        raise RuntimeError(f"PNL_UNIT_EQUITY_SPEC_MISSING:{symbol_u}")
    return PnlUnitSpec(symbol_u, "EQUITY", lot_size,
                       source=str(row.get("source_version") or "MARKET_CONTRACT_SPEC_V1"))


def reconstruct(symbol: str, fills: list[dict], pnl_spec: PnlUnitSpec | None = None) -> list[dict]:
    # Positions from different research cohorts must never offset each other.
    # In particular, a FRESH_V4 exit cannot consume an old unscoped Paper fill.
    open_longs_by_scope: dict[str | None, deque] = defaultdict(deque)
    open_shorts_by_scope: dict[str | None, deque] = defaultdict(deque)
    closed = []
    exit_batch_counter: dict[str, int] = {}
    pnl_spec = pnl_spec or PnlUnitSpec(symbol, "LEGACY_TEST", 1.0, source="LEGACY_TEST_LINEAR")

    for f in fills:
        fill_id = str(f["fill_id"])
        side = str(f["side"]).upper()
        qty = float(f["qty"] or 0.0)
        price = float(f["price"] or 0.0)
        ts = f["ts"]
        signal_id = f.get("signal_id")
        fill_scope = f.get("fill_scope")
        open_longs = open_longs_by_scope[fill_scope]
        open_shorts = open_shorts_by_scope[fill_scope]

        if side == "BUY":
            remaining = qty

            while remaining > 0 and open_shorts:
                s = open_shorts[0]
                matched = min(remaining, s["qty"])
                pnl = gross_pnl_rub(side="SHORT", entry_price=s["price"], exit_price=price,
                                    qty=matched, spec=pnl_spec)
                trade = build_trade(symbol, "SHORT", matched, s, f, pnl, pnl_spec)
                batch_key = str(f.get("fill_id"))
                exit_batch_counter[batch_key] = exit_batch_counter.get(batch_key, 0) + 1
                trade["raw"]["exit_batch_key"] = batch_key
                trade["raw"]["exit_batch_trade_index"] = exit_batch_counter[batch_key]
                trade["raw"]["exit_batch_total_qty"] = float(qty)
                closed.append(trade)
                s["qty"] -= matched
                remaining -= matched
                if s["qty"] <= 1e-12:
                    open_shorts.popleft()

            if remaining > 1e-12:
                open_longs.append({
                    "qty": remaining,
                    "price": price,
                    "ts": ts,
                    "fill_id": fill_id,
                    "signal_id": signal_id,
                    "portfolio_scope": fill_scope,
                    "strategy": f.get("signal_strategy"),
                    "timeframe": f.get("signal_timeframe"),
                    "horizon": f.get("signal_horizon"),
                    "regime": f.get("signal_regime"),
                    "active_contract": f.get("signal_contract"),
                    "exit_rule": f.get("signal_exit_rule"),
                    "stop_price": f.get("signal_stop_loss"),
                    "take_price": f.get("signal_take_profit"),
                    "signal_payload": f.get("signal_payload"),
                    "trade_payload": f.get("trade_payload"),
                    "regime_source_version": f.get("regime_source_version"),
                    "regime_timeframe": f.get("regime_timeframe"),
                    "regime_bar_ts": f.get("regime_bar_ts"),
                    "regime_atr_pct": f.get("regime_atr_pct"),
                    "regime_atr_percentile": f.get("regime_atr_percentile"),
                    "regime_adx": f.get("regime_adx"),
                    "regime_normalized_slope": f.get("regime_normalized_slope"),
                    "regime_confirmed_bars": f.get("regime_confirmed_bars"),
                    "commission_per_unit": float(f.get("commission") or 0.0) / qty,
                })

        elif side == "SELL":
            remaining = qty

            while remaining > 0 and open_longs:
                b = open_longs[0]
                matched = min(remaining, b["qty"])
                pnl = gross_pnl_rub(side="LONG", entry_price=b["price"], exit_price=price,
                                    qty=matched, spec=pnl_spec)
                trade = build_trade(symbol, "LONG", matched, b, f, pnl, pnl_spec)
                batch_key = str(f.get("fill_id"))
                exit_batch_counter[batch_key] = exit_batch_counter.get(batch_key, 0) + 1
                trade["raw"]["exit_batch_key"] = batch_key
                trade["raw"]["exit_batch_trade_index"] = exit_batch_counter[batch_key]
                trade["raw"]["exit_batch_total_qty"] = float(qty)
                closed.append(trade)
                b["qty"] -= matched
                remaining -= matched
                if b["qty"] <= 1e-12:
                    open_longs.popleft()

            if remaining > 1e-12:
                open_shorts.append({
                    "qty": remaining,
                    "price": price,
                    "ts": ts,
                    "fill_id": fill_id,
                    "signal_id": signal_id,
                    "portfolio_scope": fill_scope,
                    "strategy": f.get("signal_strategy"),
                    "timeframe": f.get("signal_timeframe"),
                    "horizon": f.get("signal_horizon"),
                    "regime": f.get("signal_regime"),
                    "active_contract": f.get("signal_contract"),
                    "exit_rule": f.get("signal_exit_rule"),
                    "stop_price": f.get("signal_stop_loss"),
                    "take_price": f.get("signal_take_profit"),
                    "signal_payload": f.get("signal_payload"),
                    "trade_payload": f.get("trade_payload"),
                    "regime_source_version": f.get("regime_source_version"),
                    "regime_timeframe": f.get("regime_timeframe"),
                    "regime_bar_ts": f.get("regime_bar_ts"),
                    "regime_atr_pct": f.get("regime_atr_pct"),
                    "regime_atr_percentile": f.get("regime_atr_percentile"),
                    "regime_adx": f.get("regime_adx"),
                    "regime_normalized_slope": f.get("regime_normalized_slope"),
                    "regime_confirmed_bars": f.get("regime_confirmed_bars"),
                    "commission_per_unit": float(f.get("commission") or 0.0) / qty,
                })

    batch_sizes: dict[str, int] = {}
    for t in closed:
        key = str(t["raw"].get("exit_batch_key") or "")
        if key:
            batch_sizes[key] = batch_sizes.get(key, 0) + 1

    for t in closed:
        key = str(t["raw"].get("exit_batch_key") or "")
        batch_size = batch_sizes.get(key, 1)
        t["raw"]["exit_batch_size"] = batch_size
        t["raw"]["exit_batch_is_batch"] = bool(batch_size > 1)

    return closed


def build_trade(symbol: str, trade_side: str, qty: float, entry: dict, exit_fill: dict,
                pnl: float, pnl_spec: PnlUnitSpec) -> dict:
    exit_ts = exit_fill["ts"]
    exit_msk = exit_ts.astimezone(MSK)
    entry_msk = entry["ts"].astimezone(MSK)
    strategy = norm_strategy(symbol, entry.get("strategy"))
    root_symbol = root_symbol_for(symbol, entry.get("active_contract"))
    entry_regime = entry.get("regime") or "UNKNOWN"
    regime_trend = next(
        (value for value in ("trend_up", "trend_down", "range") if entry_regime.startswith(value)),
        "UNKNOWN",
    )
    regime_vol = next(
        (value for value in ("low_vol", "normal_vol", "high_vol") if entry_regime.endswith(value)),
        "UNKNOWN",
    )
    entry_side = "BUY" if trade_side == "LONG" else "SELL"
    exit_regime = exit_fill.get("signal_regime") or entry_regime
    planned_exit_rule = entry.get("exit_rule") or "UNSPECIFIED"
    exit_payload = exit_fill.get("trade_payload") or exit_fill.get("signal_payload") or {}
    actual_exit_reason = str(exit_payload.get("reason") or exit_fill.get("signal_reason") or "UNVERIFIED_EXIT")
    reason_key = actual_exit_reason.lower()
    # Фактические закрытия храним в четырёх взаимоисключающих классах.
    # stall_exit является принудительным закрытием по истечению времени ожидания,
    # а не отдельной торговой целью.
    if "time_exit" in reason_key or "stall_exit" in reason_key:
        exit_rule = "TIME_EXIT"
    elif "trail" in reason_key:
        exit_rule = "TRAILING"
    elif "take_profit" in reason_key or "target" in reason_key or "take" in reason_key:
        exit_rule = "TARGET"
    elif "stop_loss" in reason_key or "stop" in reason_key:
        exit_rule = "STOP"
    else:
        exit_rule = "UNVERIFIED_EXIT"

    entry_signal_id = entry.get("signal_id")
    exit_signal_id = exit_fill.get("signal_id")

    trade_id = (
        f"{symbol}|{trade_side}|{entry.get('fill_id')}|"
        f"{exit_fill.get('fill_id')}|{qty:.8f}"
    )
    entry_commission = float(entry.get("commission_per_unit") or 0.0) * qty
    exit_fill_qty = float(exit_fill.get("qty") or qty)
    exit_commission = float(exit_fill.get("commission") or 0.0) * qty / exit_fill_qty
    commission = entry_commission + exit_commission

    return {
        "trade_id": trade_id,
        "symbol": symbol,
        "strategy": strategy,
        "side": trade_side,
        "qty": qty,
        "entry_ts": entry["ts"],
        "exit_ts": exit_ts,
        "entry_price": float(entry["price"]),
        "exit_price": float(exit_fill["price"]),
        "pnl_points": float(pnl),
        "commission": commission,
        "net_pnl": float(pnl) - commission,
        "entry_fill_id": entry.get("fill_id"),
        "exit_fill_id": exit_fill.get("fill_id"),
        "entry_signal_id": entry_signal_id,
        "exit_signal_id": exit_signal_id,
        "portfolio_scope": entry.get("portfolio_scope"),
        "exit_reason": exit_rule,
        "timeframe": entry.get("timeframe") or "LIVE",
        "horizon": entry.get("horizon") or "INTRADAY",
        "regime": entry_regime,
        "root_symbol": root_symbol,
        "entry_regime": entry_regime,
        "exit_regime": exit_regime,
        "active_contract": entry.get("active_contract") or symbol,
        "exit_rule": exit_rule,
        "hour_msk": exit_msk.hour,
        "weekday": exit_msk.strftime("%A"),
        "session": session_ru(exit_msk.hour),
        "source": "materialize_closed_trades_from_fills_v1",
        "raw": {
            "pnl_unit_version": "PNL_UNITS_V2_RUB",
            "pnl_currency": pnl_spec.currency,
            "price_to_rub_multiplier": pnl_spec.price_to_rub_multiplier,
            "pnl_spec_source": pnl_spec.source,
            "exit_side": exit_fill.get("side"),
            "exit_signal_side": exit_fill.get("signal_side"),
            "entry_session_msk": session_ru(entry_msk.hour),
            "active_contract": entry.get("active_contract") or symbol,
            "root_symbol": root_symbol,
            "entry_regime": entry_regime,
            "regime_trend": regime_trend,
            "regime_vol": regime_vol,
            "side": entry_side,
            "exit_regime": exit_regime,
            "exit_rule": exit_rule,
            "planned_exit_rule": planned_exit_rule,
            "actual_exit_reason": actual_exit_reason,
            "actual_exit_source": exit_fill.get("signal_source"),
            "entry_stop_price": entry.get("stop_price"),
            "entry_take_price": entry.get("take_price"),
            "regime_source_version": entry.get("regime_source_version"),
            "regime_timeframe": entry.get("regime_timeframe"),
            "regime_bar_ts": entry.get("regime_bar_ts"),
            "regime_atr_pct": entry.get("regime_atr_pct"),
            "regime_atr_percentile": entry.get("regime_atr_percentile"),
            "regime_adx": entry.get("regime_adx"),
            "regime_normalized_slope": entry.get("regime_normalized_slope"),
            "regime_confirmed_bars": entry.get("regime_confirmed_bars"),
        },
    }


def upsert_trades(conn, trades: list[dict]) -> int:
    n = 0
    for t in trades:
        conn.execute(
            """
            INSERT INTO analytics_closed_trades_v1 (
                trade_id, symbol, strategy, side, qty,
                entry_ts, exit_ts, entry_price, exit_price, pnl_points,
                entry_fill_id, exit_fill_id, entry_signal_id, exit_signal_id,
                exit_reason, hour_msk, weekday, session, source, raw,
                created_at, updated_at
            )
            VALUES (
                %(trade_id)s, %(symbol)s, %(strategy)s, %(side)s, %(qty)s,
                %(entry_ts)s, %(exit_ts)s, %(entry_price)s, %(exit_price)s, %(pnl_points)s,
                %(entry_fill_id)s, %(exit_fill_id)s, %(entry_signal_id)s, %(exit_signal_id)s,
                %(exit_reason)s, %(hour_msk)s, %(weekday)s, %(session)s, %(source)s, %(raw)s,
                now(), now()
            )
            ON CONFLICT (trade_id) DO UPDATE SET
                strategy = EXCLUDED.strategy,
                pnl_points = EXCLUDED.pnl_points,
                exit_reason = EXCLUDED.exit_reason,
                raw = EXCLUDED.raw,
                updated_at = now()
            """,
            {**t, "raw": Jsonb(t["raw"])},
        )
        n += 1
    return n


def upsert_canonical_trades(conn, trades: list[dict], legacy_cutoff, context_activated_at) -> int:
    """Записывает тот же факт закрытия в каноническую таблицу без дублей."""
    written = 0
    for t in trades:
        if legacy_cutoff is not None and t["exit_ts"] <= legacy_cutoff:
            continue
        portfolio_scope = t.get("portfolio_scope") or resolve_scope_at_entry(
            conn, t["symbol"], t["entry_ts"]
        )
        # Неназначенная сделка нужна для аудита (analytics_closed_trades_v1),
        # но не является допустимым фактом чистой V4/OOS-когорты.
        if str(portfolio_scope or "").startswith("FRESH_V4") and not is_assigned_strategy(
            t.get("strategy")
        ):
            continue
        cohort = portfolio_scope or ("FRESH_V2" if t["entry_ts"] >= context_activated_at else "LEGACY_DERIVED")
        result = conn.execute(
            """
            WITH claimed AS (
                INSERT INTO analytics.paper_closed_trade_identity_v2(
                    materialized_trade_id,entry_fill_id,exit_fill_id
                )
                SELECT %(trade_id)s,%(entry_fill_id)s,%(exit_fill_id)s
                WHERE NOT EXISTS (
                    SELECT 1 FROM closed_trades
                    WHERE payload->>'materialized_trade_id'=%(trade_id)s
                       OR (
                            payload->>'entry_fill_id'=%(entry_fill_id)s
                        AND payload->>'exit_fill_id'=%(exit_fill_id)s
                       )
                )
                ON CONFLICT(materialized_trade_id) DO NOTHING
                RETURNING materialized_trade_id
            )
            INSERT INTO closed_trades (
                signal_id, symbol, side, entry_ts, exit_ts, qty,
                entry_price, exit_price, gross_pnl, commission, net_pnl,
                horizon, strategy, regime, trade_source, payload,
                timeframe, source, opened_at, closed_at, holding_seconds,
                root_symbol, entry_regime, exit_regime, portfolio_scope
            )
            SELECT
                %(entry_signal_id)s, %(symbol)s, %(side)s, %(entry_ts)s, %(exit_ts)s, %(qty)s,
                %(entry_price)s, %(exit_price)s, %(pnl_points)s, %(commission)s, %(net_pnl)s,
                %(horizon)s, %(strategy)s, %(regime)s, 'paper', %(payload)s,
                %(timeframe)s, 'paper_fill_materializer_v2', %(entry_ts)s, %(exit_ts)s,
                greatest(0, extract(epoch FROM (%(exit_ts)s - %(entry_ts)s))::integer),
                %(root_symbol)s, %(entry_regime)s, %(exit_regime)s, %(portfolio_scope)s
            WHERE EXISTS (SELECT 1 FROM claimed)
            RETURNING id
            """,
            {**t, "portfolio_scope": portfolio_scope, "payload": Jsonb({
                "materialized_trade_id": t["trade_id"],
                "entry_fill_id": t["entry_fill_id"],
                "exit_fill_id": t["exit_fill_id"],
                "exit_signal_id": t["exit_signal_id"],
                "materializer": "paper_fill_materializer_v2",
                "pnl_units": {
                    "version": "PNL_UNITS_V2_RUB",
                    "currency": t["raw"]["pnl_currency"],
                    "price_to_rub_multiplier": t["raw"]["price_to_rub_multiplier"],
                    "source": t["raw"]["pnl_spec_source"],
                },
                "context": {
                    "schema_version": "V2",
                    "cohort": cohort,
                    "active_contract": t["active_contract"],
                    "root_symbol": t["root_symbol"],
                    "entry_regime": t["entry_regime"],
                    "regime_trend": t["raw"]["regime_trend"],
                    "regime_vol": t["raw"]["regime_vol"],
                    "side": t["raw"]["side"],
                    "entry_session_msk": t["raw"]["entry_session_msk"],
                    "exit_rule": t["exit_rule"],
                    "planned_exit_rule": t["raw"]["planned_exit_rule"],
                    "actual_exit_reason": t["raw"]["actual_exit_reason"],
                    "entry_stop_price": t["raw"]["entry_stop_price"],
                    "entry_take_price": t["raw"]["entry_take_price"],
                    "regime_source_version": t["raw"]["regime_source_version"],
                    "regime_timeframe": t["raw"]["regime_timeframe"],
                    "regime_bar_ts": t["raw"]["regime_bar_ts"],
                    "regime_atr_pct": t["raw"]["regime_atr_pct"],
                    "regime_atr_percentile": t["raw"]["regime_atr_percentile"],
                    "regime_adx": t["raw"]["regime_adx"],
                    "regime_normalized_slope": t["raw"]["regime_normalized_slope"],
                    "regime_confirmed_bars": t["raw"]["regime_confirmed_bars"],
                },
            })},
        ).fetchone()
        written += int(result is not None)
    return written


def refresh_canonical_attribution(conn, trades: list[dict], context_activated_at) -> int:
    updated = 0
    for t in trades:
        portfolio_scope = t.get("portfolio_scope") or resolve_scope_at_entry(
            conn, t["symbol"], t["entry_ts"]
        )
        if str(portfolio_scope or "").startswith("FRESH_V4") and not is_assigned_strategy(
            t.get("strategy")
        ):
            continue
        cohort = portfolio_scope or ("FRESH_V2" if t["entry_ts"] >= context_activated_at else "LEGACY_DERIVED")
        result = conn.execute(
            """UPDATE closed_trades
               SET strategy=%(strategy)s,timeframe=%(timeframe)s,
                   horizon=%(horizon)s,regime=%(regime)s,
                   gross_pnl=%(pnl_points)s,commission=%(commission)s,net_pnl=%(net_pnl)s,
                   root_symbol=%(root_symbol)s,entry_regime=%(entry_regime)s,
                   exit_regime=%(exit_regime)s,portfolio_scope=%(portfolio_scope)s,
                   payload=payload || jsonb_build_object(
                     'pnl_units',jsonb_build_object(
                       'version','PNL_UNITS_V2_RUB','currency',%(pnl_currency)s::text,
                       'price_to_rub_multiplier',%(price_to_rub_multiplier)s::numeric,
                       'source',%(pnl_spec_source)s::text),
                     'context',jsonb_build_object(
                       'schema_version','V2',
                       'cohort',%(cohort)s::text,
                       'active_contract',%(active_contract)s::text,'root_symbol',%(root_symbol)s::text,
                       'entry_regime',%(entry_regime)s::text,
                       'regime_trend',%(regime_trend)s::text,
                       'regime_vol',%(regime_vol)s::text,
                       'side',%(entry_side)s::text,
                       'entry_session_msk',%(entry_session_msk)s::text,'exit_rule',%(exit_rule)s::text,
                       'planned_exit_rule',%(planned_exit_rule)s::text,
                       'actual_exit_reason',%(actual_exit_reason)s::text,
                       'entry_stop_price',%(entry_stop_price)s::numeric,
                       'entry_take_price',%(entry_take_price)s::numeric,
                       'regime_source_version',%(regime_source_version)s::text,
                       'regime_timeframe',%(regime_timeframe)s::text,
                       'regime_bar_ts',%(regime_bar_ts)s::text,
                       'regime_atr_pct',%(regime_atr_pct)s::text,
                       'regime_atr_percentile',%(regime_atr_percentile)s::text,
                       'regime_adx',%(regime_adx)s::text,
                       'regime_normalized_slope',%(regime_normalized_slope)s::text,
                       'regime_confirmed_bars',%(regime_confirmed_bars)s::text))
               WHERE source='paper_fill_materializer_v2'
                 AND payload->>'materialized_trade_id'=%(trade_id)s
                 AND (strategy IS DISTINCT FROM %(strategy)s
                   OR timeframe IS DISTINCT FROM %(timeframe)s
                   OR horizon IS DISTINCT FROM %(horizon)s
                   OR regime IS DISTINCT FROM %(regime)s
                   OR gross_pnl IS DISTINCT FROM %(pnl_points)s
                   OR commission IS DISTINCT FROM %(commission)s
                   OR net_pnl IS DISTINCT FROM %(net_pnl)s
                   OR payload->'pnl_units'->>'version' IS DISTINCT FROM 'PNL_UNITS_V2_RUB'
                   OR root_symbol IS DISTINCT FROM %(root_symbol)s
                   OR entry_regime IS DISTINCT FROM %(entry_regime)s
                   OR exit_regime IS DISTINCT FROM %(exit_regime)s
                   OR payload->'context' IS DISTINCT FROM jsonb_build_object(
                        'schema_version','V2',
                        'cohort',%(cohort)s::text,
                        'active_contract',%(active_contract)s::text,'root_symbol',%(root_symbol)s::text,
                        'entry_regime',%(entry_regime)s::text,
                        'regime_trend',%(regime_trend)s::text,
                        'regime_vol',%(regime_vol)s::text,
                        'side',%(entry_side)s::text,
                        'entry_session_msk',%(entry_session_msk)s::text,'exit_rule',%(exit_rule)s::text,
                        'planned_exit_rule',%(planned_exit_rule)s::text,
                        'actual_exit_reason',%(actual_exit_reason)s::text,
                        'entry_stop_price',%(entry_stop_price)s::numeric,
                        'entry_take_price',%(entry_take_price)s::numeric,
                        'regime_source_version',%(regime_source_version)s::text,
                        'regime_timeframe',%(regime_timeframe)s::text,
                        'regime_bar_ts',%(regime_bar_ts)s::text,
                        'regime_atr_pct',%(regime_atr_pct)s::text,
                        'regime_atr_percentile',%(regime_atr_percentile)s::text,
                        'regime_adx',%(regime_adx)s::text,
                        'regime_normalized_slope',%(regime_normalized_slope)s::text,
                        'regime_confirmed_bars',%(regime_confirmed_bars)s::text))""",
            {**t, "context_activated_at": context_activated_at,
             "portfolio_scope": portfolio_scope, "cohort": cohort,
             "regime_trend": t["raw"]["regime_trend"],
             "regime_vol": t["raw"]["regime_vol"],
             "entry_side": t["raw"]["side"],
             "entry_session_msk": t["raw"]["entry_session_msk"],
             "planned_exit_rule": t["raw"]["planned_exit_rule"],
             "actual_exit_reason": t["raw"]["actual_exit_reason"],
             "pnl_currency": t["raw"]["pnl_currency"],
             "price_to_rub_multiplier": t["raw"]["price_to_rub_multiplier"],
             "pnl_spec_source": t["raw"]["pnl_spec_source"],
             "entry_stop_price": t["raw"]["entry_stop_price"],
             "entry_take_price": t["raw"]["entry_take_price"],
             "regime_source_version": t["raw"]["regime_source_version"],
             "regime_timeframe": t["raw"]["regime_timeframe"],
             "regime_bar_ts": t["raw"]["regime_bar_ts"],
             "regime_atr_pct": t["raw"]["regime_atr_pct"],
             "regime_atr_percentile": t["raw"]["regime_atr_percentile"],
             "regime_adx": t["raw"]["regime_adx"],
             "regime_normalized_slope": t["raw"]["regime_normalized_slope"],
             "regime_confirmed_bars": t["raw"]["regime_confirmed_bars"]},
        )
        updated += result.rowcount
    return updated


def main() -> int:
    args = parse_args()
    db = os.getenv("DATABASE_URL")
    if not db:
        raise SystemExit("DATABASE_URL is required")

    if not args.apply and not args.dry_run:
        args.dry_run = True

    with psycopg.connect(db, row_factory=dict_row) as conn:
        conn.execute(DDL)

        symbols = load_symbols(conn, args)
        total_trades = 0
        total_canonical_written = 0
        total_attribution_updated = 0
        legacy_cutoff = conn.execute(
            """SELECT max(exit_ts) FROM closed_trades
               WHERE source <> 'paper_fill_materializer_v2'"""
        ).fetchone()["max"]
        context_activated_at = conn.execute(
            """SELECT activated_at FROM analytics.paper_trade_context_capture_state_v2
               WHERE state_id AND active"""
        ).fetchone()["activated_at"]

        print("=== MATERIALIZE CLOSED TRADES FROM FILLS V1 ===")
        print(f"mode={'APPLY' if args.apply else 'DRY_RUN'}")
        print(f"symbols={','.join(symbols)}")
        print(f"from_ts={args.from_ts}")
        print(f"to_ts={args.to_ts}")
        print()

        for symbol in symbols:
            fills = load_fills(conn, symbol, args)
            try:
                pnl_spec = resolve_pnl_unit_spec(conn, symbol)
            except Exception as exc:
                print(f"SYMBOL_BLOCKED symbol={symbol} reason={type(exc).__name__}:{exc}")
                continue
            trades = reconstruct(symbol, fills, pnl_spec)
            total_trades += len(trades)

            print(
                f"SYMBOL_SUMMARY symbol={symbol} fills={len(fills)} "
                f"closed_trades={len(trades)}"
            )

            if args.apply:
                if args.replace:
                    conn.execute(
                        "DELETE FROM analytics_closed_trades_v1 WHERE symbol = %s",
                        (symbol,),
                    )
                written = upsert_trades(conn, trades)
                canonical_written = upsert_canonical_trades(conn, trades, legacy_cutoff, context_activated_at)
                attribution_updated = refresh_canonical_attribution(conn, trades, context_activated_at)
                total_canonical_written += canonical_written
                total_attribution_updated += attribution_updated
                print(
                    f"SYMBOL_APPLIED symbol={symbol} analytics_written={written} "
                    f"canonical_written={canonical_written} "
                    f"attribution_updated={attribution_updated}"
                )
                if not (args.symbol or args.symbols or args.symbol_pattern or args.from_ts or args.to_ts):
                    save_checkpoint(conn, symbol)

        if args.apply:
            conn.commit()

    print()
    print(f"TOTAL_CLOSED_TRADES={total_trades}")
    print(f"CANONICAL_WRITTEN={total_canonical_written}")
    print(f"ATTRIBUTION_UPDATED={total_attribution_updated}")
    print(f"VERDICT={'APPLIED' if args.apply else 'DRY_RUN_ONLY'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
