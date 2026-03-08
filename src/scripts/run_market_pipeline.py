# src/scripts/run_market_pipeline.py
# Русский коммент: тонкий entrypoint для Pipeline B.

import os
import time

from finam_core.events.event_bus import EventBus
from finam_core.adapters.grpc.market_data import FinamMarketDataClient
from finam_core.execution.paper_engine import PaperExecutionEngine
from finam_core.accounting.position_manager import PositionManager
from finam_core.accounting.portfolio_manager import PortfolioManager
from finam_core.risk.risk_engine import RiskEngine
from finam_core.strategy.once_buy import OnceBuyStrategy
from finam_core.pipelines.paper_pipeline import PaperTradingPipeline
# Русский коммент: грузим .env для запуска скрипта напрямую (24/7 режим)
try:
    from dotenv import load_dotenv
    load_dotenv(override=False)
except Exception:
    pass
ACCOUNT_ID = os.getenv("FINAM_ACCOUNT_ID") or os.getenv("ACCOUNT_ID") or "1943312"


def main():
    os.environ.setdefault("EXECUTION_MODE", "paper")

    symbol = os.getenv("SYMBOL") or "GAZP@MISX"
    run_secs = float(os.getenv("RUN_SECS") or "0")
    starting_cash = float(os.getenv("STARTING_CASH") or "100000")
    md_hb = float(os.getenv("MD_HEARTBEAT_SEC") or "10")

    print(f"Starting PAPER market pipeline. account={ACCOUNT_ID} symbol={symbol}", flush=True)

    bus = EventBus()

    # PM — источник истины
    pm = PositionManager(starting_cash=starting_cash)
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
    strategy = OnceBuyStrategy(symbol)

    pipeline = PaperTradingPipeline(bus, portfolio, pm, risk, paper, strategy)
    pipeline.attach()

    # MD: с поддержкой разных сигнатур
    print("Starting MD...", flush=True)
    try:
        md = FinamMarketDataClient(bus, heartbeat_sec=md_hb)
    except TypeError:
        try:
            md = FinamMarketDataClient(bus, heartbeat=md_hb)
        except TypeError:
            md = FinamMarketDataClient(bus)

    md.start([symbol])

    deadline = time.time() + run_secs if run_secs and run_secs > 0 else None
    try:
        while True:
            if deadline is not None and time.time() >= deadline:
                print("RUN_SECS reached, exit", flush=True)
                return
            time.sleep(0.2)
    finally:
        # Русский коммент: безопасная остановка (если метод stop существует)
        try:
            if hasattr(md, "stop") and callable(getattr(md, "stop")):
                md.stop()
        except Exception:
            pass
        print("DONE", flush=True)


if __name__ == "__main__":
    main()