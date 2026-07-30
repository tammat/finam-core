from datetime import datetime, timedelta, timezone

import pytest

from finam_core.research.purged_split import purged_temporal_split


def test_walkforward_v4_records_label_horizon_embargo() -> None:
    from scripts.run_checkpointed_walkforward_v4 import _label_horizon_bars

    assert _label_horizon_bars({"hold": 7}) == 7
    assert _label_horizon_bars({"hold": 5, "exit_policy_code": "DYNAMIC_EXIT_V1", "exit_max_holding_bars": 20}) == 20


UTC = timezone.utc


def test_purges_cross_boundary_and_embargoes_early_test_rows() -> None:
    base = datetime(2026, 7, 30, tzinfo=UTC)
    rows = [
        ("train", base, base + timedelta(minutes=5)),
        ("overlap", base + timedelta(minutes=8), base + timedelta(minutes=25)),
        ("embargo", base + timedelta(minutes=20), base + timedelta(minutes=21)),
        ("test", base + timedelta(minutes=31), base + timedelta(minutes=40)),
    ]

    split = purged_temporal_split(
        rows,
        train_ratio=0.5,
        start=lambda row: row[1],
        end=lambda row: row[2],
        embargo=timedelta(minutes=10),
    )

    assert [row[0] for row in split.train] == ["train"]
    assert [row[0] for row in split.test] == ["test"]
    assert split.purged == 1
    assert split.embargoed == 1
    assert all(train[2] < test[1] for train in split.train for test in split.test)


def test_rejects_invalid_split_configuration() -> None:
    now = datetime.now(UTC)
    rows = [(now, now), (now + timedelta(minutes=1), now + timedelta(minutes=2))]
    with pytest.raises(ValueError):
        purged_temporal_split(rows, train_ratio=1.0, start=lambda row: row[0], end=lambda row: row[1], embargo=timedelta(0))
