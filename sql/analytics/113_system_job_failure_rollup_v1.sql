BEGIN;
CREATE TABLE IF NOT EXISTS analytics.system_job_failure_rollup_v1(
 job_code text NOT NULL,
 error_fingerprint text NOT NULL,
 occurrences bigint NOT NULL,
 first_seen_at timestamptz NOT NULL,
 last_seen_at timestamptz NOT NULL,
 return_code integer,
 stdout_sample text NOT NULL DEFAULT '',
 stderr_sample text NOT NULL DEFAULT '',
 resolved_at timestamptz,
 PRIMARY KEY(job_code,error_fingerprint)
);

WITH failures AS (
 SELECT job_code,md5(coalesce(stderr_tail,'')||E'\n'||coalesce(stdout_tail,'')) error_fingerprint,
  count(*) occurrences,min(started_at) first_seen_at,max(started_at) last_seen_at,max(return_code) return_code,
  max(coalesce(stdout_tail,'')) stdout_sample,max(coalesce(stderr_tail,'')) stderr_sample
 FROM analytics.system_job_run_v1 WHERE status_code IN('FAILED','TIMEOUT') GROUP BY 1,2
)
INSERT INTO analytics.system_job_failure_rollup_v1(
 job_code,error_fingerprint,occurrences,first_seen_at,last_seen_at,return_code,stdout_sample,stderr_sample,resolved_at)
SELECT f.job_code,f.error_fingerprint,f.occurrences,f.first_seen_at,f.last_seen_at,f.return_code,
 f.stdout_sample,f.stderr_sample,CASE WHEN EXISTS(SELECT 1 FROM analytics.system_job_run_v1 ok
   WHERE ok.job_code=f.job_code AND ok.status_code='COMPLETE' AND ok.started_at>f.last_seen_at)
 THEN f.last_seen_at ELSE NULL END FROM failures f
ON CONFLICT(job_code,error_fingerprint) DO UPDATE SET
 occurrences=greatest(analytics.system_job_failure_rollup_v1.occurrences,excluded.occurrences),
 first_seen_at=least(analytics.system_job_failure_rollup_v1.first_seen_at,excluded.first_seen_at),
 last_seen_at=greatest(analytics.system_job_failure_rollup_v1.last_seen_at,excluded.last_seen_at),
 return_code=excluded.return_code,stdout_sample=excluded.stdout_sample,stderr_sample=excluded.stderr_sample,
 resolved_at=coalesce(excluded.resolved_at,analytics.system_job_failure_rollup_v1.resolved_at);

DELETE FROM analytics.system_job_run_v1 old
USING analytics.system_job_run_v1 newer
WHERE old.job_code=newer.job_code AND old.status_code IN('FAILED','TIMEOUT')
 AND newer.status_code IN('FAILED','TIMEOUT') AND old.started_at<newer.started_at
 AND md5(coalesce(old.stderr_tail,'')||E'\n'||coalesce(old.stdout_tail,''))=
     md5(coalesce(newer.stderr_tail,'')||E'\n'||coalesce(newer.stdout_tail,''));
GRANT SELECT,INSERT,UPDATE ON analytics.system_job_failure_rollup_v1 TO alex;
COMMIT;
