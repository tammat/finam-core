INSERT INTO analytics.profit_factory_candidate_link_v1 (
    candidate_id,
    target_stage,
    target_entity_type,
    target_entity_id,
    source_table,
    source_record_id,
    link_method,
    verification_status,
    confidence_score,
    evidence_payload,
    evidence_observed_at,
    verified_at,
    verified_by
)
SELECT
    i.candidate_id,
    'PAPER',
    'PAPER_RUNTIME_CANDIDATE',
    p.id::text,
    'analytics.paper_runtime_candidate_v1',
    p.id::text,
    'SOURCE_REFERENCE',
    'VERIFIED',
    1,
    jsonb_build_object(
        'edge_candidate_id', e.id,
        'candidate_uuid', e.candidate_uuid,
        'observation_uuid', e.observation_uuid,
        'strategy_code', e.strategy_code,
        'symbol', e.symbol,
        'timeframe', e.timeframe,
        'paper_status', p.paper_status,
        'reconciliation_rule', 'EDGE_ID_OBSERVATION_STRATEGY_SYMBOL_TIMEFRAME_EXACT_V1'
    ),
    p.updated_at,
    now(),
    'PROFIT_FACTORY_PAPER_RECONCILIATION_V1'
FROM analytics.paper_runtime_candidate_v1 p
JOIN analytics.edge_candidate_v1 e
  ON e.id=p.candidate_id
 AND e.observation_uuid=p.observation_uuid
 AND e.strategy_code=p.strategy_code
 AND e.symbol=p.symbol
 AND e.timeframe=p.timeframe
JOIN analytics.profit_factory_candidate_identity_v1 i
  ON i.edge_candidate_id=e.id
 AND i.candidate_id=e.candidate_uuid
 AND i.observation_id=e.observation_uuid
WHERE p.observation_uuid IS NOT NULL
ON CONFLICT (candidate_id, target_stage, target_entity_type, target_entity_id)
DO NOTHING;
