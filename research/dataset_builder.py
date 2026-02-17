import numpy as np
import pandas as pd

from strategy.feature_engine import FeatureEngine
from research.label_engine import LabelEngine


class DatasetBuilder:
    """
    Research-only dataset generator.
    Builds X (features) and y (labels).
    """

    def __init__(self, storage, window=10, horizon=5):
        self.storage = storage
        self.window = window
        self.horizon = horizon

        self.feature_engine = FeatureEngine(window=window)
        self.label_engine = LabelEngine(horizon=horizon)

    # ---------------------------------------------------
    # LOAD PRICES
    # ---------------------------------------------------

    def load_prices(self, symbol):
        with self.storage.conn.cursor() as cur:
            cur.execute("""
                SELECT ts, close
                FROM historical_prices
                WHERE symbol = %s
                ORDER BY ts ASC
            """, (symbol,))

            rows = cur.fetchall()

        if not rows:
            return None, None

        timestamps = [r[0] for r in rows]
        prices = np.array([r[1] for r in rows])

        return timestamps, prices

    # ---------------------------------------------------
    # BUILD DATASET
    # ---------------------------------------------------

    def build(self, symbol):

        timestamps, prices = self.load_prices(symbol)

        if prices is None:
            raise ValueError("No historical data found.")

        feature_rows = []
        valid_timestamps = []

        # Generate rolling features
        for i in range(len(prices)):
            self.feature_engine.update(prices[i])

            if not self.feature_engine.ready():
                continue

            features = self.feature_engine.compute()
            feature_rows.append(features)
            valid_timestamps.append(timestamps[i])

        if not feature_rows:
            raise ValueError("Not enough data to build features.")

        # Convert features to DataFrame
        X = pd.DataFrame(feature_rows)

        # Align prices for label generation
        aligned_prices = prices[self.window - 1:]

        y = self.label_engine.binary_labels(aligned_prices)

        # Remove last horizon rows (NaN labels)
        X = X.iloc[:-self.horizon]
        y = y[:-self.horizon]

        dataset = X.copy()
        dataset["label"] = y

        dataset["timestamp"] = valid_timestamps[:len(dataset)]

        return dataset

    # ---------------------------------------------------
    # EXPORT
    # ---------------------------------------------------

    def export_csv(self, dataset, path):
        dataset.to_csv(path, index=False)