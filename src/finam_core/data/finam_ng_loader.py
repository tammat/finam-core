import csv
from datetime import datetime
from typing import List
from finam_core.backtest.engine import Bar


class FinamNGLoader:

    @staticmethod
    def load(path: str) -> List[Bar]:

        bars = []

        with open(path, newline="") as f:
            reader = csv.DictReader(f)

            for row in reader:

                # begin обычно ISO: 2026-03-03T10:15:00
                ts = datetime.fromisoformat(row["begin"])

                bars.append(
                    Bar(
                        timestamp=ts,
                        open=float(row["open"]),
                        high=float(row["high"]),
                        low=float(row["low"]),
                        close=float(row["close"]),
                        volume=float(row["volume"]),
                    )
                )

        return bars