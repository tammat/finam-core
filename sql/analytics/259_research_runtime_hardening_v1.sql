BEGIN;

GRANT SELECT ON analytics.strategy_walkforward_latest_v1 TO finam;

CREATE TABLE IF NOT EXISTS analytics.adaptive_regime_paper_pilot_archive_v1
(LIKE analytics.adaptive_regime_paper_pilot_v1 INCLUDING DEFAULTS INCLUDING CONSTRAINTS);

ALTER TABLE analytics.adaptive_regime_paper_pilot_archive_v1
 ADD COLUMN IF NOT EXISTS archived_at timestamptz NOT NULL DEFAULT clock_timestamp();

CREATE UNIQUE INDEX IF NOT EXISTS adaptive_regime_pilot_archive_pkey_v1
 ON analytics.adaptive_regime_paper_pilot_archive_v1(pilot_id);

GRANT SELECT,INSERT ON analytics.adaptive_regime_paper_pilot_archive_v1 TO alex,finam;
GRANT DELETE ON analytics.adaptive_regime_paper_pilot_v1 TO finam;

COMMIT;
