#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import subprocess
import sys
from datetime import datetime, time
from zoneinfo import ZoneInfo


MSK = ZoneInfo("Europe/Moscow")

STEPS = [
    ["src/scripts/research/build_multi_asset_breakout_signal_quality_history_v1.py", "--save"],
    ["src/scripts/research/build_multi_asset_compression_expansion_history_v1.py", "--migrate", "--save"],
    ["src/scripts/research/build_multi_asset_compression_follow_through_market_bars_v2.py", "--migrate", "--save"],
    ["src/scripts/research/build_real_trading_readiness_gates_v1.py"],
    ["src/scripts/research/build_monday_paper_startup_readiness_v1.py"],
]


def session_flags() -> tuple[bool, bool, bool]:
    now = datetime.now(MSK)

    # Русский комментарий: суббота и воскресенье исключаются из наблюдения.
    if now.weekday() >= 5:
        return False, False, False

    # Русский комментарий: акции наблюдаем с ранней сессии, фьючерсы — с основной FORTS-сессии.
    equity_session = time(6, 50) <= now.time() <= time(18, 50)
    futures_session = time(9, 0) <= now.time() <= time(23, 50)
    observation_session = equity_session or futures_session

    return equity_session, futures_session, observation_session


def is_moex_session_now() -> bool:
    return session_flags()[2]


def run_step(step: list[str]) -> bool:
    cmd = [sys.executable, *step]
    print("MOEX_SESSION_STEP_START", " ".join(cmd), flush=True)

    env = os.environ.copy()
    env["PYTHONPATH"] = "src"
    env["RUNTIME_ALLOW_TRADING"] = "0"
    env["EXECUTION_ENABLED"] = "0"
    env["REAL_TRADING_ENABLED"] = "0"

    result = subprocess.run(cmd, cwd="/opt/finam-core", env=env, check=False)

    ok = result.returncode == 0
    print(
        f"MOEX_SESSION_STEP_DONE ok={ok} code={result.returncode} step={step[0]}",
        flush=True,
    )
    return ok


def main() -> int:
    print("=== MOEX_SESSION_PAPER_OBSERVATION_V1 ===")
    print("runtime_allow_trading=0")
    print("execution_enabled=0")
    print("real_trading_enabled=0")
    equity_session, futures_session, observation_session = session_flags()
    print(f"equity_session_now={int(equity_session)}")
    print(f"futures_session_now={int(futures_session)}")
    print(f"moex_session_now={int(observation_session)}")

    if not observation_session:
        print("VERDICT=MOEX_SESSION_PAPER_OBSERVATION_SKIPPED_OUT_OF_SESSION")
        print("TEST_MOEX_SESSION_PAPER_OBSERVATION_V1_OK")
        return 0

    ok_all = True
    for step in STEPS:
        ok_all = run_step(step) and ok_all

    verdict = "MOEX_SESSION_PAPER_OBSERVATION_OK" if ok_all else "MOEX_SESSION_PAPER_OBSERVATION_FAILED"

    print("orders_create=0")
    print("execution_intents_create=0")
    print(f"VERDICT={verdict}")
    print("TEST_MOEX_SESSION_PAPER_OBSERVATION_V1_OK")

    return 0 if ok_all else 1


if __name__ == "__main__":
    raise SystemExit(main())
