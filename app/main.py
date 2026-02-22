# app/main.py

import os
from dotenv import load_dotenv
from pathlib import Path
from config.settings import Settings
from storage.postgres import PostgresStorage

from execution.sim_executor import SimExecutionEngine
from execution.oms import OMS

from accounting.position_manager import PositionManager
from accounting.portfolio_manager import PortfolioManager

from risk.risk_engine import RiskEngine
from core.engine import Engine
ENV_PATH = Path(__file__).resolve().parents[1] / ".env"   # корень репо = на уровень выше папки app
load_dotenv(dotenv_path=ENV_PATH)

def main() -> int:
    load_dotenv(dotenv_path=".env")
    print("ENV_PATH:", ENV_PATH)
    print("ENV_EXISTS:", ENV_PATH.exists())
    print("POSTGRES_DSN:", "SET" if os.getenv("POSTGRES_DSN") else "MISSING")

    dsn = os.getenv("POSTGRES_DSN")
    if not dsn:
        raise RuntimeError(
            "POSTGRES_DSN is not set. Add it to .env or export env var.\n"
            "Example:\n"
            "POSTGRES_DSN=postgresql://finam:YOUR_PASSWORD@localhost:5432/finam_core"
        )

    mode = os.getenv("MODE", Settings.MODE)

    # --- Storage ---
    storage = PostgresStorage(dsn)

    # --- Execution ---
    execution_engine = SimExecutionEngine()
    oms = OMS(storage=storage, execution_engine=execution_engine)

    # --- Accounting ---
    position_manager = PositionManager()
    portfolio_manager = PortfolioManager(initial_cash=Settings.INITIAL_CASH)

    # --- Risk ---
    risk_engine = RiskEngine(
        position_manager=position_manager,
        portfolio_manager=portfolio_manager,
    )

    # --- Core Engine ---
    engine = Engine(
        oms=oms,
        position_manager=position_manager,
        portfolio_manager=portfolio_manager,
        risk_engine=risk_engine,
        storage=storage,
    )

    processed = engine.run()

    # Итоговый срез состояния
    state = portfolio_manager.compute_state(position_manager, engine_now_utc())

    print(f"MODE: {mode}")
    print(f"Processed events: {processed}")
    print(f"Cash: {state.cash}")
    print(f"Equity: {state.equity}")
    print(f"Exposure: {state.exposure}")
    print(f"Drawdown: {state.drawdown}")

    return 0


def engine_now_utc():
    # отдельной функцией, чтобы не тянуть timezone-логику через весь код
    from datetime import datetime, timezone
    return datetime.now(timezone.utc)


if __name__ == "__main__":
    raise SystemExit(main())