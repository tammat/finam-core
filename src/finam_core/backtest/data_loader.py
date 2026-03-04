import csv
from datetime import datetime
from .engine import Bar


def load_csv(path: str):

    bars = []

    with open(path) as f:
        reader = csv.DictReader(f)

        for row in reader:
            bars.append(
                Bar(
                    timestamp=datetime.fromisoformat(row["timestamp"]),
                    open=float(row["open"]),
                    high=float(row["high"]),
                    low=float(row["low"]),
                    close=float(row["close"]),
                    volume=float(row["volume"])
                )
            )

    return bars