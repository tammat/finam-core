from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Callable, Sequence, TypeVar


T = TypeVar("T")


@dataclass(frozen=True)
class PurgedSplit:
    train: list[T]
    test: list[T]
    boundary: datetime
    test_start: datetime
    purged: int
    embargoed: int


def purged_temporal_split(
    rows: Sequence[T],
    *,
    train_ratio: float,
    start: Callable[[T], datetime],
    end: Callable[[T], datetime],
    embargo: timedelta,
) -> PurgedSplit:
    """Split interval-labelled observations without train/test information leakage.

    Observations whose label interval crosses the split boundary are purged.  Test
    observations beginning inside the post-boundary embargo are excluded as well.
    """
    if not 0.0 < train_ratio < 1.0:
        raise ValueError("train_ratio must be between 0 and 1")
    if embargo < timedelta(0):
        raise ValueError("embargo must be non-negative")
    if len(rows) < 2:
        raise ValueError("at least two observations are required")

    ordered = sorted(rows, key=lambda row: (start(row), end(row)))
    split_index = max(1, min(len(ordered) - 1, int(len(ordered) * train_ratio)))
    boundary = start(ordered[split_index])
    test_start = boundary + embargo

    train = [row for row in ordered if end(row) < boundary]
    test = [row for row in ordered if start(row) >= test_start]
    purged = sum(1 for row in ordered if start(row) < boundary <= end(row))
    embargoed = sum(1 for row in ordered if boundary <= start(row) < test_start)
    return PurgedSplit(train, test, boundary, test_start, purged, embargoed)
