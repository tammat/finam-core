CREATE TABLE IF NOT EXISTS analytics.profit_factory_runtime_handoff_v1 (
    handoff_id UUID PRIMARY KEY,
    candidate_id UUID NOT NULL REFERENCES analytics.profit_factory_candidate_identity_v1(candidate_id),
    paper_entity_id TEXT NOT NULL,
    runtime_strategy_code TEXT NOT NULL,
    runtime_symbol TEXT NOT NULL,
    runtime_timeframe TEXT NOT NULL,
    handoff_status TEXT NOT NULL,
    data_scope TEXT NOT NULL,
    source_version TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT ck_profit_factory_runtime_handoff_status_v1
        CHECK (handoff_status IN ('PENDING', 'ACCEPTED', 'REJECTED', 'STOPPED')),
    CONSTRAINT ck_profit_factory_runtime_handoff_scope_v1
        CHECK (data_scope IN ('REAL', 'TEST'))
);

CREATE TABLE IF NOT EXISTS analytics.profit_factory_production_allocation_v1 (
    allocation_id UUID PRIMARY KEY,
    candidate_id UUID NOT NULL REFERENCES analytics.profit_factory_candidate_identity_v1(candidate_id),
    handoff_id UUID NOT NULL REFERENCES analytics.profit_factory_runtime_handoff_v1(handoff_id),
    allocation_status TEXT NOT NULL,
    capital_allocated NUMERIC(20,6) NOT NULL,
    currency_code TEXT NOT NULL,
    data_scope TEXT NOT NULL,
    source_version TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT ck_profit_factory_production_allocation_status_v1
        CHECK (allocation_status IN ('PENDING', 'ACTIVE', 'CLOSED', 'REJECTED')),
    CONSTRAINT ck_profit_factory_production_allocation_capital_v1
        CHECK (capital_allocated >= 0),
    CONSTRAINT ck_profit_factory_production_allocation_scope_v1
        CHECK (data_scope IN ('REAL', 'TEST'))
);

CREATE TABLE IF NOT EXISTS analytics.profit_factory_profit_fact_v1 (
    profit_fact_id UUID PRIMARY KEY,
    candidate_id UUID NOT NULL REFERENCES analytics.profit_factory_candidate_identity_v1(candidate_id),
    allocation_id UUID NOT NULL REFERENCES analytics.profit_factory_production_allocation_v1(allocation_id),
    expected_profit NUMERIC(20,6) NOT NULL,
    realized_profit NUMERIC(20,6) NOT NULL,
    currency_code TEXT NOT NULL,
    measurement_from TIMESTAMPTZ NOT NULL,
    measurement_to TIMESTAMPTZ NOT NULL,
    data_scope TEXT NOT NULL,
    source_version TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT ck_profit_factory_profit_fact_period_v1
        CHECK (measurement_to >= measurement_from),
    CONSTRAINT ck_profit_factory_profit_fact_scope_v1
        CHECK (data_scope IN ('REAL', 'TEST'))
);

INSERT INTO analytics.profit_factory_candidate_identity_v1 (
    candidate_id, edge_candidate_id, observation_id, research_batch_id,
    research_code, strategy_code, strategy_version, symbol, timeframe,
    parameter_hash, dataset_version, data_scope, source_table,
    source_version, source_created_at
) VALUES (
    '11111111-1111-4111-8111-111111111111', -1001,
    '22222222-2222-4222-8222-222222222222', 'TEST_E2E_V1',
    'TEST:E2E:PROFIT_FACTORY_V1', 'TEST_PROFIT_STRATEGY_V1', 'v1',
    'TEST@MARKET', 'M5', 'TEST_PARAMETER_HASH_V1', 'TEST_DATASET_V1',
    'TEST', 'test.profit_factory_e2e_v1', 'PROFIT_FACTORY_E2E_TEST_CHAIN_V1', now()
) ON CONFLICT (candidate_id) DO NOTHING;

INSERT INTO analytics.profit_factory_runtime_handoff_v1 (
    handoff_id, candidate_id, paper_entity_id, runtime_strategy_code,
    runtime_symbol, runtime_timeframe, handoff_status, data_scope, source_version
) VALUES (
    '33333333-3333-4333-8333-333333333333',
    '11111111-1111-4111-8111-111111111111', 'TEST-PAPER-001',
    'TEST_PROFIT_STRATEGY_V1', 'TEST@MARKET', 'M5', 'ACCEPTED', 'TEST',
    'PROFIT_FACTORY_E2E_TEST_CHAIN_V1'
) ON CONFLICT (handoff_id) DO NOTHING;

INSERT INTO analytics.profit_factory_production_allocation_v1 (
    allocation_id, candidate_id, handoff_id, allocation_status,
    capital_allocated, currency_code, data_scope, source_version
) VALUES (
    '44444444-4444-4444-8444-444444444444',
    '11111111-1111-4111-8111-111111111111',
    '33333333-3333-4333-8333-333333333333', 'ACTIVE',
    100000, 'RUB', 'TEST', 'PROFIT_FACTORY_E2E_TEST_CHAIN_V1'
) ON CONFLICT (allocation_id) DO NOTHING;

INSERT INTO analytics.profit_factory_profit_fact_v1 (
    profit_fact_id, candidate_id, allocation_id, expected_profit,
    realized_profit, currency_code, measurement_from, measurement_to,
    data_scope, source_version
) VALUES (
    '55555555-5555-4555-8555-555555555555',
    '11111111-1111-4111-8111-111111111111',
    '44444444-4444-4444-8444-444444444444',
    12500, 8700, 'RUB', now() - interval '30 days', now(),
    'TEST', 'PROFIT_FACTORY_E2E_TEST_CHAIN_V1'
) ON CONFLICT (profit_fact_id) DO NOTHING;

GRANT SELECT, INSERT, UPDATE ON analytics.profit_factory_runtime_handoff_v1 TO alex;
GRANT SELECT, INSERT, UPDATE ON analytics.profit_factory_production_allocation_v1 TO alex;
GRANT SELECT, INSERT, UPDATE ON analytics.profit_factory_profit_fact_v1 TO alex;
