BEGIN;

ALTER TABLE analytics.v5_oos_observation_audit_v1
  DROP CONSTRAINT IF EXISTS v5_oos_observation_audit_v1_run_id_source_trade_id_key,
  DROP CONSTRAINT IF EXISTS v5_oos_observation_audit_v1_source_trade_id_fkey;
ALTER TABLE analytics.v5_oos_observation_audit_v1
  ALTER COLUMN source_trade_id DROP NOT NULL,
  ADD COLUMN IF NOT EXISTS source_kind text,
  ADD COLUMN IF NOT EXISTS source_signal_id bigint;

UPDATE analytics.v5_oos_observation_audit_v1
SET source_kind='PAPER_TRADE'
WHERE source_kind IS NULL;

ALTER TABLE analytics.v5_oos_observation_audit_v1
  ALTER COLUMN source_kind SET NOT NULL,
  ADD CONSTRAINT v5_oos_audit_source_kind_check
    CHECK(source_kind IN ('PAPER_TRADE','SHADOW_SIGNAL')),
  ADD CONSTRAINT v5_oos_audit_exactly_one_source_check CHECK(
    (source_kind='PAPER_TRADE' AND source_trade_id IS NOT NULL AND source_signal_id IS NULL)
    OR (source_kind='SHADOW_SIGNAL' AND source_trade_id IS NULL AND source_signal_id IS NOT NULL)
  ),
  ADD CONSTRAINT v5_oos_audit_source_trade_fkey
    FOREIGN KEY(source_trade_id) REFERENCES public.closed_trades(id),
  ADD CONSTRAINT v5_oos_audit_source_signal_fkey
    FOREIGN KEY(source_signal_id) REFERENCES public.signals(id);

DROP INDEX IF EXISTS analytics.v5_oos_included_trade_once_idx;
CREATE UNIQUE INDEX IF NOT EXISTS v5_oos_audit_run_trade_once_idx
  ON analytics.v5_oos_observation_audit_v1(run_id,source_trade_id)
  WHERE source_kind='PAPER_TRADE';
CREATE UNIQUE INDEX IF NOT EXISTS v5_oos_audit_run_signal_once_idx
  ON analytics.v5_oos_observation_audit_v1(run_id,source_signal_id)
  WHERE source_kind='SHADOW_SIGNAL';
CREATE UNIQUE INDEX IF NOT EXISTS v5_oos_included_trade_once_idx
  ON analytics.v5_oos_observation_audit_v1(source_trade_id)
  WHERE source_kind='PAPER_TRADE' AND decision_code='INCLUDED';
CREATE UNIQUE INDEX IF NOT EXISTS v5_oos_included_signal_once_idx
  ON analytics.v5_oos_observation_audit_v1(source_signal_id)
  WHERE source_kind='SHADOW_SIGNAL' AND decision_code='INCLUDED';

CREATE TABLE IF NOT EXISTS analytics.v5_program_lock_v1(
  lock_code text PRIMARY KEY,
  enabled boolean NOT NULL,
  methodology_epoch text NOT NULL,
  reason text NOT NULL,
  updated_at timestamptz NOT NULL DEFAULT clock_timestamp()
);
INSERT INTO analytics.v5_program_lock_v1(lock_code,enabled,methodology_epoch,reason)
VALUES('CURRENT_V5_FOUR_BRANCHES_ONLY',true,'POST_FIX_V1',
       'До PASS/FAIL текущих четырёх веток новые V5-когорты запрещены')
ON CONFLICT(lock_code) DO UPDATE SET enabled=true,reason=excluded.reason,updated_at=clock_timestamp();

UPDATE analytics.trade_outcome_oos_admission_v1 a
SET status_code='RUNNING',reason_code='WAITING_FUTURE_OBSERVATIONS',
    oos_request=jsonb_set(a.oos_request,'{phase}','"DIRECT_V5_POST_FIX_V1"'::jsonb,true),
    updated_at=clock_timestamp()
FROM analytics.v5_post_fix_branch_registry_v1 r
WHERE r.admission_id=a.admission_id AND a.status_code='CLOSED'
  AND a.reason_code='PROSPECTIVE_SHADOW_GATE_PENDING';

UPDATE analytics.v5_oos_run_v1 v
SET status_code='COLLECTING',reason_code='WAITING_FUTURE_OBSERVATIONS',updated_at=clock_timestamp()
FROM analytics.v5_post_fix_branch_registry_v1 r
WHERE r.admission_id=v.admission_id AND v.observations_included=0
  AND v.reason_code='SUPERSEDED_BY_PROSPECTIVE_SHADOW_GATE';

UPDATE analytics.v5_post_fix_branch_registry_v1
SET state_code='V5_COLLECTING'
WHERE state_code='PROSPECTIVE_ACCUMULATING';

GRANT SELECT ON analytics.v5_program_lock_v1 TO alex,finam;

COMMIT;
