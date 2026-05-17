from __future__ import annotations

import csv
import os
from pathlib import Path

import psycopg2


SQL = """
with latest_flow as (
    select distinct on (symbol)
        symbol,
        regime,
        bias,
        confidence
    from institutional_flow_regime_events
    order by symbol, ts desc
),

latest_metrics as (
    select distinct on (symbol)
        symbol,
        atr_pct,
        smart_money_score,
        regime as market_regime
    from market_opportunity_metrics
    order by symbol, calculated_at desc
)

select
    f.symbol,
    f.regime,
    f.bias,
    f.confidence,
    coalesce(m.atr_pct, 0.01) as atr_pct,
    coalesce(m.smart_money_score, 0) as smart_money_score,
    coalesce(m.market_regime, 'unknown') as market_regime
from latest_flow f
left join latest_metrics m
    on m.symbol = f.symbol
where f.regime in (
    'ACCUMULATION',
    'TREND_INITIATION',
    'INSTITUTIONAL_PARTICIPATION'
)
order by f.confidence desc;
"""


def calculate_levels(
    confidence: float,
    atr_pct: float,
):
    # Русский комментарий:
    # базовая модель advisory:
    # entry = market
    # stop = 1 ATR
    # take = 2 ATR
    # RR >= 2

    entry = 100.0

    stop_distance = max(atr_pct * 100, 0.5)

    stop = round(entry - stop_distance, 2)

    take = round(entry + stop_distance * 2, 2)

    rr = round((take - entry) / (entry - stop), 2)

    if confidence >= 0.90:
        qty = "1.50x"
    elif confidence >= 0.75:
        qty = "1.25x"
    else:
        qty = "1.00x"

    probability = round(confidence * 100, 1)

    return {
        "entry": round(entry, 2),
        "stop": stop,
        "take": take,
        "rr": rr,
        "qty": qty,
        "probability": probability,
    }


def main() -> int:
    database_url = os.environ["DATABASE_URL"]

    out_dir = Path("reports")
    out_dir.mkdir(parents=True, exist_ok=True)

    out_file = out_dir / "execution_advisory.tsv"

    conn = psycopg2.connect(database_url)

    with conn:
        with conn.cursor() as cur:
            cur.execute(SQL)
            rows = cur.fetchall()

    result_rows = []

    for row in rows:
        (
            symbol,
            regime,
            bias,
            confidence,
            atr_pct,
            smart_money_score,
            market_regime,
        ) = row

        advisory = calculate_levels(
            float(confidence),
            float(atr_pct),
        )

        result_rows.append([
            symbol,
            regime,
            bias,
            confidence,
            atr_pct,
            advisory["entry"],
            advisory["stop"],
            advisory["take"],
            advisory["rr"],
            advisory["qty"],
            advisory["probability"],
        ])

    with out_file.open("w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f, delimiter="\t")

        writer.writerow([
            "Инструмент",
            "Режим",
            "Bias",
            "Confidence",
            "ATR %",
            "Условная заявка на вход",
            "Стоп-лосс",
            "Тейк-профит",
            "R:R",
            "Размер позиции",
            "Вероятность профита %",
        ])

        writer.writerows(result_rows)

    print(
        f"OK: execution advisory rows={len(result_rows)} file={out_file}",
        flush=True,
    )

    for row in result_rows[:20]:
        print(row)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
