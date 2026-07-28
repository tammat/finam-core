BEGIN;

-- PF без убыточных сделок не является числом 999 и не может дать допуск.
-- Витрины пересоздаются миграцией 201; этот столбец делает состояние явным
-- для панели и аудита.
ALTER TABLE analytics.hierarchical_evidence_v1
    ADD COLUMN IF NOT EXISTS profit_factor_observable boolean NOT NULL DEFAULT false;

CREATE OR REPLACE VIEW analytics.hierarchical_runtime_priority_v1 AS
SELECT DISTINCT ON (h.symbol_code)
       h.symbol_code AS symbol,
       h.priority_score,
       h.closed_trades AS accumulated_trades,
       false AS early_stopped,
       h.reason_code
FROM analytics.hierarchical_evidence_v1 h
WHERE h.symbol_code <> '*'
  AND h.decision_code IN ('COLLECT','DISCOVERY_ONLY','READY_FOR_OOS')
  AND NOT EXISTS (
      SELECT 1
      FROM analytics.fresh_v4_early_loss_quarantine_v1 q
      WHERE q.symbol = h.symbol_code
        AND q.strategy_code = h.strategy_code
        AND q.quarantined
        AND NOT EXISTS (
            SELECT 1
            FROM analytics.fresh_v4_early_loss_quarantine_v1 viable
            WHERE viable.symbol = q.symbol
              AND viable.strategy_code = q.strategy_code
              AND NOT viable.quarantined
        )
  )
ORDER BY h.symbol_code,h.priority_score DESC,h.closed_trades DESC;

GRANT SELECT ON analytics.system_job_schedule_v1 TO finam;
GRANT SELECT ON analytics.system_job_run_v1 TO finam;
GRANT SELECT ON analytics.hierarchical_runtime_priority_v1 TO alex,finam;

COMMIT;
