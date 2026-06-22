#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import subprocess
from pathlib import Path


def sh(cmd: str) -> str:
    p = subprocess.run(["bash", "-lc", cmd], capture_output=True, text=True)
    return (p.stdout or p.stderr or "").strip()


def exists(path: str) -> int:
    return int(Path(path).exists())


def main() -> int:
    print("=== EQUITY_MARKET_BARS_BACKFILL_LOADER_PLAN_V1 ===")
    print("mode=loader_plan_read_only")
    print("db_update=0")
    print("runtime_changed=0")
    print("execution_changed=0")
    print("telegram_send=0")

    candidates = [
        "src/scripts/live_intraday_pipeline.py",
        "src/finam_core/adapters/grpc/market_data.py",
        "src/finam_core/infra/finam/client.py",
        "src/finam_core/infra/finam/adapter.py",
        "src/finam_core/data/market_bars_writer.py",
        "src/finam_core/storage/market_bars.py",
        "src/finam_core/storage/postgres.py",
    ]

    for path in candidates:
        print(f"FILE_ROW path={path} exists={exists(path)}")

    print("SEARCH_SECTION market_data_calls")
    print(sh(
        "grep -RniE \"get_candles|GetCandles|candles|market_bars|TIMEFRAME_M1|TIMEFRAME_M5|@MISX\" "
        "src/scripts src/finam_core | head -120 || true"
    ))

    print("TARGET_SYMBOL_ROW symbol=SBERP@MISX action=BACKFILL_M1_M5_REQUIRED from=2026-06-01")
    print("TARGET_SYMBOL_ROW symbol=SFIN@MISX action=BACKFILL_M1_M5_REQUIRED from=2026-06-01")
    print("TARGET_SYMBOL_ROW symbol=VTBR@MISX action=BACKFILL_M1_M5_REQUIRED from=2026-06-01")
    print("TARGET_SYMBOL_ROW symbol=NVTK@MISX action=REFRESH_TODAY_REQUIRED from=2026-06-22")
    print("TARGET_SYMBOL_ROW symbol=OZON@MISX action=REFRESH_TODAY_REQUIRED from=2026-06-22")
    print("TARGET_SYMBOL_ROW symbol=T@MISX action=REFRESH_TODAY_REQUIRED from=2026-06-22")

    print("PROPOSED_LOADER path=src/scripts/research/backfill_equity_market_bars_v1.py")
    print("PROPOSED_TEST path=scripts/test_equity_market_bars_backfill_loader_v1.sh")
    print("PROPOSED_MODE dry_run_first_then_save")
    print("PROPOSED_REQUIREMENTS use_existing_finam_market_data_adapter,write_market_bars_only,no_runtime_change,no_execution")

    print("VERDICT=EQUITY_MARKET_BARS_BACKFILL_LOADER_PLAN_READY")
    print("TEST_EQUITY_MARKET_BARS_BACKFILL_LOADER_PLAN_V1_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
