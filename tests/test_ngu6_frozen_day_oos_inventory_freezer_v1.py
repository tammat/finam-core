from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

MODULE_PATH = (
    ROOT
    / "scripts"
    / "research"
    / "freeze_ngu6_frozen_day_oos_inventory_v1.py"
)


def load_module():
    spec = importlib.util.spec_from_file_location(
        "ngu6_freezer_test",
        MODULE_PATH,
    )

    assert spec is not None
    assert spec.loader is not None

    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)

    return module


def write_monitor_output(path: Path):
    path.write_text(
        "\n".join(
            (
                "MONITOR_VERSION=NGU6_FROZEN_DAY_OOS_MONITOR_V1",
                "DATASET_ROWS=8000",
                "DATASET_LAST=2026-08-10T12:00:00+00:00",
                "NEW_COMPLETED_DAY_TRADES=1",
                "INVENTORY_FROZEN=0",
                "PNL_REVEALED=0",
                (
                    "TRADE_IDENTITY="
                    "1|2026-08-10T10:00:00+00:00|"
                    "LONG|2026-08-10T10:25:00+00:00|219"
                ),
                "VERDICT=NEW_FROZEN_DAY_INVENTORY_READY",
            )
        )
        + "\n",
        encoding="utf-8",
    )


def test_freeze_is_atomic_and_idempotent(
    tmp_path,
    monkeypatch,
):
    module = load_module()

    monkeypatch.setattr(
        module,
        "FREEZE_DIR",
        tmp_path / "freeze",
    )

    monitor_output = tmp_path / "monitor.out"
    write_monitor_output(monitor_output)

    first = module.freeze(monitor_output)
    second = module.freeze(monitor_output)

    assert first[0] == "CREATED"
    assert second[0] == "ALREADY_FROZEN"

    assert first[1] == second[1]
    assert first[2] == second[2]

    artifacts = list(
        (tmp_path / "freeze").glob(
            "inventory_*.json"
        )
    )

    assert len(artifacts) == 1


def test_frozen_artifact_contains_no_pnl(
    tmp_path,
    monkeypatch,
):
    module = load_module()

    monkeypatch.setattr(
        module,
        "FREEZE_DIR",
        tmp_path / "freeze",
    )

    monitor_output = tmp_path / "monitor.out"
    write_monitor_output(monitor_output)

    _, artifact, _ = module.freeze(
        monitor_output
    )

    text = artifact.read_text(
        encoding="utf-8"
    )

    assert '"pnl_revealed": false' in text

    forbidden = (
        "net_pnl",
        "gross_pnl",
        "market_pnl",
        "commission",
        "slippage",
        "entry_price",
        "exit_price",
    )

    for token in forbidden:
        assert token not in text


def test_freezer_rejects_revealed_pnl(
    tmp_path,
    monkeypatch,
):
    module = load_module()

    monkeypatch.setattr(
        module,
        "FREEZE_DIR",
        tmp_path / "freeze",
    )

    monitor_output = tmp_path / "monitor.out"
    write_monitor_output(monitor_output)

    text = monitor_output.read_text(
        encoding="utf-8"
    ).replace(
        "PNL_REVEALED=0",
        "PNL_REVEALED=1",
    )

    monitor_output.write_text(
        text,
        encoding="utf-8",
    )

    try:
        module.freeze(monitor_output)
    except module.FreezeContractError as exc:
        assert (
            "pnl_revealed_contract_violation"
            in str(exc)
        )
    else:
        raise AssertionError(
            "revealed pnl was not rejected"
        )


def test_freezer_rejects_identity_count_mismatch(
    tmp_path,
    monkeypatch,
):
    module = load_module()

    monkeypatch.setattr(
        module,
        "FREEZE_DIR",
        tmp_path / "freeze",
    )

    monitor_output = tmp_path / "monitor.out"
    write_monitor_output(monitor_output)

    text = monitor_output.read_text(
        encoding="utf-8"
    ).replace(
        "NEW_COMPLETED_DAY_TRADES=1",
        "NEW_COMPLETED_DAY_TRADES=2",
    )

    monitor_output.write_text(
        text,
        encoding="utf-8",
    )

    try:
        module.freeze(monitor_output)
    except module.FreezeContractError as exc:
        assert (
            "trade_identity_count_mismatch"
            in str(exc)
        )
    else:
        raise AssertionError(
            "identity count mismatch was not rejected"
        )
