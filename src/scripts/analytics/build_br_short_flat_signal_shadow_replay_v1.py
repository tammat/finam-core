#!/usr/bin/env python3
from __future__ import annotations

import os
import psycopg2
import psycopg2.extras


SYMBOLS = ["BRM6@RTSX", "BRN6@RTSX"]
STRATEGIES = [
    "BR_CONSERVATIVE_BREAKOUT",
    "BR_CONSERVATIVE_BREAKOUT_M5",
    "HISTORICAL_BREAKOUT_V1",
]


def main() -> None:
    dsn = os.environ["DATABASE_URL"]

    print("=== BR SHORT FLAT SIGNAL SHADOW REPLAY V1 ===")
    print("mode=research_only")
    print("execution=disabled")
    print("runtime_changed=0")
    print("hypothesis=BR_SELL_signal_as_OPEN_SHORT_from_flat_position")
    print()

    with psycopg2.connect(dsn) as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                """
                select
                    id,
                    symbol,
                    side,
                    ts,
                    coalesce(entry_price, 0) as entry_price,
                    coalesce(strategy, 'UNKNOWN') as strategy,
                    coalesce(timeframe, 'UNKNOWN') as timeframe,
                    coalesce(status, 'UNKNOWN') as status,
                    payload
                from signals
                where symbol = any(%s)
                  and side='SELL'
                  and coalesce(strategy, 'UNKNOWN') = any(%s)
                  and coalesce(status, '') in ('risk_accepted','ACCEPTED','NEW')
                order by symbol, ts, id;
                """,
                (SYMBOLS, STRATEGIES),
            )
            signals = cur.fetchall()

            cur.execute(
                """
                select
                    symbol,
                    ts,
                    close
                from market_bars
                where symbol = any(%s)
                  and timeframe = 'M5'
                order by symbol, ts;
                """,
                (SYMBOLS,),
            )
            bars = cur.fetchall()

    bars_by_symbol: dict[str, list[dict]] = {}
    for b in bars:
        bars_by_symbol.setdefault(str(b["symbol"]), []).append(b)

    trades = []

    for s in signals:
        symbol = str(s["symbol"])
        signal_ts = s["ts"]
        entry_price = float(s["entry_price"] or 0.0)

        if entry_price <= 0:
            payload = dict(s["payload"] or {})
            entry_price = float(
                payload.get("entry_price")
                or payload.get("price")
                or payload.get("close")
                or 0.0
            )

        if entry_price <= 0:
            continue

        symbol_bars = bars_by_symbol.get(symbol, [])
        future = [b for b in symbol_bars if b["ts"] and b["ts"] > signal_ts]

        if not future:
            continue

        horizons = {
            "exit_1h": 12,
            "exit_2h": 24,
            "exit_4h": 48,
            "exit_8h": 96,
        }

        result = {
            "id": s["id"],
            "symbol": symbol,
            "strategy": str(s["strategy"]),
            "timeframe": str(s["timeframe"]),
            "signal_ts": signal_ts,
            "entry_price": entry_price,
        }

        for name, idx in horizons.items():
            if len(future) >= idx:
                exit_price = float(future[idx - 1]["close"])
                result[name] = entry_price - exit_price
            else:
                result[name] = None

        mfe = None
        mae = None
        scan = future[:96]
        if scan:
            pnls = [entry_price - float(b["close"]) for b in scan]
            mfe = max(pnls)
            mae = min(pnls)

        result["mfe_8h"] = mfe
        result["mae_8h"] = mae
        trades.append(result)

    print("SUMMARY")
    print(f"SELL_SIGNALS={len(signals)}")
    print(f"SIMULATED_SHORT_TRADES={len(trades)}")
    print()

    def summarize(policy: str) -> None:
        vals = [float(t[policy]) for t in trades if t.get(policy) is not None]
        if not vals:
            print(f"POLICY_ROW policy={policy} trades=0 net_pnl=0 expectancy=0 winrate=0 profit_factor=None")
            return

        wins = [v for v in vals if v > 0]
        losses = [v for v in vals if v < 0]
        gross_profit = sum(wins)
        gross_loss = abs(sum(losses))
        net = sum(vals)
        expectancy = net / len(vals)
        winrate = len(wins) / len(vals)
        pf = gross_profit / gross_loss if gross_loss > 0 else None

        print(
            "POLICY_ROW "
            f"policy={policy} trades={len(vals)} "
            f"net_pnl={net:.8f} expectancy={expectancy:.8f} "
            f"winrate={winrate:.4f} "
            f"profit_factor={pf if pf is not None else 'None'}"
        )

    print("POLICY_SUMMARY")
    for p in ["exit_1h", "exit_2h", "exit_4h", "exit_8h", "mfe_8h"]:
        summarize(p)
    print()

    print("BY_STRATEGY_POLICY_2H")
    by_strategy: dict[str, list[float]] = {}
    for t in trades:
        if t.get("exit_2h") is not None:
            by_strategy.setdefault(t["strategy"], []).append(float(t["exit_2h"]))

    for strategy, vals in sorted(by_strategy.items()):
        wins = [v for v in vals if v > 0]
        losses = [v for v in vals if v < 0]
        gp = sum(wins)
        gl = abs(sum(losses))
        pf = gp / gl if gl > 0 else None
        print(
            f"STRATEGY_ROW strategy={strategy} trades={len(vals)} "
            f"net_pnl={sum(vals):.8f} expectancy={(sum(vals)/len(vals)):.8f} "
            f"winrate={(len(wins)/len(vals)):.4f} "
            f"profit_factor={pf if pf is not None else 'None'}"
        )
    print()

    print("SAMPLE")
    for t in trades[:60]:
        print(
            "SHORT_SHADOW_ROW "
            f"id={t['id']} symbol={t['symbol']} strategy={t['strategy']} "
            f"signal_ts={t['signal_ts']} entry={t['entry_price']} "
            f"pnl_1h={t.get('exit_1h')} pnl_2h={t.get('exit_2h')} "
            f"pnl_4h={t.get('exit_4h')} pnl_8h={t.get('exit_8h')} "
            f"mfe_8h={t.get('mfe_8h')} mae_8h={t.get('mae_8h')}"
        )
    print()

    vals_2h = [float(t["exit_2h"]) for t in trades if t.get("exit_2h") is not None]
    if not vals_2h:
        print("VERDICT=NO_SHORT_REPLAY_DATA")
        return

    net_2h = sum(vals_2h)
    expectancy_2h = net_2h / len(vals_2h)
    wins = [v for v in vals_2h if v > 0]
    losses = [v for v in vals_2h if v < 0]
    pf_2h = sum(wins) / abs(sum(losses)) if losses else None

    print("DECISION_METRICS")
    print(
        f"EXIT_2H trades={len(vals_2h)} net_pnl={net_2h:.8f} "
        f"expectancy={expectancy_2h:.8f} "
        f"profit_factor={pf_2h if pf_2h is not None else 'None'}"
    )

    if len(vals_2h) >= 30 and net_2h > 0 and expectancy_2h > 0 and (pf_2h or 0) > 1.10:
        print("VERDICT=BR_SHORT_FLAT_SIGNAL_EDGE_FOUND")
    else:
        print("VERDICT=BR_SHORT_FLAT_SIGNAL_EDGE_NOT_VALIDATED")


if __name__ == "__main__":
    main()
