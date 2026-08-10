from __future__ import annotations

import importlib.util
import json
import os
import sys
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path

import psycopg2
from psycopg2.extras import RealDictCursor


ROOT = Path("/opt/finam-core")

SCREEN_PATH = ROOT / (
    "src/scripts/research/"
    "build_universe_trend_pullback_canonical_adapter_screen_v1.py"
)

CONFIG_PATH = ROOT / (
    "config/research/"
    "trend_pullback_canonical_robustness_v1.json"
)

SYMBOL = "USDRUBF@RTSX"
STRATEGY_CODE = "TREND_PULLBACK_V1"

LOT_UNITS = Decimal("1000")

TAKER_RATE = (
    Decimal("0.00462")
    / Decimal("100")
)

BASELINE_SLIPPAGE_RT = Decimal("2")
STRESS_SLIPPAGE_RT = Decimal("20")


@dataclass(frozen=True)
class NetTrade:
    gross_pnl: Decimal
    commission: Decimal
    slippage: Decimal
    total_cost: Decimal
    net_pnl: Decimal


def dec(value) -> Decimal:
    return Decimal(str(value or 0))


def load_screen():
    name = (
        "trend_pullback_canonical_screen_"
        "for_futures_base_cost_validation"
    )

    spec = importlib.util.spec_from_file_location(
        name,
        SCREEN_PATH,
    )

    if spec is None or spec.loader is None:
        raise RuntimeError(
            "ERROR=CANONICAL_SCREEN_IMPORT_FAILED"
        )

    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module

    try:
        spec.loader.exec_module(module)
    except Exception:
        sys.modules.pop(name, None)
        raise

    return module


def net_trade(
    trade,
    *,
    slippage_round_trip_rub: Decimal,
) -> NetTrade:
    gross_pnl_rub = (
        dec(trade.gross_pnl)
        * LOT_UNITS
    )

    entry_notional_rub = (
        dec(trade.entry_price)
        * LOT_UNITS
    )

    exit_notional_rub = (
        dec(trade.exit_price)
        * LOT_UNITS
    )

    commission = (
        entry_notional_rub * TAKER_RATE
        + exit_notional_rub * TAKER_RATE
    )

    total_cost = (
        commission
        + slippage_round_trip_rub
    )

    return NetTrade(
        gross_pnl=gross_pnl_rub,
        commission=commission,
        slippage=slippage_round_trip_rub,
        total_cost=total_cost,
        net_pnl=(
            gross_pnl_rub
            - total_cost
        ),
    )


def metrics(
    trades: list[NetTrade],
) -> dict[str, Decimal | int]:
    values = [
        trade.net_pnl
        for trade in trades
    ]

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

    total = sum(
        values,
        Decimal("0"),
    )

    count = len(values)

    expectancy = (
        total / Decimal(count)
        if count
        else Decimal("0")
    )

    profit_factor = (
        gross_profit / gross_loss
        if gross_loss > 0
        else (
            Decimal("Infinity")
            if gross_profit > 0
            else Decimal("0")
        )
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
        "trades": count,
        "net_pnl": total,
        "expectancy": expectancy,
        "profit_factor": profit_factor,
        "wins": len(wins),
        "losses": len(losses),
        "max_drawdown": max_drawdown,
        "commission": sum(
            (
                trade.commission
                for trade in trades
            ),
            Decimal("0"),
        ),
        "slippage": sum(
            (
                trade.slippage
                for trade in trades
            ),
            Decimal("0"),
        ),
        "total_cost": sum(
            (
                trade.total_cost
                for trade in trades
            ),
            Decimal("0"),
        ),
    }


def main() -> int:
    screen = load_screen()

    cfg = json.loads(
        CONFIG_PATH.read_text()
    )

    baseline = next(
        (
            variant
            for variant in cfg["variants"]
            if variant.get("code") == "BASELINE"
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
        cfg["screen_exit_horizon"][
            "hold_bars"
        ]
    )

    parameters["hold_bars"] = hold_bars

    development_fraction = dec(
        cfg["development_fraction"]
    )

    minimum_oos_trades = int(
        cfg["minimum_oos_trades"]
    )

    conn = psycopg2.connect(
        os.environ["DATABASE_URL"]
    )

    conn.set_session(
        readonly=True,
        autocommit=False,
    )

    try:
        with conn.cursor(
            cursor_factory=RealDictCursor
        ) as cur:
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
                  AND timeframe=%s
                ORDER BY ts
                """,
                (
                    SYMBOL,
                    cfg["timeframe"],
                ),
            )

            rows = cur.fetchall()

    finally:
        conn.rollback()
        conn.close()

    if not rows:
        raise RuntimeError(
            "ERROR=USDRUBF_MARKET_BARS_MISSING"
        )

    bars = [
        screen.MarketBar(
            ts=row["ts"],
            open=dec(row["open"]),
            high=dec(row["high"]),
            low=dec(row["low"]),
            close=dec(row["close"]),
            volume=dec(row["volume"]),
        )
        for row in rows
    ]

    development_end = int(
        Decimal(len(bars))
        * development_fraction
    )

    canonical_trades = (
        screen.build_canonical_trades(
            bars,
            parameters,
            development_end,
            len(bars),
        )
    )

    if (
        len(canonical_trades)
        < minimum_oos_trades
    ):
        raise RuntimeError(
            "ERROR=INSUFFICIENT_OOS_TRADES "
            f"trades={len(canonical_trades)} "
            f"minimum={minimum_oos_trades}"
        )

    gross_metric = screen.gross_metrics(
        canonical_trades
    )

    scenarios = (
        (
            "REGISTRY_BASELINE",
            BASELINE_SLIPPAGE_RT,
        ),
        (
            "ONE_TICK_STRESS",
            STRESS_SLIPPAGE_RT,
        ),
    )

    results = {}

    print(
        "=== TREND PULLBACK CANONICAL "
        "FUTURES BASE COST VALIDATION V1 ==="
    )

    print(f"symbol={SYMBOL}")
    print(f"strategy_code={STRATEGY_CODE}")
    print(f"timeframe={cfg['timeframe']}")

    print(
        "BASELINE_PARAMETERS "
        f"fast_ma_period="
        f"{parameters['fast_ma_period']} "
        f"slow_ma_period="
        f"{parameters['slow_ma_period']} "
        f"atr_period="
        f"{parameters['atr_period']} "
        f"pullback_atr_multiplier="
        f"{parameters['pullback_atr_multiplier']} "
        f"hold_bars={hold_bars}"
    )

    print(
        f"development_fraction="
        f"{development_fraction}"
    )

    print(
        f"development_end="
        f"{development_end}"
    )

    print(
        f"market_bars={len(bars)}"
    )

    print(
        f"canonical_oos_trades="
        f"{len(canonical_trades)}"
    )

    print(
        "gross_price_expectancy="
        f"{gross_metric['expectancy']}"
    )

    print(
        "gross_price_profit_factor="
        f"{gross_metric['profit_factor']}"
    )

    for scenario_code, slippage in scenarios:
        net_trades = [
            net_trade(
                trade,
                slippage_round_trip_rub=(
                    slippage
                ),
            )
            for trade in canonical_trades
        ]

        metric = metrics(
            net_trades
        )

        gross_pnl_rub = sum(
            (
                trade.gross_pnl
                for trade in net_trades
            ),
            Decimal("0"),
        )

        survive = (
            int(metric["trades"])
            >= minimum_oos_trades
            and dec(metric["expectancy"])
            > Decimal("0")
            and dec(metric["profit_factor"])
            > Decimal("1")
        )

        results[scenario_code] = survive

        print(
            "FUTURES_BASE_COST_ROW "
            f"scenario={scenario_code} "
            f"trades={metric['trades']} "
            f"gross_pnl_rub={gross_pnl_rub} "
            f"commission={metric['commission']} "
            f"slippage={metric['slippage']} "
            f"total_cost={metric['total_cost']} "
            f"net_pnl={metric['net_pnl']} "
            f"net_expectancy="
            f"{metric['expectancy']} "
            f"net_profit_factor="
            f"{metric['profit_factor']} "
            f"wins={metric['wins']} "
            f"losses={metric['losses']} "
            f"max_drawdown="
            f"{metric['max_drawdown']} "
            f"survive={int(survive)}"
        )

    baseline_survives = results[
        "REGISTRY_BASELINE"
    ]

    stress_survives = results[
        "ONE_TICK_STRESS"
    ]

    if not baseline_survives:
        verdict = (
            "REJECT_AFTER_BASE_COSTS"
        )

    elif not stress_survives:
        verdict = (
            "FRAGILE_AFTER_EXECUTION_STRESS"
        )

    else:
        verdict = (
            "SURVIVE_AFTER_BASE_COSTS"
        )

    print(
        f"final_status={verdict}"
    )

    print(
        "commission_model="
        "MOEX_MAKER_TAKER_FALLBACK"
    )

    print(
        "entry_liquidity_role=TAKER"
    )

    print(
        "exit_liquidity_role=TAKER"
    )

    print(
        "canonical_monetary_scale="
        "PRICE_DELTA_X_1000_RUB"
    )

    print("funding_used=0")
    print("funding_separate=1")

    print("db_writes_performed=0")
    print("runtime_changed=0")
    print("execution_changed=0")
    print("orders_changed=0")
    print("fills_changed=0")

    # Даже SURVIVE здесь ещё не является
    # окончательным economic edge:
    # funding layer пока не применён.
    print("economic_edge_claimed=0")
    print("micro_live_allowed=0")

    print(
        "VERDICT="
        "TREND_PULLBACK_CANONICAL_"
        "FUTURES_BASE_COST_VALIDATION_V1_READY"
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
