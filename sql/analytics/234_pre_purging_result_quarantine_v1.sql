BEGIN;

CREATE TABLE IF NOT EXISTS analytics.pre_purging_result_quarantine_v1(
    source_table text PRIMARY KEY,
    cutoff_ts timestamptz NOT NULL,
    total_rows bigint NOT NULL DEFAULT 0,
    affected_rows bigint NOT NULL,
    policy_code text NOT NULL DEFAULT 'LEGACY_PRE_PURGING',
    promotion_blocked boolean NOT NULL DEFAULT true,
    quarantined_at timestamptz NOT NULL DEFAULT clock_timestamp()
);
ALTER TABLE analytics.pre_purging_result_quarantine_v1
ADD COLUMN IF NOT EXISTS total_rows bigint NOT NULL DEFAULT 0;

DO $$
DECLARE
    item text;
    affected bigint;
    total bigint;
    cutoff constant timestamptz := '2026-07-30 07:44:55+03'::timestamptz;
BEGIN
    FOREACH item IN ARRAY ARRAY[
      'walkforward_edge_search_v3','strategy_hypothesis_execution_result_v2',
      'edge_hypothesis_result_v1','edge_regime_hypothesis_result_v2',
      'relationship_factory_result_v2','intermarket_lead_lag_result_v1',
      'edge_session_result_v1','execution_edge_result_v1','edge_oos_result_v1',
      'swing_selection_validation_result_v1'
    ] LOOP
      IF to_regclass('analytics.'||item) IS NULL THEN CONTINUE; END IF;
      EXECUTE format('SELECT count(*) FROM analytics.%I WHERE created_at < $1',item) INTO total USING cutoff;
      EXECUTE format('UPDATE analytics.%I SET promotion_allowed=false WHERE created_at < $1 AND promotion_allowed',item) USING cutoff;
      GET DIAGNOSTICS affected = ROW_COUNT;
      INSERT INTO analytics.pre_purging_result_quarantine_v1(source_table,cutoff_ts,total_rows,affected_rows)
      VALUES(item,cutoff,total,affected)
      ON CONFLICT(source_table) DO UPDATE SET cutoff_ts=excluded.cutoff_ts,
        total_rows=excluded.total_rows,
        affected_rows=analytics.pre_purging_result_quarantine_v1.affected_rows+excluded.affected_rows,
        promotion_blocked=true,quarantined_at=clock_timestamp();
    END LOOP;
    IF to_regclass('analytics.swing_selection_validation_result_v1') IS NOT NULL THEN
      UPDATE analytics.swing_selection_validation_result_v1
      SET final_oos_opened=false WHERE created_at<cutoff AND final_oos_opened;
    END IF;
END $$;

COMMENT ON TABLE analytics.pre_purging_result_quarantine_v1 IS
'Аудит результатов, рассчитанных до обязательных purging/embargo; продвижение навсегда заблокировано.';
GRANT SELECT ON analytics.pre_purging_result_quarantine_v1 TO alex,finam;

COMMIT;
