create or replace view v_market_event_calendar_alerts_ru as
select
    event_time as "🕒 Время события",
    instrument_group as "📈 Группа инструментов",
    case event_type
        when 'CBR_RATE_DECISION' then '🏦 Заседание ЦБ'
        when 'EIA_INVENTORY' then '🛢 Запасы нефти EIA'
        when 'EIA_GAS_STORAGE' then '🔥 Запасы газа EIA'
        when 'API_INVENTORY' then '🛢 Запасы нефти API'
        else event_type
    end as "🚨 Событие",
    event_name as "📝 Описание",
    severity as "⚠️ Важность",
    round(extract(epoch from (event_time - now())) / 60.0)::int as "⏳ Минут до события",
    case
        when event_time < now() then '⚪ Событие прошло'
        when round(extract(epoch from (event_time - now())) / 60.0)::int <= pre_event_block_min
            then '⛔ BLOCK'
        when round(extract(epoch from (event_time - now())) / 60.0)::int <= pre_event_reduce_min
            then '⚠️ REDUCE'
        else '👁 WATCH'
    end as "🎛 Режим исполнения"
from market_event_calendar
where is_active = true
  and event_time >= now() - interval '2 hours'
  and event_time <= now() + interval '7 days'
order by event_time asc;
