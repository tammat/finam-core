BEGIN;

CREATE TABLE IF NOT EXISTS analytics.forward_edge_baseline_v1 (
    baseline_key text PRIMARY KEY CHECK (baseline_key = 'EDGE_SEARCH'),
    cohort_id uuid NOT NULL,
    frozen_at timestamptz NOT NULL DEFAULT now(),
    frozen_reason text NOT NULL,
    source_version text NOT NULL
);

INSERT INTO analytics.forward_edge_baseline_v1 (
    baseline_key, cohort_id, frozen_reason, source_version
)
SELECT
    'EDGE_SEARCH', i.cohort_id,
    'Freeze last cohort with forward observations; execution proxies must not create research cohorts',
    '053_freeze_forward_edge_baseline_v1'
FROM analytics.forward_edge_incubator_v1 i
WHERE EXISTS (
    SELECT 1
    FROM analytics.forward_edge_observation_v1 o
    WHERE o.cohort_id = i.cohort_id
)
GROUP BY i.cohort_id
ORDER BY max(i.created_at) DESC
LIMIT 1
ON CONFLICT (baseline_key) DO NOTHING;

CREATE OR REPLACE FUNCTION analytics.forward_edge_baseline_cohort_id_v1()
RETURNS uuid
LANGUAGE sql
STABLE
AS $$
    SELECT cohort_id
    FROM analytics.forward_edge_baseline_v1
    WHERE baseline_key = 'EDGE_SEARCH'
$$;

CREATE OR REPLACE FUNCTION analytics.enforce_forward_edge_baseline_v1()
RETURNS trigger
LANGUAGE plpgsql
AS $$
DECLARE
    frozen_cohort_id uuid;
BEGIN
    frozen_cohort_id := analytics.forward_edge_baseline_cohort_id_v1();
    IF frozen_cohort_id IS NOT NULL AND NEW.cohort_id <> frozen_cohort_id THEN
        RAISE EXCEPTION
            'forward edge baseline is frozen at cohort %, rejected cohort %',
            frozen_cohort_id, NEW.cohort_id
            USING ERRCODE = 'check_violation';
    END IF;
    RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS enforce_forward_edge_baseline_v1
ON analytics.forward_edge_incubator_v1;

CREATE TRIGGER enforce_forward_edge_baseline_v1
BEFORE INSERT OR UPDATE OF cohort_id
ON analytics.forward_edge_incubator_v1
FOR EACH ROW
EXECUTE FUNCTION analytics.enforce_forward_edge_baseline_v1();

COMMIT;
