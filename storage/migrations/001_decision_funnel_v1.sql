BEGIN;

CREATE SCHEMA IF NOT EXISTS analytics;

CREATE TABLE IF NOT EXISTS analytics.signal_decision_funnel_v1 (
    event_id uuid PRIMARY KEY,
    signal_id text NOT NULL,
    symbol text NOT NULL,
    strategy text NOT NULL,
    timeframe text NOT NULL,
    direction text,

    stage text NOT NULL CHECK (
        stage IN (
            'MARKET_DATA',
            'STRATEGY',
            'REGIME',
            'EDGE',
            'RISK',
            'PORTFOLIO',
            'RUNTIME',
            'EXECUTION',
            'BROKER',
            'FILL'
        )
    ),

    outcome text NOT NULL CHECK (
        outcome IN ('PASS', 'REJECT', 'ERROR', 'SKIP')
    ),

    reason_code text NOT NULL,
    attempt_no integer NOT NULL DEFAULT 1
        CHECK (attempt_no > 0),

    source text NOT NULL DEFAULT 'TRADING_ENGINE',
    context jsonb NOT NULL DEFAULT '{}'::jsonb,

    occurred_at timestamptz NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now(),

    UNIQUE (signal_id, stage, attempt_no),

    CHECK (
        outcome <> 'PASS'
        OR reason_code = 'PASSED'
    ),

    CHECK (
        outcome <> 'REJECT'
        OR reason_code <> 'PASSED'
    )
);

CREATE INDEX IF NOT EXISTS
    ix_signal_decision_funnel_v1_occurred_at
ON analytics.signal_decision_funnel_v1 (
    occurred_at DESC
);

CREATE INDEX IF NOT EXISTS
    ix_signal_decision_funnel_v1_signal
ON analytics.signal_decision_funnel_v1 (
    signal_id,
    occurred_at
);

CREATE INDEX IF NOT EXISTS
    ix_signal_decision_funnel_v1_stage_outcome
ON analytics.signal_decision_funnel_v1 (
    stage,
    outcome,
    reason_code,
    occurred_at DESC
);

CREATE INDEX IF NOT EXISTS
    ix_signal_decision_funnel_v1_symbol_strategy
ON analytics.signal_decision_funnel_v1 (
    symbol,
    strategy,
    occurred_at DESC
);

CREATE INDEX IF NOT EXISTS
    ix_signal_decision_funnel_v1_context_gin
ON analytics.signal_decision_funnel_v1
USING gin (context);

COMMENT ON TABLE analytics.signal_decision_funnel_v1 IS
    'Полная трассировка прохождения и отклонения торговых сигналов';

COMMENT ON COLUMN analytics.signal_decision_funnel_v1.signal_id IS
    'Стабильный идентификатор одного торгового намерения';

COMMENT ON COLUMN analytics.signal_decision_funnel_v1.reason_code IS
    'Нормализованная причина PASS, REJECT, ERROR или SKIP';

COMMENT ON COLUMN analytics.signal_decision_funnel_v1.context IS
    'Read-only диагностический контекст решения';

COMMIT;
