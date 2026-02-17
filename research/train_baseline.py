# Комментарии:
# Time-aware walk-forward evaluation
# Никакого random split.
# Expanding window validation.

import json
import numpy as np
import pandas as pd
from dataclasses import dataclass
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score, roc_auc_score


@dataclass
class TrainConfig:
    train_size: float = 0.7
    step_size: float = 0.1
    threshold: float = 0.5


def walk_forward_split(df, train_size, step_size):

    n = len(df)
    train_end = int(n * train_size)
    step = int(n * step_size)

    splits = []

    while train_end + step <= n:
        train = df.iloc[:train_end]
        test = df.iloc[train_end:train_end + step]
        splits.append((train, test))
        train_end += step

    return splits


def train_and_evaluate(cfg: TrainConfig):

    df = pd.read_csv("data/export/ngh6_dataset.csv")

    feature_cols = ["return_1", "return_mean", "volatility", "z_score", "momentum"]

    splits = walk_forward_split(df, cfg.train_size, cfg.step_size)
    print("Total rows:", len(df))
    print("Total splits:", len(splits))
    for i, (train, test) in enumerate(splits):
        print(f"Split {i}: train={len(train)} test={len(test)}")

    all_preds = []
    all_true = []

    for train, test in splits:

        X_train = train[feature_cols].values
        y_train = train["label"].values

        X_test = test[feature_cols].values
        y_test = test["label"].values

        model = LogisticRegression()
        model.fit(X_train, y_train)

        probs = model.predict_proba(X_test)[:, 1]
        preds = np.where(probs > cfg.threshold, 1, -1)

        all_preds.extend(preds)
        all_true.extend(y_test)

    all_preds = np.array(all_preds)
    all_true = np.array(all_true)

    metrics = {
        "accuracy": float(accuracy_score(all_true, all_preds)),
        "precision": float(precision_score(all_true, all_preds, pos_label=1)),
        "recall": float(recall_score(all_true, all_preds, pos_label=1)),
        "f1": float(f1_score(all_true, all_preds, pos_label=1)),
        "roc_auc": float(roc_auc_score((all_true == 1).astype(int),
                                       (all_preds == 1).astype(int)))
    }

    print(json.dumps(metrics, indent=2))

    return metrics


if __name__ == "__main__":
    train_and_evaluate(TrainConfig())