from __future__ import annotations

import csv
import os
from pathlib import Path

import psycopg2


REPORTS = {
    "pnl_by_execution_symbol.tsv": """
        select
            symbol as "Инструмент исполнения",
            count(*) as "Сделок",
            round(avg(qty)::numeric, 6) as "Средний объём",
            round(sum(qty * price)::numeric, 2) as "Оборот"
        from trades
        group by 1
        order by "Оборот" desc nulls last;
    """,

    "exposure_by_adaptive_multiplier.tsv": """
        select
            coalesce(payload->>'adaptive_position_multiplier', '1.00') as "Мультипликатор позиции",
            count(*) as "Сделок",
            round(avg(qty)::numeric, 6) as "Средний объём",
            round(sum(qty * price)::numeric, 2) as "Оборот"
        from trades
        group by 1
        order by 1;
    """,

    "execution_lineage.tsv": """
        select
            coalesce(payload->>'requested_symbol', symbol) as "Сигнальный инструмент",
            coalesce(payload->>'execution_symbol', symbol) as "Инструмент исполнения",
            coalesce(payload->>'continuous_symbol', 'NONE') as "Непрерывный контекст",
            count(*) as "Сделок",
            round(sum(qty * price)::numeric, 2) as "Оборот"
        from trades
        group by 1,2,3
        order by "Оборот" desc nulls last;
    """,

    "institutional_flow_latest.tsv": """
        select distinct on (symbol)
            symbol as "Инструмент",
            regime as "Режим крупного потока",
            bias as "Смещение",
            round(confidence::numeric, 6) as "Уверенность",
            ts as "Время"
        from institutional_flow_regime_events
        order by symbol, ts desc;
    """,

    "opportunity_latest.tsv": """
        select distinct on (symbol)
            symbol as "Инструмент",
            asset_class as "Класс актива",
            regime as "Рыночный режим",
            round(coalesce(atr_pct,0)::numeric, 6) as "ATR %",
            round(coalesce(rvol,0)::numeric, 6) as "RVOL",
            round(coalesce(smart_money_score,0)::numeric, 6) as "Оценка крупного потока",
            coalesce(smart_money_label, 'NO_DATA') as "Метка крупного потока",
            calculated_at as "Время расчёта"
        from market_opportunity_metrics
        order by symbol, calculated_at desc;
    """,

    "strategy_signal_quality_proxy.tsv": """
        select
            coalesce(payload->>'institutional_flow_regime', '❔ Нет данных') as "Режим крупного потока",
            coalesce(payload->>'adaptive_position_multiplier', '1.00') as "Мультипликатор позиции",
            count(*) as "Сделок",
            round(avg(qty)::numeric, 6) as "Средний объём",
            round(sum(qty * price)::numeric, 2) as "Оборот"
        from trades
        group by 1,2
        order by "Оборот" desc nulls last;
    """,
}


def write_report(cur, out_file: Path, sql: str) -> int:
    cur.execute(sql)
    rows = cur.fetchall()
    headers = [desc[0] for desc in cur.description]

    with out_file.open("w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f, delimiter="\t")
        writer.writerow(headers)
        writer.writerows(rows)

    return len(rows)


def main() -> int:
    database_url = os.environ["DATABASE_URL"]

    out_dir = Path("reports/strategy_analytics")
    out_dir.mkdir(parents=True, exist_ok=True)

    total_reports = 0

    with psycopg2.connect(database_url) as conn:
        with conn.cursor() as cur:
            for filename, sql in REPORTS.items():
                rows = write_report(cur, out_dir / filename, sql)
                total_reports += 1
                print(f"OK: report={filename} rows={rows}")

    print(f"OK: strategy analytics reports={total_reports} dir={out_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
