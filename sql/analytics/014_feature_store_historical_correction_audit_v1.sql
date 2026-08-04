BEGIN;

CREATE SCHEMA IF NOT EXISTS analytics;

CREATE TABLE IF NOT EXISTS
    analytics.feature_store_historical_correction_audit_v1 (
        audit_id uuid PRIMARY KEY,
        audit_run_id uuid NOT NULL,
        symbol text NOT NULL,
        timeframe text NOT NULL,

        checked_rows integer NOT NULL
            CHECK (checked_rows >= 0),

        changed_rows integer NOT NULL
            CHECK (changed_rows >= 0),

        missing_market_snapshot_rows integer NOT NULL
            CHECK (missing_market_snapshot_rows >= 0),

        missing_market_bar_rows integer NOT NULL
            CHECK (missing_market_bar_rows >= 0),

        first_changed_ts timestamptz,
        last_changed_ts timestamptz,

        correction_detected boolean NOT NULL,
        dry_run boolean NOT NULL,

        source_version text NOT NULL,
        created_at timestamptz NOT NULL
            DEFAULT clock_timestamp(),

        CONSTRAINT
            feature_store_historical_correction_changed_range_v1
        CHECK (
            first_changed_ts IS NULL
            OR last_changed_ts IS NULL
            OR first_changed_ts <= last_changed_ts
        ),

        CONSTRAINT
            feature_store_historical_correction_detection_v1
        CHECK (
            correction_detected
            OR (
                changed_rows = 0
                AND missing_market_bar_rows = 0
            )
        )
    );

CREATE INDEX IF NOT EXISTS
    ix_feature_store_historical_correction_audit_run_v1
ON analytics.feature_store_historical_correction_audit_v1 (
    audit_run_id,
    correction_detected,
    symbol,
    timeframe
);

CREATE INDEX IF NOT EXISTS
    ix_feature_store_historical_correction_audit_pair_v1
ON analytics.feature_store_historical_correction_audit_v1 (
    symbol,
    timeframe,
    created_at DESC
);

CREATE INDEX IF NOT EXISTS
    ix_feature_store_historical_correction_detected_v1
ON analytics.feature_store_historical_correction_audit_v1 (
    created_at DESC,
    symbol,
    timeframe
)
WHERE correction_detected;

COMMENT ON TABLE
    analytics.feature_store_historical_correction_audit_v1
IS
    'Аудит поздних изменений OHLCV между public.market_bars и marketcore.market_snapshot_v1.';

COMMENT ON COLUMN
    analytics.feature_store_historical_correction_audit_v1.audit_run_id
IS
    'Идентификатор одного запуска исторического аудита.';

COMMENT ON COLUMN
    analytics.feature_store_historical_correction_audit_v1.correction_detected
IS
    'Признак обнаруженного расхождения выше установленного допуска.';

COMMENT ON COLUMN
    analytics.feature_store_historical_correction_audit_v1.dry_run
IS
    'Признак запуска без изменения dirty-state.';

COMMIT;
