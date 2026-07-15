# MarketCore Profit Funnel Source Audit V2

stage=RESEARCH count=20 source=marketcore_ui.paper_edge_research_candidates_v1 source_age_seconds=156 scope=SCOPE_UNVERIFIED cohort=f056c3f6-dd4f-4df1-8def-dc224e23855c cohort_count=1 quality=UNVERIFIED net_pnl=NOT_APPLICABLE cost_impact=NOT_APPLICABLE
stage=CANDIDATE count=9 source=analytics.edge_candidate_v1 source_age_seconds=799077 scope=SCOPE_UNVERIFIED cohort=UNRECONCILED cohort_count=2 quality=UNVERIFIED net_pnl=NOT_APPLICABLE cost_impact=NOT_APPLICABLE
stage=VALIDATED_EDGE count=9 source=analytics.edge_candidate_v1.validation_score source_age_seconds=799077 scope=SCOPE_UNVERIFIED cohort=UNRECONCILED cohort_count=2 quality=UNVERIFIED net_pnl=NOT_APPLICABLE cost_impact=NOT_APPLICABLE
stage=OOS count=5 source=analytics.edge_oos_result_v1 source_age_seconds=290181 scope=SCOPE_UNVERIFIED cohort=20260712_MOMENTUM_THRESHOLD_RECALC_V2 cohort_count=1 quality=UNVERIFIED net_pnl=NOT_APPLICABLE cost_impact=NOT_APPLICABLE
stage=FORWARD count=1933 source=analytics.forward_edge_observation_v1 source_age_seconds=809 scope=SCOPE_UNVERIFIED cohort=4397bb9e-a18b-4fd0-9163-0c4634922e24 cohort_count=1 quality=UNVERIFIED net_pnl=-4126.263744000007865819 cost_impact=3268.5837440000000010
stage=SHADOW count=1933 source=analytics.forward_edge_shadow_trade_v1 source_age_seconds=144 scope=SCOPE_UNVERIFIED cohort=4397bb9e-a18b-4fd0-9163-0c4634922e24 cohort_count=1 quality=UNVERIFIED net_pnl=-4126.263744000007865819 cost_impact=3268.5837440000000010
stage=PAPER count=4073 source=marketcore_ui.paper_runtime_summary_v1 source_age_seconds=1145384 scope=SCOPE_UNVERIFIED cohort=8f9b1ed2-bb31-4d03-b6a7-c555df5b14fe cohort_count=1 quality=UNVERIFIED net_pnl=-22672.33 cost_impact=NOT_APPLICABLE
stage=RUNTIME count=16848 source=public.runtime_observations source_age_seconds=2218168 scope=SCOPE_UNVERIFIED cohort=UNRECONCILED cohort_count=0 quality=UNVERIFIED net_pnl=NOT_APPLICABLE cost_impact=NOT_APPLICABLE
stage=LIVE count=11011 source=public.runtime_governance_live_accumulation_v1 source_age_seconds=2 scope=SCOPE_UNVERIFIED cohort=UNRECONCILED cohort_count=0 quality=UNVERIFIED net_pnl=NOT_APPLICABLE cost_impact=NOT_APPLICABLE
stage=PROFIT count=0 source=analytics.profit_factory_profit_fact_v1[data_scope=REAL] source_age_seconds=UNAVAILABLE scope=REAL cohort=UNRECONCILED cohort_count=0 quality=UNAVAILABLE net_pnl=NOT_APPLICABLE cost_impact=NOT_APPLICABLE

stages_total=10
scope_unverified=9
cohort_unreconciled=5
real_trading_changed=0
VERDICT=MARKETCORE_STAGE7_PROFIT_FUNNEL_SOURCE_AUDIT_READY
