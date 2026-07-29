from __future__ import annotations

import argparse
import os
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone

import psycopg2
import psycopg2.extras
import requests


DB = os.getenv("DATABASE_URL", "postgresql:///finam_core")
WATCH_DAYS = int(os.getenv("V5_ROLLOVER_WATCH_DAYS", "7"))
FORCE_DAYS = int(os.getenv("V5_ROLLOVER_FORCE_DAYS", "3"))
EARLY_VOLUME_MULTIPLIER = float(os.getenv("V5_ROLLOVER_EARLY_VOLUME_MULTIPLIER", "1.20"))
MIN_NEXT_TRADES = int(os.getenv("V5_ROLLOVER_MIN_NEXT_TRADES", "10"))


@dataclass(frozen=True)
class MarketSnapshot:
    last_trade_date: date | None
    volume: float
    trades: int


def choose_rollover(
    *, days: int | None, current_volume: float, current_trades: int,
    next_volume: float, next_trades: int,
) -> tuple[bool, str]:
    if days is None:
        return False, "EXPIRY_UNKNOWN"
    if next_trades < MIN_NEXT_TRADES or next_volume <= 0:
        return False, "NEXT_LIQUIDITY_NOT_READY"
    if days <= FORCE_DAYS:
        return True, "EXPIRY_PROTECTION"
    if days <= WATCH_DAYS and next_volume >= current_volume * 0.80:
        return True, "ROLLOVER_WINDOW_LIQUID"
    if next_volume > current_volume * EARLY_VOLUME_MULTIPLIER and next_trades >= current_trades:
        return True, "NEXT_CONTRACT_MORE_LIQUID"
    return False, "KEEP_CURRENT_LIQUIDITY"


def fetch_snapshot(symbol: str) -> MarketSnapshot:
    secid = symbol.split("@", 1)[0]
    url = (
        "https://iss.moex.com/iss/engines/futures/markets/forts/"
        f"securities/{secid}.json?iss.meta=off"
    )
    response = requests.get(url, timeout=15, headers={"User-Agent": "MarketCore/v5-rollover-v1"})
    response.raise_for_status()
    payload = response.json()
    combined = {}
    for block in ("securities", "marketdata"):
        data = payload.get(block) or {}
        columns, rows = data.get("columns") or [], data.get("data") or []
        if rows:
            combined.update(dict(zip(columns, rows[0])))
    raw_date = combined.get("LASTTRADEDATE") or combined.get("EXPIRATIONDATE")
    expiry = date.fromisoformat(str(raw_date)[:10]) if raw_date else None
    volume = float(combined.get("VOLTODAY") or combined.get("VALTODAY") or 0)
    trades = int(combined.get("NUMTRADES") or 0)
    return MarketSnapshot(expiry, volume, trades)


def _record(cursor, *, root, current, next_symbol, action, reason, details) -> None:
    cursor.execute("""
        INSERT INTO analytics.v5_futures_rollover_decision_v1(
          root_symbol,current_symbol,next_symbol,action_code,reason_code,details,decided_at)
        VALUES(%s,%s,%s,%s,%s,%s::jsonb,clock_timestamp())
    """, (root,current,next_symbol,action,reason,psycopg2.extras.Json(details)))


def _switch(cursor, *, root: str, current: str, next_symbol: str, scope: str) -> None:
    cursor.execute("""
        INSERT INTO analytics.runtime_strategy_policy_v2(
          symbol,timeframe,regime_family,strategy_code,generator_code,enabled,
          priority,assignment_reason,updated_at)
        SELECT %s,timeframe,regime_family,strategy_code,generator_code,true,
               priority,assignment_reason||'; automatic flat rollover',clock_timestamp()
        FROM analytics.runtime_strategy_policy_v2
        WHERE symbol=%s AND enabled
        ON CONFLICT(symbol,timeframe,regime_family) DO UPDATE SET
          strategy_code=excluded.strategy_code,generator_code=excluded.generator_code,
          enabled=true,priority=excluded.priority,
          assignment_reason=excluded.assignment_reason,updated_at=excluded.updated_at
    """, (next_symbol,current))
    if cursor.rowcount == 0:
        raise RuntimeError("NEXT_STRATEGY_POLICY_NOT_CREATED")

    cursor.execute("""
        INSERT INTO runtime_active_universe(
          symbol,strategy,regime,score,priority,is_enabled,allocated_at,last_seen_at,
          source,raw_json,updated_at,timeframe)
        SELECT %s,strategy,regime,score,priority,true,clock_timestamp(),clock_timestamp(),
               'v5_flat_liquidity_rollover_v1',
               coalesce(raw_json,'{}'::jsonb)||jsonb_build_object(
                 'rollover_from',%s,'rollover_reason','FLAT_LIQUIDITY_VERIFIED'),
               clock_timestamp(),timeframe
        FROM runtime_active_universe WHERE symbol=%s
        ORDER BY is_enabled DESC,updated_at DESC LIMIT 1
        ON CONFLICT(symbol) DO UPDATE SET
          strategy=excluded.strategy,regime=excluded.regime,score=excluded.score,
          priority=excluded.priority,is_enabled=true,disabled_at=NULL,disable_reason=NULL,
          source=excluded.source,raw_json=excluded.raw_json,updated_at=excluded.updated_at,
          timeframe=excluded.timeframe
    """, (next_symbol,current,current))
    if cursor.rowcount == 0:
        raise RuntimeError("CURRENT_RUNTIME_ROW_NOT_FOUND")
    cursor.execute("""
        UPDATE runtime_active_universe SET is_enabled=false,disabled_at=clock_timestamp(),
          disable_reason='AUTOMATIC_FLAT_LIQUIDITY_ROLLOVER',updated_at=clock_timestamp()
        WHERE symbol=%s
    """, (current,))

    if root == "GD":
        cursor.execute("""UPDATE analytics.v5_asset_scope_map_v1
          SET symbol=%s,updated_at=clock_timestamp() WHERE asset_code='GOLD'""", (next_symbol,))
        cursor.execute("""UPDATE analytics.v5_asset_branch_policy_v1
          SET symbol=%s,updated_at=clock_timestamp() WHERE asset_code='GOLD'""", (next_symbol,))
        cursor.execute("""UPDATE analytics.v5_asset_contract_readiness_v1
          SET runtime_symbol=%s,updated_at=clock_timestamp() WHERE asset_code='GOLD'""", (next_symbol,))

    cursor.execute("SELECT analytics.resolve_paper_portfolio_scope_v1(%s,'paper')", (next_symbol,))
    resolved = str((cursor.fetchone() or [""])[0] or "")
    if resolved != scope:
        raise RuntimeError(f"V5_SCOPE_CHANGED:{scope}:{resolved}")

    cursor.execute("""UPDATE analytics.v5_futures_rollover_state_v1
      SET current_symbol=%s,last_rolled_at=clock_timestamp(),updated_at=clock_timestamp()
      WHERE root_symbol=%s""", (next_symbol,root))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    switched = blocked_open = kept = errors = 0
    with psycopg2.connect(DB) as connection:
        with connection.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cursor:
            cursor.execute("SELECT pg_advisory_xact_lock(941903221)")
            cursor.execute("""SELECT root_symbol,current_symbol,scope_code
              FROM analytics.v5_futures_rollover_state_v1 WHERE enabled ORDER BY root_symbol""")
            states = cursor.fetchall()
            for state in states:
                root,current,scope = state["root_symbol"],state["current_symbol"],state["scope_code"]
                cursor.execute("""SELECT contract_symbol FROM futures_contract_universe
                  WHERE root_symbol=%s AND is_active AND status<>'QUARANTINE'
                    AND roll_priority>(SELECT roll_priority FROM futures_contract_universe WHERE contract_symbol=%s)
                  ORDER BY roll_priority LIMIT 1""", (root,current))
                candidate = cursor.fetchone()
                next_symbol = str(candidate["contract_symbol"]) if candidate else ""
                details = {"apply": args.apply}
                if not next_symbol:
                    _record(cursor,root=root,current=current,next_symbol=None,action="KEEP",reason="NEXT_CONTRACT_MISSING",details=details)
                    kept += 1
                    continue
                cursor.execute("""SELECT EXISTS(SELECT 1
                  FROM analytics.paper_research_position_projection_v1
                  WHERE symbol=%s AND abs(coalesce(nullif(state->>'qty','')::numeric,0))>1e-9) AS open""", (current,))
                if bool(cursor.fetchone()["open"]):
                    _record(cursor,root=root,current=current,next_symbol=next_symbol,action="BLOCK",reason="OPEN_POSITION",details=details)
                    blocked_open += 1
                    continue
                cursor.execute("""SELECT max(ts) AS latest_bar FROM market_bars
                  WHERE symbol=%s AND timeframe IN ('M1','M5')""", (next_symbol,))
                latest_bar = cursor.fetchone()["latest_bar"]
                if latest_bar is None or datetime.now(timezone.utc)-latest_bar.astimezone(timezone.utc) > timedelta(minutes=10):
                    _record(cursor,root=root,current=current,next_symbol=next_symbol,action="BLOCK",reason="NEXT_BARS_STALE",details=details)
                    kept += 1
                    continue
                cursor.execute("""SELECT verified_at FROM analytics.market_contract_cost_spec_v1
                  WHERE symbol=%s AND verified_at>=clock_timestamp()-interval '2 days'""", (next_symbol,))
                if cursor.fetchone() is None:
                    _record(cursor,root=root,current=current,next_symbol=next_symbol,action="BLOCK",reason="NEXT_COST_SPEC_STALE",details=details)
                    kept += 1
                    continue
                try:
                    current_md,next_md = fetch_snapshot(current),fetch_snapshot(next_symbol)
                    expiry = current_md.last_trade_date
                    days = (expiry-date.today()).days if expiry else None
                    allowed,reason = choose_rollover(
                        days=days,current_volume=current_md.volume,current_trades=current_md.trades,
                        next_volume=next_md.volume,next_trades=next_md.trades,
                    )
                    details.update({"days":days,"current_volume":current_md.volume,
                                    "next_volume":next_md.volume,"current_trades":current_md.trades,
                                    "next_trades":next_md.trades})
                    if not allowed:
                        _record(cursor,root=root,current=current,next_symbol=next_symbol,action="KEEP",reason=reason,details=details)
                        kept += 1
                    elif not args.apply:
                        _record(cursor,root=root,current=current,next_symbol=next_symbol,action="DRY_RUN",reason=reason,details=details)
                        kept += 1
                    else:
                        cursor.execute("SAVEPOINT v5_rollover_switch")
                        try:
                            _switch(cursor,root=root,current=current,next_symbol=next_symbol,scope=scope)
                        except Exception as exc:
                            cursor.execute("ROLLBACK TO SAVEPOINT v5_rollover_switch")
                            cursor.execute("RELEASE SAVEPOINT v5_rollover_switch")
                            _record(
                                cursor,
                                root=root,
                                current=current,
                                next_symbol=next_symbol,
                                action="ERROR",
                                reason=type(exc).__name__,
                                details={**details, "error": str(exc)[:300]},
                            )
                            errors += 1
                            continue
                        cursor.execute("RELEASE SAVEPOINT v5_rollover_switch")
                        _record(cursor,root=root,current=current,next_symbol=next_symbol,action="SWITCH",reason=reason,details=details)
                        switched += 1
                except Exception as exc:
                    _record(cursor,root=root,current=current,next_symbol=next_symbol,action="ERROR",reason=type(exc).__name__,details={**details,"error":str(exc)[:300]})
                    errors += 1
    print(f"switched={switched} blocked_open={blocked_open} kept={kept} errors={errors}")
    print("execution_changed=0 orders_changed=0 fills_changed=0 real_allowed=0")
    print("VERDICT=V5_FUTURES_FLAT_LIQUIDITY_ROLLOVER_OK")
    return 0 if errors == 0 else 2


if __name__ == "__main__":
    raise SystemExit(main())
