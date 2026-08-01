BEGIN;

CREATE TABLE IF NOT EXISTS analytics.v5_post_fix_branch_registry_v1 (
    branch_code text PRIMARY KEY,
    methodology_epoch text NOT NULL CHECK (methodology_epoch = 'POST_FIX_V1'),
    logical_symbol text NOT NULL,
    observation_symbol text NOT NULL,
    strategy_code text NOT NULL,
    side_code text NOT NULL CHECK (side_code IN ('LONG','SHORT')),
    timeframe text NOT NULL CHECK (timeframe = 'M5'),
    candidate_code text NOT NULL,
    entry_mode text NOT NULL,
    stop_atr numeric NOT NULL CHECK (stop_atr > 0),
    take_atr numeric NOT NULL CHECK (take_atr > 0),
    trail_after_r numeric,
    trail_atr numeric,
    minimum_observations integer NOT NULL DEFAULT 20 CHECK (minimum_observations >= 20),
    state_code text NOT NULL DEFAULT 'FROZEN_COLLECTING'
      CHECK (state_code IN ('FROZEN_COLLECTING','OOS_PASS','OOS_FAIL','RETIRED')),
    paper_allowed boolean NOT NULL DEFAULT false CHECK (paper_allowed = false),
    real_allowed boolean NOT NULL DEFAULT false CHECK (real_allowed = false),
    frozen_at timestamptz NOT NULL,
    admission_id uuid,
    metadata jsonb NOT NULL DEFAULT '{}'::jsonb,
    created_at timestamptz NOT NULL DEFAULT clock_timestamp()
);

CREATE OR REPLACE FUNCTION analytics.reject_frozen_branch_mutation_v1()
RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
  IF OLD.branch_code IS DISTINCT FROM NEW.branch_code
     OR OLD.logical_symbol IS DISTINCT FROM NEW.logical_symbol
     OR OLD.observation_symbol IS DISTINCT FROM NEW.observation_symbol
     OR OLD.strategy_code IS DISTINCT FROM NEW.strategy_code
     OR OLD.side_code IS DISTINCT FROM NEW.side_code
     OR OLD.timeframe IS DISTINCT FROM NEW.timeframe
     OR OLD.candidate_code IS DISTINCT FROM NEW.candidate_code
     OR OLD.entry_mode IS DISTINCT FROM NEW.entry_mode
     OR OLD.stop_atr IS DISTINCT FROM NEW.stop_atr
     OR OLD.take_atr IS DISTINCT FROM NEW.take_atr
     OR OLD.trail_after_r IS DISTINCT FROM NEW.trail_after_r
     OR OLD.trail_atr IS DISTINCT FROM NEW.trail_atr
     OR OLD.frozen_at IS DISTINCT FROM NEW.frozen_at THEN
    RAISE EXCEPTION 'POST_FIX_V1 frozen profile is immutable; create a new epoch';
  END IF;
  RETURN NEW;
END $$;

DROP TRIGGER IF EXISTS v5_post_fix_branch_immutable_v1
  ON analytics.v5_post_fix_branch_registry_v1;
CREATE TRIGGER v5_post_fix_branch_immutable_v1
BEFORE UPDATE ON analytics.v5_post_fix_branch_registry_v1
FOR EACH ROW EXECUTE FUNCTION analytics.reject_frozen_branch_mutation_v1();

GRANT SELECT,INSERT,UPDATE ON analytics.v5_post_fix_branch_registry_v1 TO alex,finam;

COMMIT;
