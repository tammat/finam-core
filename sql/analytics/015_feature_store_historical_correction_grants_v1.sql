BEGIN;

ALTER TABLE
    analytics.feature_store_historical_correction_audit_v1
OWNER TO postgres;

ALTER TABLE
    analytics.feature_store_watermark_v1
OWNER TO postgres;

REVOKE ALL
ON TABLE analytics.feature_store_historical_correction_audit_v1
FROM alex;

REVOKE ALL
ON TABLE analytics.feature_store_watermark_v1
FROM alex;

REVOKE ALL
ON TABLE analytics.feature_store_historical_correction_audit_v1
FROM PUBLIC;

REVOKE ALL
ON TABLE analytics.feature_store_watermark_v1
FROM PUBLIC;

GRANT USAGE
ON SCHEMA analytics
TO finam;

GRANT SELECT, INSERT
ON TABLE analytics.feature_store_historical_correction_audit_v1
TO finam;

GRANT SELECT, UPDATE
ON TABLE analytics.feature_store_watermark_v1
TO finam;

GRANT USAGE
ON SCHEMA analytics
TO alex;

GRANT SELECT
ON TABLE analytics.feature_store_historical_correction_audit_v1
TO alex;

GRANT SELECT
ON TABLE analytics.feature_store_watermark_v1
TO alex;

COMMIT;
