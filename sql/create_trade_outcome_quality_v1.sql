drop view if exists trade_outcome_quality_v1;

create view trade_outcome_quality_v1 as
select
    o.id,
    o.symbol,
    o.continuous_symbol,
    o.strategy,
    o.timeframe,
    o.trade_source,
    o.net_pnl,
    o.holding_seconds,

    case
        when
            coalesce(o.strategy, '') <> ''
            and coalesce(o.timeframe, '') <> ''
            and coalesce(o.continuous_symbol, '') <> ''
            and coalesce(o.raw_json->>'outcome_engine_version', '') <> ''
            and coalesce(o.raw_json->'entry_payload'->>'continuous_symbol', '') <> ''
            and coalesce(o.raw_json->'entry_payload'->>'strategy', '') <> ''
            and coalesce(o.raw_json->'entry_payload'->>'regime', '') not in ('', 'unknown', 'UNKNOWN')
            then 'A'

        when
            coalesce(o.strategy, '') <> ''
            and coalesce(o.timeframe, '') <> ''
            and coalesce(o.continuous_symbol, '') <> ''
            then 'B'

        when
            coalesce(o.strategy, '') <> ''
            then 'C'

        else 'D'
    end as quality_grade,

    (
        case when coalesce(o.strategy, '') <> '' then 1 else 0 end +
        case when coalesce(o.timeframe, '') <> '' then 1 else 0 end +
        case when coalesce(o.continuous_symbol, '') <> '' then 1 else 0 end +
        case when coalesce(o.raw_json->>'outcome_engine_version', '') <> '' then 1 else 0 end +
        case when coalesce(o.raw_json->'entry_payload'->>'regime', '') not in ('', 'unknown', 'UNKNOWN') then 1 else 0 end +
        case when coalesce(o.raw_json->'entry_payload'->>'continuous_symbol', '') <> '' then 1 else 0 end
    ) as quality_score,

    case
        when coalesce(o.raw_json->'entry_payload'->>'regime', '') in ('', 'unknown', 'UNKNOWN')
            then false
        else true
    end as regime_known,

    case
        when coalesce(o.raw_json->'entry_payload'->>'continuous_symbol', '') <> ''
            then true
        else false
    end as continuous_symbol_known,

    case
        when coalesce(o.raw_json->>'outcome_engine_version', '') <> ''
            then true
        else false
    end as partition_isolated

from trade_outcomes o;
