BEGIN;

ALTER TABLE marketcore_ui.research_summary_v1
ADD COLUMN IF NOT EXISTS research_candidates INTEGER NOT NULL DEFAULT 0;

COMMIT;
