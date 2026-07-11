CREATE SCHEMA IF NOT EXISTS analytics;

CREATE TABLE IF NOT EXISTS analytics.profit_factory_candidate_identity_v1 (
    candidate_id UUID PRIMARY KEY,
    edge_candidate_id BIGINT NOT NULL UNIQUE,
    observation_id UUID NOT NULL,
    research_batch_id TEXT NOT NULL,
    research_code TEXT NOT NULL,
    strategy_code TEXT NOT NULL,
    strategy_version TEXT NOT NULL,
    symbol TEXT NOT NULL,
    timeframe TEXT NOT NULL,
    parameter_hash TEXT NOT NULL,
    dataset_version TEXT NOT NULL,
    data_scope TEXT NOT NULL DEFAULT 'REAL',
    source_table TEXT NOT NULL DEFAULT 'analytics.edge_candidate_v1',
    source_version TEXT NOT NULL DEFAULT 'PROFIT_FACTORY_IDENTITY_CONTRACT_V1',
    source_created_at TIMESTAMPTZ NOT NULL,
    registered_at TIMESTAMPTZ NOT NULL DEFAULT now(),

    CONSTRAINT uq_profit_factory_candidate_identity_natural_v1 UNIQUE (
        strategy_code,
        strategy_version,
        symbol,
        timeframe,
        parameter_hash,
        dataset_version
    ),
    CONSTRAINT ck_profit_factory_identity_research_batch_v1
        CHECK (btrim(research_batch_id) <> ''),
    CONSTRAINT ck_profit_factory_identity_research_code_v1
        CHECK (btrim(research_code) <> ''),
    CONSTRAINT ck_profit_factory_identity_strategy_v1
        CHECK (btrim(strategy_code) <> '' AND btrim(strategy_version) <> ''),
    CONSTRAINT ck_profit_factory_identity_instrument_v1
        CHECK (btrim(symbol) <> '' AND btrim(timeframe) <> ''),
    CONSTRAINT ck_profit_factory_identity_parameter_v1
        CHECK (btrim(parameter_hash) <> ''),
    CONSTRAINT ck_profit_factory_identity_dataset_v1
        CHECK (btrim(dataset_version) <> ''),
    CONSTRAINT ck_profit_factory_identity_scope_v1
        CHECK (data_scope IN ('REAL', 'TEST'))
);

ALTER TABLE analytics.profit_factory_candidate_identity_v1
ADD COLUMN IF NOT EXISTS data_scope TEXT NOT NULL DEFAULT 'REAL';

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conname='ck_profit_factory_identity_scope_v1'
          AND conrelid='analytics.profit_factory_candidate_identity_v1'::regclass
    ) THEN
        ALTER TABLE analytics.profit_factory_candidate_identity_v1
        ADD CONSTRAINT ck_profit_factory_identity_scope_v1
        CHECK (data_scope IN ('REAL', 'TEST'));
    END IF;
END $$;

CREATE INDEX IF NOT EXISTS ix_profit_factory_identity_strategy_v1
ON analytics.profit_factory_candidate_identity_v1(strategy_code, symbol, timeframe);

CREATE INDEX IF NOT EXISTS ix_profit_factory_identity_research_batch_v1
ON analytics.profit_factory_candidate_identity_v1(research_batch_id);

INSERT INTO analytics.profit_factory_candidate_identity_v1 (
    candidate_id,
    edge_candidate_id,
    observation_id,
    research_batch_id,
    research_code,
    strategy_code,
    strategy_version,
    symbol,
    timeframe,
    parameter_hash,
    dataset_version,
    source_created_at
)
SELECT
    candidate_uuid,
    id,
    observation_uuid,
    research_batch_id,
    research_code,
    strategy_code,
    strategy_version,
    symbol,
    timeframe,
    parameter_hash,
    dataset_version,
    created_at
FROM analytics.edge_candidate_v1
WHERE candidate_uuid IS NOT NULL
  AND observation_uuid IS NOT NULL
  AND btrim(research_batch_id) <> ''
  AND btrim(research_code) <> ''
  AND btrim(strategy_code) <> ''
  AND btrim(strategy_version) <> ''
  AND btrim(symbol) <> ''
  AND btrim(timeframe) <> ''
  AND btrim(parameter_hash) <> ''
  AND btrim(dataset_version) <> ''
ON CONFLICT (candidate_id) DO NOTHING;

COMMENT ON TABLE analytics.profit_factory_candidate_identity_v1 IS
'Immutable canonical identity registry. candidate_id equals analytics.edge_candidate_v1.candidate_uuid.';

COMMENT ON COLUMN analytics.profit_factory_candidate_identity_v1.candidate_id IS
'Canonical Profit Factory candidate identifier copied exactly from edge_candidate_v1.candidate_uuid.';

GRANT USAGE ON SCHEMA analytics TO alex;
GRANT SELECT, INSERT ON analytics.profit_factory_candidate_identity_v1 TO alex;
