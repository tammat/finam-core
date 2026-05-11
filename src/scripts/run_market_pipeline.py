# -*- coding: utf-8 -*-
"""run_market_pipeline.py — тонкий entrypoint для Pipeline B.

Pipeline B:
QUOTE -> Strategy -> Risk -> PaperExecution -> publish(FILL) -> Accounting(PM.apply_fill)

Русский коммент: этот файл специально держим "тонким".
Вся логика пайплайна живёт в finam_core.pipelines.paper_pipeline.
"""

from __future__ import annotations

import os
from finam_core.risk.real_stock_safety_gate import RealStockSafetyGate
import time
import argparse
import signal

# предотвращаем BrokenPipe при использовании grep/pipe
signal.signal(signal.SIGPIPE, signal.SIG_DFL)

import sys

# безопасный вывод: подавляет BrokenPipeError при пайпах/grep
class _SafeStdout:
    def __init__(self, wrapped):
        self._wrapped = wrapped
    def write(self, s):
        try:
            return self._wrapped.write(s)
        except BrokenPipeError:
            return 0
    def flush(self):
        try:
            return self._wrapped.flush()
        except BrokenPipeError:
            return None
    def __getattr__(self, name):
        return getattr(self._wrapped, name)

sys.stdout = _SafeStdout(sys.stdout)

from dotenv import load_dotenv
from finam_core.reconciliation.startup_recovery_gate import StartupRecoveryGate
load_dotenv()

def parse_args():
    import argparse
    import os

    parser = argparse.ArgumentParser(description="Finam PAPER pipeline (Pipeline B).")

    parser.add_argument("--symbol", default=os.getenv("SYMBOL") or "NGH6@RTSX")
    parser.add_argument(
        "--symbols",
        default=os.getenv("SYMBOLS") or "",
        help="Comma-separated list of symbols",
    )
    parser.add_argument(
        "--strategy",
        default=os.getenv("PIPELINE_STRATEGY") or "once_buy",
        choices=("once_buy", "simple_reactive", "breakout_reactive", "strategy_stack", "vwap_bands_mr"),
    )

    parser.add_argument("--run-secs", type=float, default=float(os.getenv("RUN_SECS") or "0"))
    parser.add_argument("--starting-cash", type=float, default=float(os.getenv("STARTING_CASH") or "100000"))
    parser.add_argument("--portfolio-snapshot-path", default=os.getenv("PORTFOLIO_SNAPSHOT_PATH") or "")
    parser.add_argument("--portfolio-refresh-sec", type=float, default=float(os.getenv("PORTFOLIO_REFRESH_SEC") or "0"))
    parser.add_argument("--md-heartbeat-sec", type=float, default=float(os.getenv("MD_HEARTBEAT_SEC") or "10"))
    parser.add_argument("--md-first-quote-grace-sec", type=float, default=float(os.getenv("MD_FIRST_QUOTE_GRACE_SEC") or "60"))

    parser.add_argument("--risk-soft", action="store_true", default=(os.getenv("RISK_SOFT") == "1"))
    parser.add_argument("--exit-on-fill", action="store_true", default=(os.getenv("EXIT_ON_FILL", "1") == "1"))

    parser.add_argument("--quote-log-every", type=float, default=float(os.getenv("QUOTE_LOG_EVERY") or "0"))
    parser.add_argument("--debug", action="store_true", default=(os.getenv("MD_DEBUG") == "1"))

    parser.add_argument("--enable-filter-engine", action="store_true", default=(os.getenv("ENABLE_FILTER_ENGINE") == "1"))
    parser.add_argument("--filter-profile", default=os.getenv("FILTER_PROFILE") or "")
    parser.add_argument("--tradeability-gate", default=os.getenv("TRADEABILITY_GATE") or "")
    parser.add_argument("--tradeability-min-range-atr", type=float, default=float(os.getenv("TRADEABILITY_MIN_RANGE_ATR") or "1.5"))
    parser.add_argument("--tradeability-max-range-atr", type=float, default=float(os.getenv("TRADEABILITY_MAX_RANGE_ATR") or "0.0"))
    parser.add_argument("--regime-ema-slope", default=os.getenv("REGIME_EMA_SLOPE") or "")
    parser.add_argument("--regime-adaptive-mode", default=os.getenv("REGIME_ADAPTIVE_MODE") or "")

    parser.add_argument(
        "--feed",
        choices=["real", "sim"],
        default="real",
        help="Market data source",
    )

    return parser.parse_args()



from finam_core.events.event_bus import EventBus
from finam_core.adapters.grpc.market_data import FinamMarketDataClient
from finam_core.execution.paper_engine import PaperExecutionEngine
from finam_core.accounting.position_manager import PositionManager
from finam_core.accounting.portfolio_manager import PortfolioManager
from finam_core.events.event_store_factory import EventStoreFactory
from finam_core.events.event_projection_bridge import EventProjectionBridge
from finam_core.projections.realtime_projection_subscriber import RealtimeProjectionSubscriber
from finam_core.risk.risk_engine import RiskEngine
from finam_core.strategy.once_buy import OnceBuyStrategy
from finam_core.strategy.simple_reactive import SimpleReactiveStrategy
from finam_core.strategy.breakout_reactive import BreakoutReactiveStrategy
from finam_core.signals.strategy_stack import StrategyStack
from finam_core.strategy.vwap_bands_mr import VWAPBandsMRStrategy
from finam_core.strategy.vwap_bands_mr import VWAPBandsMRStrategy
from finam_core.pipelines.paper_pipeline import PaperTradingPipeline
from finam_core.accounting.portfolio_bootstrap import load_portfolio_snapshot, bootstrap_position_manager
from finam_core.recovery.recovery_orchestrator import RecoveryOrchestrator

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
    p.add_argument("--strategy", default=os.getenv("PIPELINE_STRATEGY") or "once_buy", choices=("once_buy", "simple_reactive", "breakout_reactive", "strategy_stack", "vwap_bands_mr"))

    # Русский коммент: symbols — список подписки MarketData (мульти-инструмент)


    p.add_argument("--run-secs", type=float, default=float(os.getenv("RUN_SECS") or "0"))
    p.add_argument("--starting-cash", type=float, default=float(os.getenv("STARTING_CASH") or "100000"))
    p.add_argument("--portfolio-snapshot-path", default=os.getenv("PORTFOLIO_SNAPSHOT_PATH") or "")
    p.add_argument("--portfolio-refresh-sec", type=float, default=float(os.getenv("PORTFOLIO_REFRESH_SEC") or "0"))
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


def main() -> None:
    args = parse_args()

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

    # Русский коммент: если задан снимок портфеля, стартуем от фактического состояния.
    if args.portfolio_snapshot_path:
        snapshot = load_portfolio_snapshot(args.portfolio_snapshot_path)
        bootstrap_position_manager(pm, snapshot)
        print(
            f"PORTFOLIO_BOOTSTRAP path={args.portfolio_snapshot_path} "
            f"cash={getattr(pm, 'cash', None)} starting_cash={getattr(pm, 'starting_cash', None)} "
            f"positions={len(getattr(pm, 'positions', {}))}",
            flush=True,
        )

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
    elif args.strategy == "breakout_reactive":
        strategy = BreakoutReactiveStrategy(symbol=args.symbol)

    elif args.strategy == "strategy_stack":
        strategies = [
            BreakoutReactiveStrategy(symbol=args.symbol),
        ]

        # Русский коммент: SimpleReactive включаем только для тестов
        if os.getenv("ENABLE_TEST_STRATEGY", "0") == "1":
            strategies.append(SimpleReactiveStrategy())

        strategy = StrategyStack(strategies)

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


    # Русский комментарий: StartupRecoveryGate выполняется до запуска market data.
    if os.getenv("ENABLE_STARTUP_RECOVERY_GATE", "1") == "1":
        startup_gate = StartupRecoveryGate(
            orders_client=orders_client if "orders_client" in locals() else None,
            managed_service=managed_positions if "managed_positions" in locals() else None,
            positions_client=positions_client if "positions_client" in locals() else None,
            oms_journal=oms_journal if "oms_journal" in locals() else None,
            rebuild_aggregate_type=os.getenv("STARTUP_REBUILD_AGGREGATE_TYPE", "portfolio"),
            rebuild_aggregate_id=os.getenv("STARTUP_REBUILD_AGGREGATE_ID"),
        )

    startup_decision = startup_gate.check()

    if not startup_decision.allowed:
        print(
                "STARTUP_RECOVERY_GATE_BLOCK "
                f"reason={startup_decision.reason} "
                f"issues={startup_decision.issues}",
                flush=True,
            )
        raise SystemExit(2)

        print(
            "STARTUP_RECOVERY_GATE_OK "
            f"reason={startup_decision.reason}",
            flush=True,
        )


    # Русский комментарий: регистрируем shared EventBus для всех EventStoreFactory.create().
    try:
        EventStoreFactory.configure(event_bus=bus)
        print("PIPE_EVENT_STORE_FACTORY_BUS_OK", flush=True)
    except Exception as exc:
        print(f"PIPE_EVENT_STORE_FACTORY_BUS_FAILED error={exc}", flush=True)

    # Русский комментарий: realtime projections подключаются к EventBus безопасно.
    if os.getenv("ENABLE_REALTIME_PROJECTIONS", "1") == "1":
        try:
            projection_bridge = EventProjectionBridge(
                event_bus=bus,
                subscriber=RealtimeProjectionSubscriber(),
            )
            projection_bridge_result = projection_bridge.attach()
            print(
                f"PIPE_PROJECTION_BRIDGE_OK mode={projection_bridge_result.mode}",
                flush=True,
            )
        except Exception as exc:
            print(
                f"PIPE_PROJECTION_BRIDGE_FAILED error={exc}",
                flush=True,
            )

    # Русский комментарий: финальный recovery gate до запуска MarketData.
    if os.getenv("ENABLE_RECOVERY_ORCHESTRATOR", "1") == "1":
        recovery_result = RecoveryOrchestrator().run_checks()
        if not recovery_result.ok:
            print(
                f"PIPE_RECOVERY_ORCHESTRATOR_BLOCK reason={recovery_result.reason}",
                flush=True,
            )
        raise SystemExit(2)

        print(
            f"PIPE_RECOVERY_ORCHESTRATOR_OK reason={recovery_result.reason}",
            flush=True,
        )

    print("Starting MD...", flush=True)
    # Русский коммент: MarketDataClient у нас нормализован под heartbeat_sec, но оставим fallback
    if args.feed == "sim":
        from finam_core.market.sim_feed import SimFeed
        md = SimFeed(symbol=symbol, event_bus=bus)
        print("SIM FEED ENABLED", flush=True)
    else:
        try:
            # === AUTO SWITCH: SIMULATION OR REAL MARKET DATA ===
            if os.getenv("SIMULATE_MARKET", "0") == "1":
                print("RUN_PIPELINE: using SimFeed (simulation)", flush=True)
                from finam_core.market.sim_feed import SimFeed
                md = SimFeed(symbol=symbol, event_bus=bus)
            else:
                print("RUN_PIPELINE: using FinamMarketDataClient", flush=True)
                md = FinamMarketDataClient(bus, heartbeat_sec=args.md_heartbeat_sec)
        except TypeError:
            md = FinamMarketDataClient(bus)

    md.start(symbols)

    portfolio_refresh_sec = float(args.portfolio_refresh_sec or 0.0)
    last_portfolio_refresh_ts = 0.0

    deadline = (time.time() + run_secs) if run_secs > 0 else None
    try:
        while True:
            now = time.time()

            if (
                args.portfolio_snapshot_path
                and portfolio_refresh_sec > 0
                and (now - last_portfolio_refresh_ts) >= portfolio_refresh_sec
            ):
                try:
                    snapshot = load_portfolio_snapshot(args.portfolio_snapshot_path)
                    bootstrap_position_manager(pm, snapshot)
                    last_portfolio_refresh_ts = now
                    print(
                        f"PORTFOLIO_REFRESH path={args.portfolio_snapshot_path} "
                        f"cash={getattr(pm, 'cash', None)} starting_cash={getattr(pm, 'starting_cash', None)} "
                        f"positions={len(getattr(pm, 'positions', {}))}",
                        flush=True,
                    )
                except Exception as e:
                    print(f"PORTFOLIO_REFRESH_FAILED error={e}", flush=True)

            if deadline is not None and now >= deadline:
                print("RUN_SECS reached, exit", flush=True)
                return
            time.sleep(0.2)
    finally:
        try:
            if hasattr(md, "stop") and callable(getattr(md, "stop")):
                md.stop()
        except Exception:
            pass
        try:
            print("DONE", flush=True)
        except BrokenPipeError:
            pass


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        # Русский коммент: штатная остановка без traceback и без BrokenPipe при пайпах
        try:
            print("STOPPED by KeyboardInterrupt", flush=True)
        except BrokenPipeError:
            pass
        raise SystemExit(0)
