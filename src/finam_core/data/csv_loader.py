import csv
from datetime import datetime
from typing import List
from finam_core.backtest.engine import Bar


class CSVBarLoader:

    @staticmethod
    def load(path: str) -> List[Bar]:

        bars = []

        with open(path, newline="") as f:
            reader = csv.DictReader(f)

            for row in reader:
                bars.append(
                    Bar(
                        timestamp=datetime.fromisoformat(row["timestamp"]),
                        open=float(row["open"]),
                        high=float(row["high"]),
                        low=float(row["low"]),
                        close=float(row["close"]),
                        volume=float(row["volume"]),
                    )
                )

        return bars