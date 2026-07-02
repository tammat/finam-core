BEGIN;

DROP VIEW IF EXISTS marketcore_ui.paper_runtime_explainability_v1;

CREATE VIEW marketcore_ui.paper_runtime_explainability_v1 AS

SELECT
    tcs.id                                      AS snapshot_id,
    tcs.ts,
    tcs.symbol,
    tcs.strategy,
    tcs.timeframe,
    tcs.trade_source,

    tcs.trade_id,
    tcs.db_trade_id,

    tcs.snapshot #>> '{attribution,signal_id}'          AS signal_id,
    tcs.snapshot #>> '{attribution,fill_id}'            AS fill_id,
    tcs.snapshot #>> '{attribution,trade_id}'           AS runtime_trade_id,

    tcs.snapshot #>  '{attribution}'                    AS attribution,
    tcs.snapshot #>  '{trade_context_snapshot}'         AS trade_context,
    tcs.snapshot #>  '{risk_context}'                  AS risk_context,
    tcs.snapshot #>  '{feature_context}'               AS feature_context,
    tcs.snapshot #>  '{exit_policy_context}'           AS exit_policy_context,
    tcs.snapshot #>  '{context_quality}'               AS context_quality,

    tcs.snapshot #>  '{attribution,trade_context_snapshot,edge_gate}'
                                                     AS edge_gate,

    rg.raw_json #> '{explainability}'                  AS explainability,

    trc.heat_status,
    trc.risk_multiplier,
    trc.governance_mode,

    sqa.confidence,
    sqa.rr,
    sqa.outcome_class,
    sqa.pnl,

    f.price                                           AS fill_price,
    f.qty                                             AS fill_qty,
    f.commission                                      AS fill_commission,

    now()                                             AS refreshed_at

FROM public.trade_context_snapshots tcs

LEFT JOIN public.trade_risk_context trc
       ON trc.closed_trade_id=tcs.db_trade_id

LEFT JOIN public.signal_quality_audit_v1 sqa
       ON sqa.signal_id =
          tcs.snapshot #>> '{attribution,signal_id}'

LEFT JOIN public.fills f
       ON f.fill_id =
          tcs.snapshot #>> '{attribution,fill_id}'

LEFT JOIN LATERAL (

    SELECT raw_json

    FROM public.runtime_governance_live_accumulation_v1 g

    WHERE g.symbol=tcs.symbol

    ORDER BY g.created_at DESC

    LIMIT 1

) rg ON TRUE

WHERE tcs.trade_source='paper';

GRANT SELECT ON marketcore_ui.paper_runtime_explainability_v1 TO alex;

COMMIT;
