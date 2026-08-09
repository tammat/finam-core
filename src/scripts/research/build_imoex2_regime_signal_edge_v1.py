#!/usr/bin/env python3
"""
IMOEX2_REGIME_SIGNAL_EDGE_V1

Цель:
проверить наличие gross signal edge на IMOEX2,
условного на рыночный режим.

Принципы:
- PostgreSQL read-only;
- только IMOEX2;
- никакого MXU6;
- commission=0;
- slippage=0;
- chronological + purged OOS;
- regime определяется независимо из analytics_regime_snapshots_v2;
- multiple-testing correction;
- runtime/execution не изменяются.
"""

from __future__ import annotations

import json
import math
import os
import statistics
from decimal import Decimal
from pathlib import Path

import psycopg2
import psycopg2.extras

from scripts.build_strategy_execution_runner_v1 import (
    Bar,
    build_trades,
    metrics,
)
from finam_core.research.purged_split import (
    purged_bar_window,
    trades_in_purged_window,
)


CONFIG_PATH = Path(
    "config/research/imoex2_regime_signal_edge_v1.json"
)

STRATEGY_CODES = {
    "MOMENTUM": "MOMENTUM_CONTINUATION_V2",
    "MEAN_REVERSION": "MEAN_REVERSION_V2",
    "BREAKOUT": "VOLATILITY_BREAKOUT_V2",
}


def dec(value) -> Decimal:
    if value is None:
        return Decimal("0")
    return Decimal(str(value))


def load_config() -> dict:
    return json.loads(CONFIG_PATH.read_text())


def trade_pnl(trade) -> float:
    for name in ("net_pnl", "gross_pnl", "pnl"):
        value = getattr(trade, name, None)
        if value is not None:
            return float(value)
    return 0.0


def raw_p_value(trades) -> float:
    values = [trade_pnl(t) for t in trades]

    if len(values) < 2:
        return 1.0

    mean = statistics.fmean(values)
    stdev = statistics.stdev(values)

    if stdev <= 0:
        return 1.0

    t_stat = abs(
        mean / (stdev / math.sqrt(len(values)))
    )

    # Нормальная аппроксимация двухстороннего p-value.
    return math.erfc(t_stat / math.sqrt(2.0))


def fold_passes(trades, fold_count: int = 3) -> tuple[int, int]:
    ordered = sorted(
        trades,
        key=lambda trade: trade.entry_ts,
    )

    if not ordered:
        return 0, fold_count

    size = math.ceil(len(ordered) / fold_count)
    passed = 0

    for fold in range(fold_count):
        start = fold * size
        end = min((fold + 1) * size, len(ordered))

        sample = ordered[start:end]

        if not sample:
            continue

        result = metrics(sample)

        pf = dec(result.get("profit_factor"))
        expectancy = dec(result.get("expectancy"))

        if (
            int(result.get("trades") or 0) >= 6
            and pf >= Decimal("1.0")
            and expectancy > 0
        ):
            passed += 1

    return passed, fold_count


def main() -> int:
    cfg = load_config()

    symbol = cfg["symbol"]
    timeframe = cfg["timeframe"]

    print("=== IMOEX2 REGIME SIGNAL EDGE V1 ===")
    print("mode=gross_regime_signal_edge_discovery")
    print(f"signal_symbol={symbol}")
    print(f"timeframe={timeframe}")
    print(
        f"minimum_regime_confidence="
        f"{cfg['minimum_regime_confidence']}"
    )
    print("execution_instrument_used=0")
    print("execution_costs_used=0")
    print("commission=0")
    print("slippage=0")
    print()

    conn = psycopg2.connect(
        os.environ["DATABASE_URL"]
    )
    conn.set_session(
        readonly=True,
        autocommit=False,
    )

    try:
        with conn.cursor(
            cursor_factory=psycopg2.extras.RealDictCursor
        ) as cur:

            cur.execute(
                """
                SELECT ts,close
                FROM public.market_bars
                WHERE symbol=%s
                  AND timeframe=%s
                  AND close IS NOT NULL
                ORDER BY ts
                """,
                (symbol, timeframe),
            )

            bars = [
                Bar(
                    row["ts"],
                    float(row["close"]),
                )
                for row in cur.fetchall()
            ]

            cur.execute(
                """
                SELECT DISTINCT ON (ts)
                    ts,
                    regime,
                    confidence
                FROM analytics_regime_snapshots_v2
                WHERE symbol=%s
                  AND timeframe=%s
                  AND confidence >= %s
                ORDER BY ts,confidence DESC
                """,
                (
                    symbol,
                    timeframe,
                    float(cfg["minimum_regime_confidence"]),
                ),
            )

            regime_rows = [
                dict(row)
                for row in cur.fetchall()
            ]

        total_bars = len(bars)

        if total_bars < int(cfg["minimum_bars"]):
            print(f"bars={total_bars}")
            print(
                "VERDICT="
                "IMOEX2_REGIME_SIGNAL_INSUFFICIENT_BARS"
            )
            return 3

        regime_by_ts = {
            row["ts"]: str(row["regime"])
            for row in regime_rows
        }

        covered = sum(
            1
            for bar in bars
            if bar.ts in regime_by_ts
        )

        coverage = (
            covered / total_bars
            if total_bars
            else 0.0
        )

        print(f"bars={total_bars}")
        print(f"regime_rows={len(regime_rows)}")
        print(f"regime_coverage_ratio={coverage:.6f}")

        if coverage < float(
            cfg["minimum_regime_coverage"]
        ):
            print(
                "VERDICT="
                "IMOEX2_REGIME_SIGNAL_INSUFFICIENT_COVERAGE"
            )
            return 4

        development_end = int(
            total_bars
            * float(cfg["development_fraction"])
        )

        print(
            f"development_bars={development_end}"
        )
        print(
            f"raw_oos_bars="
            f"{total_bars - development_end}"
        )
        print()

        candidates = []
        all_rows = []

        for family, variants in cfg["families"].items():

            strategy_code = STRATEGY_CODES[family]

            for variant_no, raw_params in enumerate(
                variants,
                start=1,
            ):
                params = dict(raw_params)
                params["commission"] = 0.0
                params["slippage"] = 0.0

                lookback = int(params["lookback"])

                oos_start, oos_stop, _ = (
                    purged_bar_window(
                        bars,
                        start=development_end,
                        end=total_bars,
                        parameters=params,
                    )
                )

                source_start = max(
                    0,
                    development_end - lookback,
                )

                run = {
                    "strategy_code": strategy_code,
                    "parameter_json": params,
                }

                all_trades = build_trades(
                    run,
                    bars[source_start:],
                )

                oos_all = trades_in_purged_window(
                    all_trades,
                    start_ts=oos_start,
                    end_ts=oos_stop,
                )

                for regime in cfg["regimes"]:

                    regime_trades = [
                        trade
                        for trade in oos_all
                        if regime_by_ts.get(
                            trade.entry_ts
                        ) == regime
                    ]

                    result = metrics(regime_trades)

                    trades = int(
                        result.get("trades") or 0
                    )
                    pf = dec(
                        result.get("profit_factor")
                    )
                    expectancy = dec(
                        result.get("expectancy")
                    )

                    folds_passed, folds_total = (
                        fold_passes(regime_trades)
                    )

                    raw_p = raw_p_value(
                        regime_trades
                    )

                    row = {
                        "family": family,
                        "strategy": strategy_code,
                        "variant": variant_no,
                        "regime": regime,
                        "trades": trades,
                        "pf": pf,
                        "expectancy": expectancy,
                        "folds_passed": folds_passed,
                        "folds_total": folds_total,
                        "raw_p": raw_p,
                    }

                    all_rows.append(row)

        trial_count = len(all_rows)

        for row in all_rows:

            adjusted_p = min(
                1.0,
                row["raw_p"] * trial_count,
            )

            candidate = (
                row["trades"]
                >= int(cfg["minimum_oos_trades"])
                and row["pf"]
                >= dec(
                    cfg[
                        "minimum_oos_profit_factor"
                    ]
                )
                and row["expectancy"]
                > dec(
                    cfg[
                        "minimum_oos_expectancy"
                    ]
                )
                and row["folds_passed"]
                >= int(
                    cfg["minimum_folds_passed"]
                )
                and adjusted_p
                <= float(
                    cfg[
                        "maximum_adjusted_p_value"
                    ]
                )
            )

            row["adjusted_p"] = adjusted_p
            row["candidate"] = candidate

            print(
                "REGIME_DISCOVERY_ROW "
                f"family={row['family']} "
                f"strategy={row['strategy']} "
                f"variant={row['variant']} "
                f"regime={row['regime']} "
                f"oos_trades={row['trades']} "
                f"gross_oos_profit_factor={row['pf']} "
                f"gross_oos_expectancy="
                f"{row['expectancy']} "
                f"folds_passed="
                f"{row['folds_passed']}/"
                f"{row['folds_total']} "
                f"raw_p={row['raw_p']:.6f} "
                f"adjusted_p={adjusted_p:.6f} "
                f"signal_candidate={int(candidate)}"
            )

            if candidate:
                candidates.append(row)

        print()
        print("REGIME_SIGNAL_CANDIDATE_ROWS")

        ranked = sorted(
            candidates,
            key=lambda row: (
                row["expectancy"],
                row["pf"],
                row["trades"],
            ),
            reverse=True,
        )

        for rank, row in enumerate(
            ranked,
            start=1,
        ):
            print(
                "REGIME_SIGNAL_CANDIDATE_ROW "
                f"rank={rank} "
                f"family={row['family']} "
                f"strategy={row['strategy']} "
                f"variant={row['variant']} "
                f"regime={row['regime']} "
                f"oos_trades={row['trades']} "
                f"gross_oos_profit_factor={row['pf']} "
                f"gross_oos_expectancy="
                f"{row['expectancy']} "
                f"adjusted_p="
                f"{row['adjusted_p']:.6f}"
            )

        print()
        print(
            "SUMMARY_ROW "
            f"trials={trial_count} "
            f"regime_candidates={len(candidates)}"
        )

        print("gross_regime_signal_edge_search=1")
        print("economic_edge_claimed=0")
        print("multiple_testing_adjusted=1")
        print("execution_instrument_used=0")
        print("execution_costs_used=0")
        print("purged_oos_used=1")
        print("db_writes_performed=0")
        print("runtime_changed=0")
        print("execution_changed=0")
        print("orders_changed=0")
        print("fills_changed=0")
        print("micro_live_allowed=0")

        if candidates:
            verdict = (
                "IMOEX2_REGIME_SIGNAL_"
                "CANDIDATES_FOUND"
            )
        else:
            verdict = (
                "IMOEX2_REGIME_SIGNAL_"
                "NO_CANDIDATES"
            )

        print(f"VERDICT={verdict}")

        conn.rollback()
        return 0

    finally:
        conn.close()


if __name__ == "__main__":
    raise SystemExit(main())
