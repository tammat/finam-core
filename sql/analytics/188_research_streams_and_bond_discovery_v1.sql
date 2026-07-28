BEGIN;

CREATE TABLE IF NOT EXISTS analytics.research_stream_v1 (
    stream_code text PRIMARY KEY,
    caption_ru text NOT NULL,
    allocation_share numeric(5,4) NOT NULL CHECK (allocation_share >= 0 AND allocation_share <= 1),
    state_code text NOT NULL,
    paper_enabled boolean NOT NULL DEFAULT false,
    real_trading_enabled boolean NOT NULL DEFAULT false,
    policy jsonb NOT NULL DEFAULT jsonb_build_object(),
    updated_at timestamptz NOT NULL DEFAULT clock_timestamp()
);

INSERT INTO analytics.research_stream_v1(
    stream_code, caption_ru, allocation_share, state_code, paper_enabled,
    real_trading_enabled, policy
) VALUES
    ('FRESH_V3_EQUITY', 'Акции', 0.50, 'READY_FOR_PAPER', true, false,
     jsonb_build_object('portfolio_scope', 'FRESH_V3_EQUITY', 'selection', 'DB_DRIVEN')),
    ('FRESH_V3_FUTURES', 'Фьючерсы', 0.35, 'READY_FOR_PAPER', true, false,
     jsonb_build_object(
        'portfolio_scope', 'FRESH_V3_FUTURES',
        'selection', 'DB_DRIVEN',
        'contract_types', jsonb_build_array('QUARTERLY', 'PERPETUAL', 'CONTINUOUS')
     )),
    ('FRESH_V3_BONDS', 'Облигации', 0.15, 'DATA_DISCOVERY', false, false,
     jsonb_build_object(
        'portfolio_scope', 'FRESH_V3_BONDS',
        'selection', 'DB_DRIVEN',
        'boards', jsonb_build_array('TQOB', 'TQCB'),
        'priority_order', jsonb_build_array('OFZ', 'CORPORATE_QUALITY'),
        'required_checks', jsonb_build_array(
            'SPECIFICATION', 'FRESHNESS', 'HISTORY', 'SPREAD', 'VOLUME',
            'ACCRUED_INTEREST', 'YIELD', 'DURATION', 'OFFER_AMORTIZATION', 'CREDIT_RISK'
        ),
        'activation_gate', 'DATA_AND_SPEC_READY'
     ))
ON CONFLICT(stream_code) DO UPDATE SET
    caption_ru = excluded.caption_ru,
    allocation_share = excluded.allocation_share,
    state_code = CASE
        WHEN analytics.research_stream_v1.stream_code = 'FRESH_V3_BONDS'
            AND analytics.research_stream_v1.state_code NOT IN ('READY_FOR_PAPER', 'ACTIVE')
        THEN 'DATA_DISCOVERY'
        ELSE analytics.research_stream_v1.state_code
    END,
    paper_enabled = CASE
        WHEN analytics.research_stream_v1.stream_code = 'FRESH_V3_BONDS'
        THEN analytics.research_stream_v1.paper_enabled
        ELSE excluded.paper_enabled
    END,
    real_trading_enabled = false,
    policy = excluded.policy,
    updated_at = clock_timestamp();

UPDATE analytics.instrument_scout_policy_v1
SET policy = jsonb_set(
        jsonb_set(
            jsonb_set(
                policy,
                '{category_order}',
                jsonb_build_array('OIL','GAS','METALS','FX','INDEX','EQUITY','BOND','OTHER'),
                true
            ),
            '{category_quotas,BOND}',
            '3'::jsonb,
            true
        ),
        '{bond_policy}',
        jsonb_build_object(
            'boards', jsonb_build_array('TQOB','TQCB'),
            'ofz_first', true,
            'min_bars', 5000,
            'freshness_hours', 72,
            'max_spread_bps', 35,
            'real_trading_enabled', false,
            'next_state', 'DATA_DISCOVERY'
        ),
        true
    )
WHERE policy_code = 'AUTONOMOUS_INSTRUMENT_SCOUT_V1';

INSERT INTO presentation.ui_resource_v1(
    resource_key, locale_code, caption, caption_short, caption_mobile,
    tooltip, resource_group, source_version
) VALUES
    ('research.stream.equity', 'ru', 'Акции', 'Акции', 'Акции',
     'Отдельный накопительный исследовательский поток акций', 'research', 'RESEARCH_STREAMS_V1'),
    ('research.stream.futures', 'ru', 'Фьючерсы', 'Фьючерсы', 'Фьючерсы',
     'Фьючерсы, вечные контракты и непрерывные серии', 'research', 'RESEARCH_STREAMS_V1'),
    ('research.stream.bonds', 'ru', 'Облигации', 'Облигации', 'Облиг.',
     'ОФЗ и качественные корпоративные облигации; пока идёт поиск данных', 'research', 'RESEARCH_STREAMS_V1'),
    ('research.stream.state.data_discovery', 'ru', 'Поиск данных', 'Данные', 'Данные',
     'Проверяются инструменты, спецификации, история и ликвидность', 'research', 'RESEARCH_STREAMS_V1')
ON CONFLICT(resource_key, locale_code) DO UPDATE SET
    caption = excluded.caption,
    caption_short = excluded.caption_short,
    caption_mobile = excluded.caption_mobile,
    tooltip = excluded.tooltip,
    source_version = excluded.source_version,
    updated_at = clock_timestamp();

GRANT SELECT ON analytics.research_stream_v1 TO alex;

COMMIT;
