BEGIN;

ALTER TABLE analytics.runtime_strategy_assignment_v1
    ADD COLUMN IF NOT EXISTS v4_paper_enabled boolean NOT NULL DEFAULT true,
    ADD COLUMN IF NOT EXISTS min_orderbook_coverage numeric NOT NULL DEFAULT 0
        CHECK (min_orderbook_coverage BETWEEN 0 AND 1),
    ADD COLUMN IF NOT EXISTS cost_source text NOT NULL DEFAULT 'LEGACY_ASSIGNMENT';

CREATE TABLE IF NOT EXISTS analytics.futures_symbol_alias_v1 (
    canonical_symbol text PRIMARY KEY,
    execution_symbol text NOT NULL,
    feed_symbol text NOT NULL,
    root_symbol text NOT NULL,
    enabled boolean NOT NULL DEFAULT true,
    reason text NOT NULL,
    updated_at timestamptz NOT NULL DEFAULT clock_timestamp()
);

INSERT INTO analytics.futures_symbol_alias_v1
    (canonical_symbol, execution_symbol, feed_symbol, root_symbol, reason)
VALUES
    ('NG_CONT', 'NGQ6@RTSX', 'NGQ6@RTSX', 'NG', 'Активный контракт газа'),
    ('CNYRUB_CONT', 'CNYRUBF@RTSX', 'CNYRUBF@RTSX', 'CNYRUB', 'Вечный фьючерс юань/рубль'),
    ('USDRUB_CONT', 'USDRUBF@RTSX', 'USDRUBF@RTSX', 'USDRUB', 'Вечный фьючерс доллар/рубль'),
    ('GOLD_CONT', 'GDU6@RTSX', 'GDU6@RTSX', 'GOLD', 'GLDRUBF — канон, GDU6 — биржевой контракт'),
    ('GLDRUBF@RTSX', 'GDU6@RTSX', 'GDU6@RTSX', 'GOLD', 'Нормализация логического имени золота')
ON CONFLICT (canonical_symbol) DO UPDATE SET
    execution_symbol=EXCLUDED.execution_symbol,
    feed_symbol=EXCLUDED.feed_symbol,
    root_symbol=EXCLUDED.root_symbol,
    enabled=true,
    reason=EXCLUDED.reason,
    updated_at=clock_timestamp();

INSERT INTO analytics.runtime_strategy_assignment_v1 (
    symbol,timeframe,asset_group,strategy_code,generator_code,enabled,priority,
    countertrend_long_allowed,countertrend_short_allowed,
    commission_bps,spread_bps,slippage_bps,min_edge_buffer_bps,
    v4_paper_enabled,min_orderbook_coverage,cost_source,assignment_reason
)
VALUES
    ('NGQ6@RTSX','M1','FUTURES','NG_CONSERVATIVE_BREAKOUT_M1','NG_FUTURES_GENERATOR_V1',true,100,false,false,
      3,5.682,5,5,false,0.80,'REAL_BOOK_7D_20260722','Газ переключён на NGQ6; admission после свежего стакана'),
    ('CNYRUBF@RTSX','M5','FUTURES','CNY_REGIME_FUTURES','CNY_REGIME_GENERATOR_V1',true,90,false,false,
      3,1.414,3,4,false,0.80,'REAL_BOOK_7D_20260722','Отдельная валютная режимная модель юаня'),
    ('USDRUBF@RTSX','M5','FUTURES','USD_REGIME_FUTURES','USD_REGIME_GENERATOR_V1',true,85,false,false,
      3,1.826,3,4,false,0.80,'REAL_BOOK_7D_20260722','Отдельная валютная режимная модель доллара'),
    ('GDU6@RTSX','M5','FUTURES','GOLD_TREND_BREAKOUT','GOLD_TREND_BREAKOUT_GENERATOR_V1',true,80,false,false,
      3,4,5,6,false,0.80,'CONSERVATIVE_UNTIL_REAL_BOOK','Трендово-пробойная модель золота; ждёт реальный стакан')
ON CONFLICT (symbol,timeframe) DO UPDATE SET
    asset_group=EXCLUDED.asset_group,
    strategy_code=EXCLUDED.strategy_code,
    generator_code=EXCLUDED.generator_code,
    enabled=EXCLUDED.enabled,
    priority=EXCLUDED.priority,
    countertrend_long_allowed=EXCLUDED.countertrend_long_allowed,
    countertrend_short_allowed=EXCLUDED.countertrend_short_allowed,
    commission_bps=EXCLUDED.commission_bps,
    spread_bps=EXCLUDED.spread_bps,
    slippage_bps=EXCLUDED.slippage_bps,
    min_edge_buffer_bps=EXCLUDED.min_edge_buffer_bps,
    v4_paper_enabled=EXCLUDED.v4_paper_enabled,
    min_orderbook_coverage=EXCLUDED.min_orderbook_coverage,
    cost_source=EXCLUDED.cost_source,
    assignment_reason=EXCLUDED.assignment_reason,
    updated_at=clock_timestamp();

-- Старый газовый контракт не должен оставаться исполнимым назначением.
UPDATE analytics.runtime_strategy_assignment_v1
SET enabled=false, v4_paper_enabled=false,
    assignment_reason='STALE_GAS_CONTRACT_REPLACED_BY_NGQ6', updated_at=clock_timestamp()
WHERE symbol LIKE 'NG%' AND symbol <> 'NGQ6@RTSX';

CREATE OR REPLACE VIEW analytics.v4_futures_admission_readiness_v1 AS
SELECT a.symbol,a.timeframe,a.strategy_code,a.generator_code,
       (s.symbol IS NOT NULL) AS contract_ready,
       coalesce(q.market_data_quality,'NO_BOOK') AS book_quality,
       coalesce(q.latest_age_seconds,1e12) AS book_age_seconds,
       coalesce(q.snapshots,0) AS snapshots,
       a.min_orderbook_coverage,
       a.v4_paper_enabled,
       CASE
         WHEN s.symbol IS NULL THEN 'NO_CONTRACT_SPEC'
         WHEN q.symbol IS NULL THEN 'NO_REAL_ORDERBOOK'
         WHEN q.latest_age_seconds > 120 THEN 'ORDERBOOK_STALE'
         WHEN q.market_data_quality <> 'READY' THEN 'ORDERBOOK_NOT_READY'
         WHEN NOT a.v4_paper_enabled THEN 'AWAITING_AUDITED_ADMISSION'
         ELSE 'READY'
       END AS reason_code
FROM analytics.runtime_strategy_assignment_v1 a
LEFT JOIN analytics.market_contract_spec_v1 s
  ON s.symbol=a.symbol AND s.is_active
LEFT JOIN analytics.market_microstructure_quality_v1 q
  ON q.symbol=a.symbol
WHERE a.asset_group='FUTURES' AND a.enabled;

GRANT SELECT ON analytics.futures_symbol_alias_v1,
    analytics.v4_futures_admission_readiness_v1 TO finam;
GRANT SELECT,INSERT,UPDATE ON analytics.runtime_strategy_assignment_v1 TO finam;

COMMIT;
