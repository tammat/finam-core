# -*- coding: utf-8 -*-

from __future__ import annotations

import os
import json
import psycopg2

# Telegram отключён для strategy performance monitor: это аналитика, не actionable сигнал.
from finam_core.control.adaptive_strategy_controller import AdaptiveStrategyController


MIN_TRADES = 20


def classify(trades: int, profit_factor, expectancy) -> str:
    if trades < MIN_TRADES:
        return "NO_DATA"

    pf = float(profit_factor or 0.0)
    exp = float(expectancy or 0.0)

    if pf >= 1.5 and exp > 0:
        return "HEALTHY"

    if pf >= 1.0 and exp > 0:
        return "WATCH"

    return "DEGRADED"


def main() -> None:
    conn = psycopg2.connect(
        dbname=os.getenv("PGDATABASE", "finam_core"),
        user=os.getenv("PGUSER") or None,
        host=os.getenv("PGHOST") or None,
        port=os.getenv("PGPORT") or None,
        password=os.getenv("PGPASSWORD") or None,
    )

    with conn.cursor() as cur:
        cur.execute("""
            SELECT
                   symbol,
                   COALESCE(strategy, 'default') AS strategy,
                   trades, wins, losses, net_pnl, expectancy,
                   profit_factor, winrate, last_trade_ts
            FROM grafana_strategy_performance_monitor
            ORDER BY net_pnl DESC;
        """)
        rows = cur.fetchall()

    lines = ["📈 Strategy Performance Monitor", ""]

    controller = AdaptiveStrategyController(conn)

    problem_count = 0
    control_updates = 0

    for row in rows:
        symbol, strategy, trades, wins, losses, net_pnl, expectancy, pf, winrate, last_ts = row
        strategy = str(strategy or "default")
        status, decision_reason = controller.classify_metrics(
            trades=int(trades or 0),
            profit_factor=pf,
            expectancy=expectancy,
            net_pnl=net_pnl,
            min_trades=MIN_TRADES,
        )

        status, decision_reason = controller.apply_recovery_hysteresis(
            symbol=symbol,
            strategy=strategy,
            candidate_status=status,
            candidate_reason=decision_reason,
        )

        decision = controller.decision_from_status(
            symbol,
            status,
            strategy=strategy,
            reason=decision_reason,
        )
        controller.upsert_decision(
            decision,
            payload={
                "trades": int(trades or 0),
                "wins": int(wins or 0),
                "losses": int(losses or 0),
                "net_pnl": float(net_pnl or 0.0),
                "expectancy": float(expectancy or 0.0),
                "profit_factor": float(pf or 0.0),
                "winrate": float(winrate or 0.0),
                "last_trade_ts": str(last_ts),
                "source": "strategy_performance_monitor",
                "strategy": strategy,
                "decision_reason": decision_reason,
            },
        )
        control_updates += 1

        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO strategy_performance_history (
                    symbol, status, trades, wins, losses,
                    net_pnl, expectancy, profit_factor, winrate,
                    last_trade_ts, payload
                )
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s::jsonb)
                """,
                (
                    symbol,
                    status,
                    int(trades or 0),
                    int(wins or 0),
                    int(losses or 0),
                    float(net_pnl or 0.0),
                    float(expectancy or 0.0),
                    float(pf or 0.0),
                    float(winrate or 0.0),
                    last_ts,
                    json.dumps(
                        {
                            "source": "strategy_performance_monitor",
                "strategy": strategy,
                "decision_reason": decision_reason,
                            "min_trades": MIN_TRADES,
                        },
                        ensure_ascii=False,
                    ),
                ),
            )
        conn.commit()

        if status == "HEALTHY":
            continue

        problem_count += 1

        lines.extend([
            f"Инструмент: {symbol}",
            f"Стратегия: {strategy}",
            f"Статус: {status}",
            f"Trades: {trades} | Win/Loss: {wins}/{losses}",
            f"Net PnL: {round(float(net_pnl or 0.0), 2)}",
            f"Expectancy: {round(float(expectancy or 0.0), 2)}",
            f"PF: {round(float(pf or 0.0), 2)}",
            f"Winrate: {round(float(winrate or 0.0), 2)}%",
            f"Last trade: {last_ts}",
            "",
        ])

    if problem_count == 0:
        print(f"STRATEGY_PERFORMANCE_MONITOR_OK problems=0 control_updates={control_updates} no_telegram=1", flush=True)
        return

    TelegramNotifier().send("\n".join(lines))

    print(f"STRATEGY_PERFORMANCE_MONITOR_OK problems={problem_count} control_updates={control_updates}", flush=True)


if __name__ == "__main__":
    main()
