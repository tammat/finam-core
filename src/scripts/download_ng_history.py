import requests
import pandas as pd

# Пример для FORTS (нужно уточнить точное имя инструмента)
url = "https://iss.moex.com/iss/engines/futures/markets/forts/securities/NGH6/candles.json"

params = {
    "interval": 10,   # 10 = 5m
    "from": "2024-01-01",
    "till": "2024-03-01"
}

r = requests.get(url, params=params)
data = r.json()

cols = data["candles"]["columns"]
rows = data["candles"]["data"]

df = pd.DataFrame(rows, columns=cols)
df.to_csv("ngh6_5m.csv", index=False)

print("Saved ngh6_5m.csv")