from __future__ import annotations

import importlib.util
import sys
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

MONITOR_PATH = (
    ROOT
    / "scripts"
    / "research"
    / "run_ngu6_frozen_day_oos_monitor_v1.py"
)

SPEC = importlib.util.spec_from_file_location(
    "run_ngu6_frozen_day_oos_monitor_v1",
    MONITOR_PATH,
)

if SPEC is None or SPEC.loader is None:
    raise RuntimeError(
        "monitor_module_spec_load_failed"
    )

monitor = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = monitor
SPEC.loader.exec_module(monitor)


def test_oos3_boundary_is_frozen():
    assert monitor.OOS3_BOUNDARY == datetime(
        2026, 8, 8, 12, 45,
        tzinfo=timezone.utc,
    )


def test_day_trade_inside_session():
    assert monitor.is_day_trade(
        datetime(
            2026, 8, 10, 10, 0,
            tzinfo=timezone.utc,
        ),
        datetime(
            2026, 8, 10, 10, 25,
            tzinfo=timezone.utc,
        ),
    )


def test_trade_outside_day_session_rejected():
    assert not monitor.is_day_trade(
        datetime(
            2026, 8, 10, 16, 0,
            tzinfo=timezone.utc,
        ),
        datetime(
            2026, 8, 10, 16, 25,
            tzinfo=timezone.utc,
        ),
    )


def test_cross_day_trade_rejected():
    assert not monitor.is_day_trade(
        datetime(
            2026, 8, 10, 15, 50,
            tzinfo=timezone.utc,
        ),
        datetime(
            2026, 8, 11, 8, 10,
            tzinfo=timezone.utc,
        ),
    )


def test_monitor_does_not_read_public_market_bars():
    source = MONITOR_PATH.read_text()

    assert "FROM public.market_bars" not in source


def test_monitor_routes_via_persisted_native_dataset():
    source = MONITOR_PATH.read_text()

    assert (
        "load_persisted_dataset_snapshot"
        in source
    )


def test_monitor_reuses_existing_contract_spec_loader():
    source = MONITOR_PATH.read_text()

    assert "FORWARD_OBSERVER_SCRIPT" in source
    assert "load_contract_spec_at" in source
    assert (
        "analytics.instrument_contract_spec_v1"
        not in source
    )


def test_monitor_does_not_duplicate_contract_spec_sql():
    source = MONITOR_PATH.read_text()

    assert (
        "FROM analytics.market_contract_spec_v1"
        not in source
    )
