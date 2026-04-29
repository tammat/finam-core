# -*- coding: utf-8 -*-
"""
run_market_pipeline.py — тонкий entrypoint для Pipeline B.

Pipeline B:
QUOTE -> Strategy -> Risk -> PaperExecution -> publish(FILL) -> Accounting(PM.apply_fill)

Русский коммент: этот файл специально держим "тонким".
Вся логика пайплайна живёт в finam_core.pipelines.paper_pipeline.
"""

import os
import time
import argparse

from finam_core.events.event_bus import EventBus
from finam_core.adapters.grpc.market_data import FinamMarketDataClient
from finam_core.execution.paper_engine import PaperExecutionEngine
from finam_core.accounting.position_manager import PositionManager
from finam_core.accounting.portfolio_manager import PortfolioManager
from finam_core.risk.risk_engine import RiskEngine
from finam_core.strategy.once_buy import OnceBuyStrategy
from finam_core.strategy.simple_reactive import SimpleReactiveStrategy
from finam_core.strategy.vwap_bands_mr import VWAPBandsMRStrategy
from finam_core.strategy.vwap_bands_mr import VWAPBandsMRStrategy
from finam_core.pipelines.paper_pipeline import PaperTradingPipeline

try:
    from finam_core.strategy.filters.regime_filters import FilterEngine
except Exception:
    FilterEngine = None

try:
    from finam_core.strategy.filters.filter_presets import get_filter_preset
except Exception:
    get_filter_preset = None

# Русский коммент: грузим .env (если python-dotenv установлен) — удобно для 24/7 запуска
try:
    from dotenv import load_dotenv  # type: ignore
    load_dotenv(override=False)
except Exception:
    pass

ACCOUNT_ID = os.getenv("FINAM_ACCOUNT_ID") or os.getenv("ACCOUNT_ID") or "1943312"


def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Finam PAPER pipeline (Pipeline B).")

    # Русский коммент: symbol — для стратегии (какой инструмент торгуем)
    p.add_argument("--symbol", default=os.getenv("SYMBOL") or "NGH6@RTSX")
    p.add_argument("--strategy", default=os.getenv("PIPELINE_STRATEGY") or "once_buy", choices=("once_buy", "simple_reactive", "vwap_bands_mr"))

    # Русский коммент: symbols — список подписки MarketData (мульти-инструмент)
    p.add_argument(
        "--symbols",
        default=os.getenv("SYMBOLS") or "",
        help="CSV list for MarketData subscription, e.g. NGH6@RTSX,GAZP@MISX",
    )

    p.add_argument("--run-secs", type=float, default=float(os.getenv("RUN_SECS") or "0"))
    p.add_argument("--starting-cash", type=float, default=float(os.getenv("STARTING_CASH") or "100000"))
    p.add_argument("--md-heartbeat-sec", type=float, default=float(os.getenv("MD_HEARTBEAT_SEC") or "10"))
    p.add_argument("--md-first-quote-grace-sec", type=float, default=float(os.getenv("MD_FIRST_QUOTE_GRACE_SEC") or "60"))

    # Русский коммент: режимы управления (можно и env)
    p.add_argument("--risk-soft", action="store_true", default=(os.getenv("RISK_SOFT") == "1"))
    p.add_argument("--exit-on-fill", action="store_true", default=(os.getenv("EXIT_ON_FILL", "1") == "1"))

    # Русский коммент: троттлинг вывода котировок (0 = выключено)
    p.add_argument("--quote-log-every", type=float, default=float(os.getenv("QUOTE_LOG_EVERY") or "0"))

    # Русский коммент: debug включает MD_DEBUG=1 (и всё отладочное в MarketData)
    p.add_argument("--debug", action="store_true", default=(os.getenv("MD_DEBUG") == "1"))

    p.add_argument("--enable-filter-engine", action="store_true", default=(os.getenv("ENABLE_FILTER_ENGINE") == "1"))
    p.add_argument("--filter-profile", default=os.getenv("FILTER_PROFILE") or "")
    p.add_argument("--tradeability-gate", default=os.getenv("TRADEABILITY_GATE") or "")
    p.add_argument("--tradeability-min-range-atr", type=float, default=float(os.getenv("TRADEABILITY_MIN_RANGE_ATR") or "1.5"))
    p.add_argument("--tradeability-max-range-atr", type=float, default=float(os.getenv("TRADEABILITY_MAX_RANGE_ATR") or "0.0"))
    p.add_argument("--regime-ema-slope", default=os.getenv("REGIME_EMA_SLOPE") or "")
    p.add_argument("--regime-adaptive-mode", default=os.getenv("REGIME_ADAPTIVE_MODE") or "")

    return p.parse_args()


def main() -> None:
    args = _parse_args()

    # Русский коммент: env-переменные — единый источник флагов внутри компонентов
    os.environ.setdefault("EXECUTION_MODE", "paper")

    if args.debug:
        os.environ["MD_DEBUG"] = "1"
    else:
        os.environ.pop("MD_DEBUG", None)

    if args.risk_soft:
        os.environ["RISK_SOFT"] = "1"
    else:
        os.environ["RISK_SOFT"] = "0"

    os.environ["EXIT_ON_FILL"] = "1" if args.exit_on_fill else "0"
    os.environ["QUOTE_LOG_EVERY"] = str(args.quote_log_every)
    os.environ["MD_HEARTBEAT_SEC"] = str(args.md_heartbeat_sec)
    os.environ["MD_FIRST_QUOTE_GRACE_SEC"] = str(args.md_first_quote_grace_sec)

    symbol = args.symbol

    # Русский коммент: если --symbols не задан, подписываемся хотя бы на symbol
    symbols_raw = args.symbols.strip()
    if symbols_raw:
        symbols = [s.strip() for s in symbols_raw.split(",") if s.strip()]
    else:
        symbols = [symbol]

    run_secs = float(args.run_secs or 0)
    starting_cash = float(args.starting_cash)

    print(f"Starting PAPER market pipeline. account={ACCOUNT_ID} symbol={symbol}", flush=True)

    bus = EventBus()

    # PM — источник истины для paper accounting
    pm = PositionManager(starting_cash=starting_cash)
    # Русский коммент: некоторые правила риска ждут эти атрибуты
    pm.cash = starting_cash
    pm.starting_cash = starting_cash
    pm.starting_capital = starting_cash

    # PortfolioManager оставляем для mark_price + risk context
    try:
        portfolio = PortfolioManager(starting_cash=starting_cash)
    except TypeError:
        try:
            portfolio = PortfolioManager(initial_cash=starting_cash)
        except TypeError:
            portfolio = PortfolioManager(starting_cash)

    setattr(portfolio, "position_manager", pm)

    risk = RiskEngine()
    paper = PaperExecutionEngine(slippage_coef=0.25, commission=0.0)
    if args.strategy == "simple_reactive":
        strategy = SimpleReactiveStrategy()
    elif args.strategy == "vwap_bands_mr":
        strategy = VWAPBandsMRStrategy(
            window=150,
            k=1.5,
            stop_pct=0.004,
            take_pct=0.0,
        )
    else:
        strategy = OnceBuyStrategy(symbol)

    filter_engine = None
    if args.enable_filter_engine:
        if FilterEngine is None:
            print("WARNING: ENABLE_FILTER_ENGINE=1, but FilterEngine import failed", flush=True)
        else:
            if args.filter_profile and get_filter_preset is not None:
                filter_params = get_filter_preset(symbol, args.filter_profile)
            else:
                filter_params = {
                    "tradeability_gate": args.tradeability_gate,
                    "tradeability_min_range_atr": args.tradeability_min_range_atr,
                    "tradeability_max_range_atr": args.tradeability_max_range_atr,
                    "regime_ema_slope": args.regime_ema_slope,
                    "regime_adaptive_mode": args.regime_adaptive_mode,
                }
            filter_engine = FilterEngine(filter_params)
            print(f"FilterEngine enabled params={filter_params}", flush=True)

    pipeline = PaperTradingPipeline(bus, portfolio, pm, risk, paper, strategy, filter_engine=filter_engine)
    pipeline.attach()

    print("Starting MD...", flush=True)
    # Русский коммент: MarketDataClient у нас нормализован под heartbeat_sec, но оставим fallback
    try:
        md = FinamMarketDataClient(bus, heartbeat_sec=args.md_heartbeat_sec)
    except TypeError:
        md = FinamMarketDataClient(bus)

    md.start(symbols)

    deadline = (time.time() + run_secs) if run_secs > 0 else None
    try:
        while True:
            if deadline is not None and time.time() >= deadline:
                print("RUN_SECS reached, exit", flush=True)
                return
            time.sleep(0.2)
    finally:
        try:
            if hasattr(md, "stop") and callable(getattr(md, "stop")):
                md.stop()
        except Exception:
            pass
        print("DONE", flush=True)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        # Русский коммент: штатная остановка от systemd/SIGINT не должна давать traceback в journalctl.
        print("STOPPED by KeyboardInterrupt", flush=True)
        raise SystemExit(0)
