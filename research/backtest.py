# Комментарии:
# Walk-forward equity backtest
# С комиссией и slippage

import numpy as np
import pandas as pd
from dataclasses import dataclass
from sklearn.linear_model import LogisticRegression


@dataclass
class BacktestConfig:
    train_size: float = 0.7
    step_size: float = 0.1
    threshold: float = 0.6
    commission: float = 0.0005
    slippage: float = 0.0005
    horizon: int = 5


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


def compute_equity(returns):
    return np.cumprod(1 + returns)


def sharpe_ratio(returns):
    if np.std(returns) == 0:
        return 0
    return np.mean(returns) / np.std(returns) * np.sqrt(252)


def max_drawdown(equity):
    peak = np.maximum.accumulate(equity)
    dd = (equity - peak) / peak
    return dd.min()


# Комментарии:
# PnL теперь считается на том же горизонте, что и label (H баров).
# Используем future price, а не return_1.

def run_backtest(cfg: BacktestConfig):
    df = pd.read_csv("data/export/ngh6_dataset.csv")

    # Загружаем реальные цены
    from storage.postgres import PostgresStorage
    storage = PostgresStorage()

    prices = storage.get_historical_prices("NGH6@RTSX")

    price_df = pd.DataFrame(prices)
    price_df.columns = ["timestamp", "close"]

    # Объединяем по timestamp
    # Приводим timestamp к datetime
    df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True)
    price_df["timestamp"] = pd.to_datetime(price_df["timestamp"], utc=True)
    df = df.merge(price_df, on="timestamp", how="left")
    feature_cols = ["return_1", "return_mean", "volatility", "z_score", "momentum"]

    splits = walk_forward_split(df, cfg.train_size, cfg.step_size)

    all_returns = []

    for train, test in splits:

        X_train = train[feature_cols].values
        y_train = train["label"].values
        X_test = test[feature_cols].values

        model = LogisticRegression()
        model.fit(X_train, y_train)

        probs = model.predict_proba(X_test)[:, 1]

        positions = np.where(
            probs > cfg.threshold, 1,
            np.where(probs < (1 - cfg.threshold), -1, 0)
        )

        # --- КОРРЕКТНЫЙ future return ---
        #future_price = test["close"].shift(-cfg.horizon)
        #future_return = (future_price - test["close"]) / test["close"]
        #future_return = future_return.fillna(0).values

        # Комментарии:
        # Non-overlapping trades execution model

        returns = []

        i = 0
        while i < len(test):

            signal = positions[i]

            if signal != 0:

                entry_price = test["close"].iloc[i]

                exit_index = i + cfg.horizon

                if exit_index >= len(test):
                    break

                exit_price = test["close"].iloc[exit_index]

                gross_return = (exit_price - entry_price) / entry_price

                trade_return = signal * gross_return

                cost = cfg.commission + cfg.slippage

                net_return = trade_return - cost

                returns.append(net_return)

                i = exit_index  # skip forward

            else:
                i += 1

        all_returns.extend(returns)
    all_returns = np.array(all_returns)

    equity = compute_equity(all_returns)

    results = {
        "total_return": float(equity[-1] - 1),
        "sharpe": float(sharpe_ratio(all_returns)),
        "max_drawdown": float(max_drawdown(equity)),
        "trades": int(np.sum(np.abs(all_returns) > 0))
    }

    print(results)

    return results


if __name__ == "__main__":
    run_backtest(BacktestConfig())