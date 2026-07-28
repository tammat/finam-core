BEGIN;

CREATE SCHEMA IF NOT EXISTS analytics;

CREATE TABLE IF NOT EXISTS analytics.runtime_strategy_policy_v2 (
    symbol text NOT NULL,
    timeframe text NOT NULL,
    regime_family text NOT NULL CHECK (regime_family IN ('RANGE', 'TREND')),
    strategy_code text NOT NULL,
    generator_code text NOT NULL,
    enabled boolean NOT NULL DEFAULT true,
    priority integer NOT NULL DEFAULT 50,
    assignment_reason text NOT NULL,
    updated_at timestamptz NOT NULL DEFAULT clock_timestamp(),
    PRIMARY KEY (symbol, timeframe, regime_family)
);

COMMENT ON TABLE analytics.runtime_strategy_policy_v2 IS
'DB-политика маршрутизации: боковик — возврат к среднему, подтверждённый тренд — пробой волатильности.';

INSERT INTO analytics.runtime_strategy_policy_v2(
    symbol,timeframe,regime_family,strategy_code,generator_code,priority,assignment_reason
)
SELECT u.symbol,coalesce(nullif(u.timeframe,''),'M5'),r.regime_family,
       r.strategy_code,r.generator_code,coalesce(u.priority,50),
       'Режимная политика активной исследовательской вселенной'
FROM runtime_active_universe u
CROSS JOIN (VALUES
 ('RANGE','MEAN_REVERSION_EQUITY','EQUITY_MEAN_REVERSION_GENERATOR_V1'),
 ('TREND','VOLATILITY_BREAKOUT_EQUITY','EQUITY_VOLATILITY_BREAKOUT_GENERATOR_V1')
) r(regime_family,strategy_code,generator_code)
WHERE u.symbol LIKE '%@MISX'
ON CONFLICT(symbol,timeframe,regime_family) DO NOTHING;

-- Существующие специализированные фьючерсные генераторы сохраняют собственную
-- стратегию в обоих семействах режима. Это не подмена модели: режим по-прежнему
-- обязан быть определён, но маршрутизация остаётся в выделенном генераторе.
INSERT INTO analytics.runtime_strategy_policy_v2(
    symbol,timeframe,regime_family,strategy_code,generator_code,priority,assignment_reason
)
SELECT u.symbol,coalesce(nullif(u.timeframe,''),'M5'),r.regime_family,
       u.strategy,'DEDICATED_FUTURES_GENERATOR_V1',coalesce(u.priority,50),
       'Политика существующего специализированного фьючерсного генератора'
FROM runtime_active_universe u
CROSS JOIN (VALUES ('RANGE'),('TREND')) r(regime_family)
WHERE u.symbol NOT LIKE '%@MISX'
  AND coalesce(u.strategy,'') NOT IN ('','UNKNOWN','UNASSIGNED','DEFAULT')
ON CONFLICT(symbol,timeframe,regime_family) DO NOTHING;

CREATE OR REPLACE FUNCTION analytics.activate_instrument_with_strategy_policy_v2(
    p_symbol text,p_timeframe text,p_asset_group text,
    p_range_strategy text,p_range_generator text,
    p_trend_strategy text,p_trend_generator text,
    p_priority integer DEFAULT 50,p_score double precision DEFAULT 0.0,
    p_reason text DEFAULT 'Атомарное включение инструмента'
) RETURNS void LANGUAGE plpgsql AS $$
BEGIN
    IF coalesce(p_range_strategy,'')='' OR coalesce(p_trend_strategy,'')='' THEN
        RAISE EXCEPTION 'ACTIVE_UNIVERSE_POLICY_REQUIRED:%:%',p_symbol,p_timeframe;
    END IF;
    INSERT INTO analytics.runtime_strategy_policy_v2(
      symbol,timeframe,regime_family,strategy_code,generator_code,priority,assignment_reason
    ) VALUES
      (p_symbol,p_timeframe,'RANGE',p_range_strategy,p_range_generator,p_priority,p_reason),
      (p_symbol,p_timeframe,'TREND',p_trend_strategy,p_trend_generator,p_priority,p_reason)
    ON CONFLICT(symbol,timeframe,regime_family) DO UPDATE SET
      strategy_code=excluded.strategy_code,generator_code=excluded.generator_code,
      enabled=true,priority=excluded.priority,assignment_reason=excluded.assignment_reason,
      updated_at=clock_timestamp();

    INSERT INTO runtime_active_universe(
      symbol,timeframe,strategy,regime,score,priority,is_enabled,source,raw_json,updated_at
    ) VALUES(
      p_symbol,p_timeframe,p_range_strategy,'WAITING_CONFIRMED_REGIME',p_score,p_priority,true,
      'atomic_strategy_policy_v2',jsonb_build_object('asset_group',p_asset_group,'reason',p_reason),clock_timestamp()
    ) ON CONFLICT(symbol) DO UPDATE SET
      timeframe=excluded.timeframe,strategy=excluded.strategy,regime=excluded.regime,
      score=excluded.score,priority=excluded.priority,is_enabled=true,disabled_at=null,
      disable_reason=null,source=excluded.source,raw_json=excluded.raw_json,
      updated_at=clock_timestamp();
END; $$;

CREATE OR REPLACE FUNCTION analytics.enforce_active_universe_policy_v2()
RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
  IF NEW.is_enabled AND NOT EXISTS(
    SELECT 1 FROM analytics.runtime_strategy_policy_v2 p
    WHERE p.symbol=NEW.symbol AND p.enabled
      AND p.timeframe IN(coalesce(nullif(NEW.timeframe,''),'M5'),'ANY')
  ) THEN
    RAISE EXCEPTION 'ACTIVE_UNIVERSE_WITHOUT_STRATEGY_POLICY:%:%',NEW.symbol,NEW.timeframe;
  END IF;
  RETURN NEW;
END; $$;

DROP TRIGGER IF EXISTS trg_active_universe_requires_strategy_policy_v2 ON runtime_active_universe;
CREATE TRIGGER trg_active_universe_requires_strategy_policy_v2
BEFORE INSERT OR UPDATE OF is_enabled,strategy,timeframe ON runtime_active_universe
FOR EACH ROW EXECUTE FUNCTION analytics.enforce_active_universe_policy_v2();

CREATE OR REPLACE VIEW analytics.closed_trades_fresh_v4_assigned AS
SELECT * FROM analytics.closed_trades_fresh_v4_regime
WHERE upper(coalesce(strategy,'')) NOT IN('','UNKNOWN','UNASSIGNED','DEFAULT');

COMMENT ON VIEW analytics.closed_trades_fresh_v4_assigned IS
'Чистая V4-когорта; UNASSIGNED сохранены в closed_trades только для аудита и исключены из OOS.';

GRANT SELECT ON analytics.runtime_strategy_policy_v2 TO alex,finam;
GRANT SELECT ON analytics.closed_trades_fresh_v4_assigned TO alex,finam;
GRANT EXECUTE ON FUNCTION analytics.activate_instrument_with_strategy_policy_v2(
 text,text,text,text,text,text,text,integer,double precision,text
) TO alex,finam;

COMMIT;
