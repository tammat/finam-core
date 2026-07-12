from __future__ import annotations

from scripts import build_strategy_execution_runner_v1 as engine


engine.RUNNER_VERSION = "STRATEGY_EXECUTION_RUNNER_V2"
engine.ENGINE_NAME = "STRATEGY_EXECUTION_RUNNER_V2"


if __name__ == "__main__":
    engine.main()
