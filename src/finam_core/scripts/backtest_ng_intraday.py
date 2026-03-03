#src/scripts/backtest_ng_intraday.py
import requests
import pandas as pd
from datetime import datetime

BASE_URL = "https://iss.moex.com/iss/engines/futures/markets/forts/securities/NG-3.26/candles.json"
INTERVAL = 1  # 1-minute candles
DATE_FROM = "2024-01-01"
DATE_TILL = "2024-03-02"

def fetch_all():
    all_rows = []
    start = 0

    while True:
        params = {
            "interval": INTERVAL,
            "from": DATE_FROM,
            "till": DATE_TILL,
            "start": start,
        }

        r = requests.get(BASE_URL, params=params)
        data = r.json()

        candles = data["candles"]["data"]
        columns = data["candles"]["columns"]

        if not candles:
            break

        df = pd.DataFrame(candles, columns=columns)
        all_rows.append(df)

        print(f"Loaded batch start={start}, rows={len(df)}")

        start += len(df)

    if not all_rows:
        raise RuntimeError("No data returned")

    return pd.concat(all_rows, ignore_index=True)


def resample_to_5m(df):
    df["begin"] = pd.to_datetime(df["begin"])
    df = df.set_index("begin")

    df_5m = df.resample("5T").agg({
        "open": "first",
        "close": "last",
        "high": "max",
        "low": "min",
        "volume": "sum"
    }).dropna()

    return df_5m.reset_index()


if __name__ == "__main__":
    df_1m = fetch_all()
    print("Total 1m rows:", len(df_1m))

    df_5m = resample_to_5m(df_1m)
    print("Total 5m rows:", len(df_5m))

    df_5m.to_csv("NGH6_5m.csv", index=False)
    print("Saved NGH6_5m.csv")