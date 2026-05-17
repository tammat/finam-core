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
    coalesce(payload->>'strategy', payload->>'source', trade_source, origin, 'UNKNOWN') as strategy,
    
        case coalesce(payload->>'institutional_flow_regime', 'UNKNOWN')
            when 'ACCUMULATION' then '🟢 Накопление'
            when 'DISTRIBUTION' then '🔴 Распределение'
            when 'TREND_INITIATION' then '🚀 Запуск тренда'
            when 'BREAKOUT_TRAP' then '🪤 Ловушка пробоя'
            when 'INSTITUTIONAL_PARTICIPATION' then '🏦 Активность крупного участника'
            when 'NORMAL_FLOW' then '⚪ Обычная активность'
            else coalesce(latest_regime.regime_ru, '❔ Нет данных')
        end as institutional_regime
    ,
    coalesce(payload->>'adaptive_position_multiplier', '1.00') as adaptive_multiplier
from trades t
left join lateral (
    select
        case r.regime
            when 'ACCUMULATION' then '🟢 Накопление'
            when 'DISTRIBUTION' then '🔴 Распределение'
            when 'TREND_INITIATION' then '🚀 Запуск тренда'
            when 'BREAKOUT_TRAP' then '🪤 Ловушка пробоя'
            when 'INSTITUTIONAL_PARTICIPATION' then '🏦 Активность крупного участника'
            when 'NORMAL_FLOW' then '⚪ Обычная активность'
            else '❔ Нет данных'
        end as regime_ru
    from institutional_flow_regime_events r
    where r.symbol = t.symbol
    order by r.ts desc
    limit 1
) latest_regime on true
where qty > 0
order by created_at asc, id asc;
"""


class PositionBook:
    def __init__(self):
        self.qty = 0.0
        self.avg_price = 0.0

    def add(self, qty: float, price: float):
        if self.qty + qty <= 0:
            self.qty = 0
            self.avg_price = 0
            return

        total_cost = (self.avg_price * self.qty) + (price * qty)
        self.qty += qty
        self.avg_price = total_cost / self.qty

    def reduce(self, qty: float):
        self.qty -= qty
        if self.qty <= 0:
            self.qty = 0
            self.avg_price = 0


def main() -> int:
    database_url = os.environ["DATABASE_URL"]

    estimated_tax_rate = float(
        os.getenv("ANALYTICS_ESTIMATED_TAX_RATE", "0.15")
    )

    out_dir = Path("reports/strategy_analytics")
    out_dir.mkdir(parents=True, exist_ok=True)

    out_file = out_dir / "realized_pnl_engine.tsv"

    with psycopg2.connect(database_url) as conn:
        with conn.cursor() as cur:
            cur.execute(SQL)
            rows = cur.fetchall()

    books = defaultdict(PositionBook)

    stats = defaultdict(lambda: {
        "trades": 0,
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
            strategy,
            institutional_regime,
            adaptive_multiplier,
        ) = row

        key = (
            symbol,
            strategy,
            institutional_regime,
            adaptive_multiplier,
        )

        qty = float(qty)
        price = float(price)
        commission = float(commission)

        stats[key]["commission"] += commission

        book = books[symbol]

        if side.upper() == "BUY":
            book.add(qty, price)
            continue

        if side.upper() != "SELL":
            continue

        if book.qty <= 0:
            continue

        matched_qty = min(book.qty, qty)

        gross_pnl = (
            (price - book.avg_price) * matched_qty
        )

        tax = max(gross_pnl, 0) * estimated_tax_rate

        net_pnl = (
            gross_pnl
            - commission
            - tax
        )

        stats[key]["trades"] += 1
        stats[key]["gross_pnl"] += gross_pnl
        stats[key]["tax"] += tax
        stats[key]["net_pnl"] += net_pnl

        if net_pnl >= 0:
            stats[key]["wins"] += 1
        else:
            stats[key]["losses"] += 1

        book.reduce(matched_qty)

    result_rows = []

    for key, s in stats.items():
        (
            symbol,
            strategy,
            institutional_regime,
            adaptive_multiplier,
        ) = key

        total = s["wins"] + s["losses"]

        winrate = (
            (s["wins"] / total) * 100
            if total > 0
            else 0
        )

        result_rows.append([
            symbol,
            strategy,
            institutional_regime,
            adaptive_multiplier,
            s["trades"],
            round(s["gross_pnl"], 2),
            round(s["commission"], 2),
            round(s["tax"], 2),
            round(s["net_pnl"], 2),
            round(winrate, 2),
        ])

    result_rows.sort(
        key=lambda x: x[8],
        reverse=True,
    )

    with out_file.open("w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f, delimiter="\t")

        writer.writerow([
            "Инструмент",
            "Стратегия",
            "Режим крупного капитала",
            "Мультипликатор позиции",
            "Закрытых сделок",
            "Валовая прибыль",
            "Комиссии",
            "Налог",
            "Чистая прибыль после издержек и налога",
            "Доля прибыльных сделок, %",
        ])

        writer.writerows(result_rows)

    print(
        f"OK: realized pnl engine rows={len(result_rows)} "
        f"file={out_file}"
    )

    for row in result_rows[:20]:
        print(row)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
