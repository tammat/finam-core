create or replace view v_grafana_execution_lineage as
select
    coalesce(payload->>'continuous_symbol', 'NONE') as "🔗 Непрерывный инструмент",
    coalesce(payload->>'requested_symbol', symbol) as "📡 Сигнальный инструмент",
    coalesce(payload->>'execution_symbol', symbol) as "🎯 Инструмент исполнения",
    count(*) as "📊 Сделок",
    round(avg(qty)::numeric, 6) as "⚖️ Средний объём",
    round(sum(qty * price)::numeric, 2) as "💰 Оборот",
    max(ts) as "🕒 Последняя сделка"
from trades
group by 1,2,3;


create or replace view v_grafana_adaptive_position_exposure as
select
    coalesce(payload->>'adaptive_position_multiplier', '1.00') as "🎚️ Мультипликатор позиции",
    count(*) as "📊 Сделок",
    round(avg(qty)::numeric, 6) as "⚖️ Средний объём",
    round(sum(qty * price)::numeric, 2) as "💰 Оборот",
    max(ts) as "🕒 Последняя сделка"
from trades
group by 1;


create or replace view v_grafana_institutional_flow_state as
select distinct on (symbol)
    symbol as "📈 Инструмент",
    case regime
        when 'NORMAL_FLOW' then '⚪ Обычный поток'
        when 'ACCUMULATION' then '🟢 Накопление'
        when 'DISTRIBUTION' then '🔴 Распределение'
        when 'BREAKOUT_TRAP' then '🪤 Ложный пробой'
        when 'TREND_INITIATION' then '🚀 Запуск тренда'
        when 'INSTITUTIONAL_PARTICIPATION' then '🏦 Крупный участник'
        else '❔ Неизвестно'
    end as "🏦 Режим крупного потока",
    case bias
        when 'LONG_BIAS' then '🟢 Лонг-приоритет'
        when 'SHORT_BIAS' then '🔴 Шорт-приоритет'
        when 'MOMENTUM_BIAS' then '🚀 Импульс'
        when 'FADE_BIAS' then '🪤 Контрдвижение'
        when 'FOLLOW_FLOW' then '🏦 Следовать потоку'
        else '⚪ Нейтрально'
    end as "🧭 Смещение",
    round(confidence::numeric, 6) as "🎯 Уверенность",
    reason as "📝 Причина",
    ts as "🕒 Время"
from institutional_flow_regime_events
order by symbol, ts desc;
