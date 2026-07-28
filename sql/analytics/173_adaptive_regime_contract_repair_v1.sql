BEGIN;

-- Repair unfinished adaptive tasks produced before the canonical regime
-- contract was inherited.  Historical completed results remain immutable.
UPDATE analytics.edge_regime_discovery_task_v3 AS task
SET configuration_spec = jsonb_set(
        jsonb_set(
            task.configuration_spec,
            '{regime_policy}',
            registry.regime_policy || jsonb_build_object(
                'target_symbols',
                coalesce(task.configuration_spec #> '{regime_policy,target_symbols}', '[]'::jsonb)
            ),
            true
        ),
        '{gate_policy}',
        registry.gate_policy,
        true
    )
FROM analytics.edge_search_algorithm_registry_v1 AS registry
WHERE task.strategy_family = registry.algorithm_code
  AND task.status_code IN ('PENDING', 'RUNNING')
  AND registry.enabled
  AND jsonb_array_length(
        coalesce(task.configuration_spec #> '{regime_policy,allowed_regimes}', '[]'::jsonb)
      ) = 0;

COMMIT;
