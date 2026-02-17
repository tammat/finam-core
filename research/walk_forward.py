# research/walk_forward.py
# Комментарии: walk-forward сплит без shuffle, только по времени (anti-leakage)

from dataclasses import dataclass
import pandas as pd


@dataclass
class WalkForwardConfig:
    train_frac: float = 0.7
    val_frac: float = 0.15
    test_frac: float = 0.15


def walk_forward_split(df: pd.DataFrame, cfg: WalkForwardConfig) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    if "timestamp" not in df.columns:
        raise ValueError("dataset must have 'timestamp' column")

    df = df.sort_values("timestamp").reset_index(drop=True)

    n = len(df)
    if n < 50:
        raise ValueError(f"dataset too small for walk-forward split: n={n}")

    if abs((cfg.train_frac + cfg.val_frac + cfg.test_frac) - 1.0) > 1e-9:
        raise ValueError("train/val/test fractions must sum to 1.0")

    n_train = int(n * cfg.train_frac)
    n_val = int(n * cfg.val_frac)

    train = df.iloc[:n_train].copy()
    val = df.iloc[n_train:n_train + n_val].copy()
    test = df.iloc[n_train + n_val:].copy()

    if len(train) == 0 or len(val) == 0 or len(test) == 0:
        raise ValueError(f"bad split sizes: train={len(train)} val={len(val)} test={len(test)}")

    return train, val, test