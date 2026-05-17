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
            case regime
                when 'ACCUMULATION' then '🟢 Накопление'
                when 'DISTRIBUTION' then '🔴 Распределение'
                when 'TREND_INITIATION' then '🚀 Запуск тренда'
                when 'BREAKOUT_TRAP' then '🪤 Ловушка пробоя'
                when 'INSTITUTIONAL_PARTICIPATION' then '🏦 Активность крупного участника'
                when 'NORMAL_FLOW' then '⚪ Обычная активность'
                else '❔ Нет данных'
            end as "Режим крупного потока",

            case bias
                when 'LONG_BIAS' then '🟢⬆ Приоритет покупок'
                when 'SHORT_BIAS' then '🔴⬇ Приоритет продаж'
                when 'NEUTRAL' then '⚪ Преимущество отсутствует'
                when 'MOMENTUM_BIAS' then '🚀 Импульсное движение'
                when 'FADE_BIAS' then '🪤 Возврат после ложного пробоя'
                else '❔ Нет данных'
            end as "Смещение",
            round(confidence::numeric, 6) as "Уверенность",
            ts as "Время"
        from institutional_flow_regime_events
        order by symbol, ts desc;
    """,

    "opportunity_latest.tsv": """
        select distinct on (symbol)
            symbol as "Инструмент",
            case asset_class
                when 'EQUITY' then 'Акции'
                when 'FUTURES_CONTINUOUS' then 'Фьючерсы / непрерывный контекст'
                when 'FUTURES' then 'Фьючерсы'
                else coalesce(asset_class, '❔ Нет данных')
            end as "Класс актива",

            case regime
                when 'trend_down' then '🔴 Нисходящий тренд'
                when 'trend_up' then '🟢 Восходящий тренд'
                when 'trend_up_high_vol' then '🚀 Восходящий тренд / высокая волатильность'
                when 'trend_down_high_vol' then '🔻 Нисходящий тренд / высокая волатильность'
                when 'continuous_smart_money_context' then '🔗 Контекст крупного потока'
                when 'unknown_trend_unknown_vol' then '❔ Режим не определён'
                else coalesce(regime, '❔ Нет данных')
            end as "Рыночный режим",
            round(coalesce(atr_pct,0)::numeric, 6) as "ATR %",
            round(coalesce(rvol,0)::numeric, 6) as "RVOL",
            round(coalesce(smart_money_score,0)::numeric, 6) as "Оценка крупного потока",
            case coalesce(smart_money_label, 'NO_DATA')
                when 'SMART_MONEY_CANDIDATE' then '🏦 Кандидат крупного потока'
                when 'INSTITUTIONAL_GRADE' then '🏛️ Институциональный уровень'
                when 'NORMAL_FLOW' then '⚪ Обычный поток'
                when 'NO_SMART_MONEY_DATA' then '❔ Нет данных'
                when 'NO_DATA' then '❔ Нет данных'
                else coalesce(smart_money_label, '❔ Нет данных')
            end as "Метка крупного потока",
            calculated_at as "Время расчёта"
        from market_opportunity_metrics
        order by symbol, calculated_at desc;
    """,

    "strategy_signal_quality_proxy.tsv": """
        select
            case coalesce(payload->>'institutional_flow_regime', 'UNKNOWN')
                when 'ACCUMULATION' then '🟢 Накопление'
                when 'DISTRIBUTION' then '🔴 Распределение'
                when 'TREND_INITIATION' then '🚀 Запуск тренда'
                when 'BREAKOUT_TRAP' then '🪤 Ловушка пробоя'
                when 'INSTITUTIONAL_PARTICIPATION' then '🏦 Активность крупного участника'
                when 'NORMAL_FLOW' then '⚪ Обычная активность'
                else '❔ Нет данных'
            end as "Режим крупного потока",
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
