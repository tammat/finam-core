BEGIN;

-- Runtime collection is driven only by exact V5 contexts.  Higher hierarchy
-- levels remain analytical support and cannot displace a concrete branch.
CREATE OR REPLACE VIEW analytics.hierarchical_runtime_priority_v1 AS
SELECT DISTINCT ON (h.symbol_code)
       h.symbol_code AS symbol,
       h.priority_score,
       h.closed_trades AS accumulated_trades,
       false AS early_stopped,
       h.reason_code
FROM analytics.hierarchical_evidence_v1 h
WHERE h.cohort_code='FRESH_V5_CONFIRM'
  AND h.level_code='EXACT_CONTEXT'
  AND h.symbol_code<>'*'
  AND h.decision_code IN ('COLLECT','DISCOVERY_ONLY','READY_FOR_OOS')
  AND NOT EXISTS (
      SELECT 1
      FROM analytics.fresh_v4_early_loss_quarantine_v1 q
      WHERE q.symbol=h.symbol_code
        AND q.strategy_code=h.strategy_code
        AND q.quarantined
        AND NOT EXISTS (
            SELECT 1
            FROM analytics.fresh_v4_early_loss_quarantine_v1 viable
            WHERE viable.symbol=q.symbol
              AND viable.strategy_code=q.strategy_code
              AND NOT viable.quarantined
        )
  )
ORDER BY h.symbol_code,h.priority_score DESC,h.closed_trades DESC;

COMMENT ON VIEW analytics.hierarchical_runtime_priority_v1 IS
'Evidence-driven V5 runtime priority: exact branches only; 20-79, 10-19, 5-9, 3-4, then new branches.';

GRANT SELECT ON analytics.hierarchical_runtime_priority_v1 TO alex,finam;

COMMIT;
