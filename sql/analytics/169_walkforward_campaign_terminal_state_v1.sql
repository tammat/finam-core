BEGIN;

UPDATE analytics.walkforward_campaign_v4
SET status_code='COMPLETE',
    progress_pct=100,
    finished_at=coalesce(finished_at,clock_timestamp()),
    heartbeat_at=clock_timestamp()
WHERE phase_code='COMPLETE' AND status_code<>'COMPLETE';

CREATE OR REPLACE FUNCTION analytics.guard_walkforward_campaign_terminal_state_v1()
RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
  IF NEW.phase_code='COMPLETE' THEN
    NEW.status_code := 'COMPLETE';
    NEW.progress_pct := 100;
    NEW.finished_at := coalesce(NEW.finished_at,clock_timestamp());
  END IF;
  RETURN NEW;
END $$;

DROP TRIGGER IF EXISTS trg_walkforward_campaign_terminal_state_v1
ON analytics.walkforward_campaign_v4;
CREATE TRIGGER trg_walkforward_campaign_terminal_state_v1
BEFORE INSERT OR UPDATE ON analytics.walkforward_campaign_v4
FOR EACH ROW EXECUTE FUNCTION analytics.guard_walkforward_campaign_terminal_state_v1();

COMMIT;
