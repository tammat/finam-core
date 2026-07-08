CREATE TABLE IF NOT EXISTS knowledge.trading_plan_source_v1
(
    source_code           TEXT PRIMARY KEY,

    source_name           TEXT NOT NULL,

    source_group          TEXT NOT NULL,

    knowledge_table       TEXT NOT NULL,

    knowledge_field       TEXT NOT NULL,

    enabled               BOOLEAN NOT NULL DEFAULT TRUE,

    source_version        TEXT NOT NULL,

    created_at            TIMESTAMPTZ NOT NULL DEFAULT now(),

    updated_at            TIMESTAMPTZ NOT NULL DEFAULT now()
);

INSERT INTO knowledge.trading_plan_source_v1
(
    source_code,
    source_name,
    source_group,
    knowledge_table,
    knowledge_field,
    enabled,
    source_version
)
VALUES

('LAST_CLOSE',
 'Last Close',
 'PRICE',
 'public.market_bars',
 'close',
 TRUE,
 'TRADING_PLAN_SOURCE_REGISTRY_V1'),

('BREAKOUT_LEVEL',
 'Breakout Level',
 'MARKET_STRUCTURE',
 'knowledge.market_structure_v1',
 'level_price',
 TRUE,
 'TRADING_PLAN_SOURCE_REGISTRY_V1'),

('SUPPORT',
 'Support',
 'MARKET_STRUCTURE',
 'knowledge.market_structure_v1',
 'level_price',
 TRUE,
 'TRADING_PLAN_SOURCE_REGISTRY_V1'),

('RESISTANCE',
 'Resistance',
 'MARKET_STRUCTURE',
 'knowledge.market_structure_v1',
 'level_price',
 TRUE,
 'TRADING_PLAN_SOURCE_REGISTRY_V1'),

('SWING_HIGH',
 'Swing High',
 'MARKET_STRUCTURE',
 'knowledge.market_structure_v1',
 'level_price',
 TRUE,
 'TRADING_PLAN_SOURCE_REGISTRY_V1'),

('SWING_LOW',
 'Swing Low',
 'MARKET_STRUCTURE',
 'knowledge.market_structure_v1',
 'level_price',
 TRUE,
 'TRADING_PLAN_SOURCE_REGISTRY_V1'),

('FIBONACCI_RETRACEMENT',
 'Fibonacci Retracement',
 'MARKET_STRUCTURE',
 'knowledge.market_structure_v1',
 'level_price',
 TRUE,
 'TRADING_PLAN_SOURCE_REGISTRY_V1'),

('FIBONACCI_EXTENSION',
 'Fibonacci Extension',
 'MARKET_STRUCTURE',
 'knowledge.market_structure_v1',
 'level_price',
 TRUE,
 'TRADING_PLAN_SOURCE_REGISTRY_V1'),

('PIVOT_LEVEL',
 'Pivot',
 'MARKET_STRUCTURE',
 'knowledge.market_structure_v1',
 'level_price',
 TRUE,
 'TRADING_PLAN_SOURCE_REGISTRY_V1'),

('CHANNEL_UPPER',
 'Channel Upper',
 'MARKET_STRUCTURE',
 'knowledge.market_structure_v1',
 'level_price',
 TRUE,
 'TRADING_PLAN_SOURCE_REGISTRY_V1'),

('CHANNEL_LOWER',
 'Channel Lower',
 'MARKET_STRUCTURE',
 'knowledge.market_structure_v1',
 'level_price',
 TRUE,
 'TRADING_PLAN_SOURCE_REGISTRY_V1'),

('VWAP',
 'VWAP',
 'VOLUME',
 'knowledge.market_structure_v1',
 'level_price',
 TRUE,
 'TRADING_PLAN_SOURCE_REGISTRY_V1'),

('ATR',
 'ATR',
 'VOLATILITY',
 'knowledge.market_structure_v1',
 'level_price',
 TRUE,
 'TRADING_PLAN_SOURCE_REGISTRY_V1')

ON CONFLICT(source_code)
DO UPDATE SET

source_name      = EXCLUDED.source_name,
source_group     = EXCLUDED.source_group,
knowledge_table  = EXCLUDED.knowledge_table,
knowledge_field  = EXCLUDED.knowledge_field,
enabled          = EXCLUDED.enabled,
updated_at       = now(),
source_version   = EXCLUDED.source_version;
