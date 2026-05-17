from __future__ import annotations

import csv
import os
from collections import defaultdict
from pathlib import Path

import psycopg2


SQL = """
select
    created_at,
    symbol,
    side,
    qty,
    price,
    coalesce(commission, 0) as commission,

    case coalesce(payload->>'institutional_flow_regime', 'UNKNOWN')
        when 'ACCUMULATION' then '🟢 Накопление'
        when 'DISTRIBUTION' then '🔴 Распределение'
        when 'TREND_INITIATION' then '🚀 Запуск тренда'
        when 'BREAKOUT_TRAP' then '🪤 Ловушка пробоя'
        when 'INSTITUTIONAL_PARTICIPATION' then '🏦 Активность крупного участника'
        when 'NORMAL_FLOW' then '⚪ Обычная активность'
        else '❔ Нет данных'
    end as regime_ru,

    coalesce(payload->>'strategy', payload->>'source', trade_source, origin, '❔ Нет данных') as strategy

from trades
where qty > 0
order by created_at asc, id asc;
"""


class PositionBook:
    def __init__(self) -> None:
        self.qty = 0.0
        self.avg_price = 0.0

    def buy(self, qty: float, price: float) -> None:
        if self.qty + qty <= 0:
            self.qty = 0.0
            self.avg_price = 0.0
            return

        total = self.qty * self.avg_price + qty * price
        self.qty += qty
        self.avg_price = total / self.qty

    def sell(self, qty: float) -> float:
        matched = min(self.qty, qty)
        self.qty -= matched

        if self.qty <= 0:
            self.qty = 0.0
            self.avg_price = 0.0

        return matched


def main() -> int:
    database_url = os.environ["DATABASE_URL"]
    tax_rate = float(os.getenv("ANALYTICS_ESTIMATED_TAX_RATE", "0.15"))

    out_dir = Path("reports/strategy_analytics")
    out_dir.mkdir(parents=True, exist_ok=True)

    out_file = out_dir / "pnl_by_institutional_regime.tsv"

    with psycopg2.connect(database_url) as conn:
        with conn.cursor() as cur:
            cur.execute(SQL)
            rows = cur.fetchall()

    books = defaultdict(PositionBook)

    stats = defaultdict(lambda: {
        "closed_trades": 0,
        "gross_pnl": 0.0,
        "commission": 0.0,
        "tax": 0.0,
        "net_pnl": 0.0,
        "wins": 0,
        "losses": 0,
    })

    for row in rows:
        (
            created_at,
            symbol,
            side,
            qty,
            price,
            commission,
            regime_ru,
            strategy,
        ) = row

        qty = float(qty)
        price = float(price)
        commission = float(commission)

        book = books[symbol]
        key = regime_ru

        stats[key]["commission"] += commission

        if str(side).upper() == "BUY":
            book.buy(qty, price)
            continue

        if str(side).upper() != "SELL":
            continue

        if book.qty <= 0:
            continue

        matched = book.sell(qty)
        gross = (price - book.avg_price) * matched
        tax = max(gross, 0.0) * tax_rate
        net = gross - commission - tax

        stats[key]["closed_trades"] += 1
        stats[key]["gross_pnl"] += gross
        stats[key]["tax"] += tax
        stats[key]["net_pnl"] += net

        if net >= 0:
            stats[key]["wins"] += 1
        else:
            stats[key]["losses"] += 1

    result = []

    for regime, s in stats.items():
        total = s["wins"] + s["losses"]
        winrate = (s["wins"] / total * 100) if total else 0.0
        avg_net = (s["net_pnl"] / s["closed_trades"]) if s["closed_trades"] else 0.0

        result.append([
            regime,
            s["closed_trades"],
            round(s["gross_pnl"], 2),
            round(s["commission"], 2),
            round(s["tax"], 2),
            round(s["net_pnl"], 2),
            round(avg_net, 4),
            round(winrate, 2),
        ])

    result.sort(key=lambda x: x[5], reverse=True)

    with out_file.open("w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f, delimiter="\t")
        writer.writerow([
            "Режим крупного капитала",
            "Закрытых сделок",
            "Валовая прибыль",
            "Комиссии",
            "Налог",
            "Чистая прибыль после издержек и налога",
            "Средняя чистая прибыль на сделку",
            "Доля прибыльных сделок, %",
        ])
        writer.writerows(result)

    print(f"OK: pnl by institutional regime rows={len(result)} file={out_file}")
    for row in result:
        print(row)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
