from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from dateutil.relativedelta import relativedelta


@dataclass(frozen=True)
class WalkForwardWindow:
    index: int
    train_from: date
    train_to: date
    test_from: date
    test_to: date


class WalkForwardEngine:
    """Русский комментарий: строит rolling train/test окна для walk-forward research."""

    def build_windows(
        self,
        *,
        start_date: date,
        end_date: date,
        train_months: int,
        test_months: int,
        step_months: int = 1,
    ) -> list[WalkForwardWindow]:
        windows: list[WalkForwardWindow] = []

        i = 1
        train_from = start_date

        while True:
            train_to = train_from + relativedelta(months=train_months) - relativedelta(days=1)
            test_from = train_to + relativedelta(days=1)
            test_to = test_from + relativedelta(months=test_months) - relativedelta(days=1)

            if test_to > end_date:
                break

            windows.append(
                WalkForwardWindow(
                    index=i,
                    train_from=train_from,
                    train_to=train_to,
                    test_from=test_from,
                    test_to=test_to,
                )
            )

            i += 1
            train_from = train_from + relativedelta(months=step_months)

        return windows
