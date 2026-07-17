BEGIN;
UPDATE analytics.edge_search_run_analysis_v1 a SET
 primary_reason_code='EDGE_SEARCH_EXECUTOR_FAILED:DISCOVER_REGIME',
 failure_factors='["TECHNICAL_EXECUTOR_FAILURE"]'::jsonb,
 recommendation_code='FIX_EXECUTOR_AND_RETRY_SYSTEM_SCHEDULE',
 explanation_ru='Технический сбой этапа DISCOVER_REGIME; торговый результат не оценивался. Система повторит сценарий после исправления.'
FROM analytics.edge_search_step_run_v1 s
WHERE s.run_id=a.run_id AND s.executor_code='DISCOVER_REGIME' AND s.status_code='FAILED'
  AND coalesce(s.stderr_tail,'') LIKE '%IndexError: tuple index out of range%';
COMMIT;
