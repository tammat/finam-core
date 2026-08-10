from __future__ import annotations

import json
import os
from decimal import Decimal
from pathlib import Path

import psycopg2
from psycopg2.extras import RealDictCursor

from scripts.research import (
    build_universe_trend_pullback_canonical_adapter_screen_v1 as screen,
)
from scripts.research.build_trend_pullback_canonical_cost_resolver_v1 import (
    resolve_cost_contract,
)
from scripts.research.build_trend_pullback_canonical_cost_validation_v1 import (
    apply_research_cost_identity,
    equity_round_trip_commission,
    equity_round_trip_slippage,
)


SOURCE_VERSION = (
    "TREND_PULLBACK_CANONICAL_EQUITY_BASE_COST_VALIDATION_V1"
)

CONFIG_PATH = Path(
    "config/research/"
    "trend_pullback_canonical_robustness_v1.json"
)

SYMBOLS = (
    "NVTK@MISX",
    "PLZL@MISX",
)


def dec(value) -> Decimal:
    return Decimal(str(value))


def net_metrics(values: list[Decimal]) -> dict:
    trades = len(values)

    if trades == 0:
        return {
            "trades": 0,
            "net_pnl": Decimal("0"),
            "expectancy": Decimal("0"),
            "profit_factor": Decimal("0"),
            "winrate": Decimal("0"),
            "max_drawdown": Decimal("0"),
        }

    wins = [
        value
        for value in values
        if value > 0
    ]

    losses = [
        value
        for value in values
        if value < 0
    ]

    net_pnl = sum(
        values,
        Decimal("0"),
    )

    gross_profit = sum(
        wins,
        Decimal("0"),
    )

    gross_loss = abs(
        sum(
            losses,
            Decimal("0"),
        )
    )

    profit_factor = (
        gross_profit / gross_loss
        if gross_loss > 0
        else Decimal("999999")
    )

    expectancy = (
        net_pnl
        / Decimal(trades)
    )

    winrate = (
        Decimal(len(wins))
        / Decimal(trades)
    )

    equity = Decimal("0")
    peak = Decimal("0")
    max_drawdown = Decimal("0")

    for value in values:
        equity += value

        if equity > peak:
            peak = equity

        drawdown = peak - equity

        if drawdown > max_drawdown:
            max_drawdown = drawdown

    return {
        "trades": trades,
        "net_pnl": net_pnl,
        "expectancy": expectancy,
        "profit_factor": profit_factor,
        "winrate": winrate,
        "max_drawdown": max_drawdown,
    }


def load_baseline_parameters(cfg: dict) -> dict:
    variants = cfg.get("variants")

    if not isinstance(variants, list):
        raise RuntimeError(
            "ERROR=ROBUSTNESS_VARIANTS_NOT_FOUND"
        )

    baseline = next(
        (
            item
            for item in variants
            if item.get("code") == "BASELINE"
        ),
        None,
    )

    if baseline is None:
        raise RuntimeError(
            "ERROR=BASELINE_VARIANT_NOT_FOUND"
        )

    parameters = {
        key: value
        for key, value in baseline.items()
        if key != "code"
    }

    hold_bars = int(
        cfg["screen_exit_horizon"]["hold_bars"]
    )

    parameters["hold_bars"] = hold_bars

    return parameters


def main() -> int:
    cfg = json.loads(
        CONFIG_PATH.read_text()
    )

    parameters = load_baseline_parameters(
        cfg
    )

    minimum_oos_trades = int(
        cfg["minimum_oos_trades"]
    )

    dsn = os.environ.get(
        "DATABASE_URL"
    )

    if not dsn:
        raise SystemExit(
            "ERROR=DATABASE_URL_NOT_SET"
        )

    survivors = 0

    with psycopg2.connect(dsn) as conn:
        with conn.cursor(
            cursor_factory=RealDictCursor
        ) as cur:

            for symbol in SYMBOLS:
                cost = resolve_cost_contract(
                    cur,
                    symbol,
                )

                if (
                    cost.evidence_status
                    != "COST_SOURCE_COMPLETE"
                ):
                    raise RuntimeError(
                        "ERROR=EQUITY_COST_SOURCE_INCOMPLETE "
                        f"symbol={symbol} "
                        f"status={cost.evidence_status}"
                    )

                cur.execute(
                    """
                    SELECT
                        ts,
                        open,
                        high,
                        low,
                        close,
                        volume
                    FROM public.market_bars
                    WHERE symbol=%s
                      AND timeframe='M5'
                    ORDER BY ts
                    """,
                    (symbol,),
                )

                bars = [
                    screen.MarketBar(
                        ts=row["ts"],
                        open=dec(row["open"]),
                        high=dec(row["high"]),
                        low=dec(row["low"]),
                        close=dec(row["close"]),
                        volume=dec(row["volume"] or 0),
                    )
                    for row in cur.fetchall()
                ]

                if not bars:
                    raise RuntimeError(
                        "ERROR=MARKET_BARS_MISSING "
                        f"symbol={symbol}"
                    )

                development_fraction = Decimal(
                    str(
                        cfg[
                            "development_fraction"
                        ]
                    )
                )

                development_end = int(
                    Decimal(len(bars))
                    * development_fraction
                )

                trades = (
                    screen.build_canonical_trades(
                        bars,
                        parameters,
                        development_end,
                        len(bars),
                    )
                )

                gross_metric = (
                    screen.gross_metrics(
                        trades
                    )
                )

                commission_total = Decimal("0")
                slippage_total = Decimal("0")
                net_values: list[Decimal] = []

                for trade in trades:
                    commission = (
                        equity_round_trip_commission(
                            entry_notional=trade.entry_price,
                            exit_notional=trade.exit_price,
                            commission_per_trade=(
                                cost.commission_per_trade
                                or Decimal("0")
                            ),
                            commission_pct=(
                                cost.commission_pct
                                or Decimal("0")
                            ),
                        )
                    )

                    slippage = (
                        equity_round_trip_slippage(
                            slippage_per_trade=(
                                cost.slippage_per_trade
                                or Decimal("0")
                            ),
                        )
                    )

                    costed = apply_research_cost_identity(
                        gross_pnl=trade.gross_pnl,
                        commission=commission,
                        slippage=slippage,
                    )

                    commission_total += commission
                    slippage_total += slippage
                    net_values.append(
                        costed.net_pnl
                    )

                metrics = net_metrics(
                    net_values
                )

                gross_pnl = dec(
                    gross_metric["gross_pnl"]
                )

                total_cost = (
                    commission_total
                    + slippage_total
                )

                cost_to_gross_ratio = (
                    total_cost / abs(gross_pnl)
                    if gross_pnl != 0
                    else Decimal("999999")
                )

                survive = (
                    metrics["trades"]
                    >= minimum_oos_trades
                    and metrics["expectancy"] > 0
                    and metrics["profit_factor"] > 1
                )

                if survive:
                    survivors += 1

                print(
                    "EQUITY_BASE_COST_ROW "
                    f"symbol={symbol} "
                    f"trades={metrics['trades']} "
                    f"gross_pnl={gross_pnl} "
                    f"gross_pf="
                    f"{gross_metric['profit_factor']} "
                    f"gross_expectancy="
                    f"{gross_metric['expectancy']} "
                    f"commission={commission_total} "
                    f"slippage={slippage_total} "
                    f"total_cost={total_cost} "
                    f"net_pnl={metrics['net_pnl']} "
                    f"net_expectancy="
                    f"{metrics['expectancy']} "
                    f"net_profit_factor="
                    f"{metrics['profit_factor']} "
                    f"net_winrate="
                    f"{metrics['winrate']} "
                    f"max_drawdown="
                    f"{metrics['max_drawdown']} "
                    f"cost_to_gross_ratio="
                    f"{cost_to_gross_ratio} "
                    f"survive_after_base_costs="
                    f"{int(survive)}"
                )

    print(
        "SUMMARY_ROW "
        f"symbols={len(SYMBOLS)} "
        f"survivors={survivors}"
    )

    print(
        "base_costs_used=1"
    )

    print(
        "execution_spread_impact_used=0"
    )

    print(
        "economic_edge_claimed=0"
    )

    print(
        "runtime_changed=0"
    )

    print(
        "execution_changed=0"
    )

    print(
        "orders_changed=0"
    )

    print(
        "fills_changed=0"
    )

    print(
        "micro_live_allowed=0"
    )

    print(
        "VERDICT="
        "TREND_PULLBACK_CANONICAL_EQUITY_BASE_COST_VALIDATION_V1_READY"
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
