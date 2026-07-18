from __future__ import annotations

import uuid

import psycopg2
import psycopg2.extras


def test_isolated_oos_forward_shadow_paper_contract_rolls_back() -> None:
    connection = psycopg2.connect("postgresql:///finam_core")
    try:
        with connection.cursor() as cursor:
            cursor.execute("""SELECT i.plan_item_id,i.hypothesis_id,i.strategy_family,i.symbol,i.timeframe,i.parameter_snapshot
              FROM analytics.swing_next_research_plan_item_v1 i
              WHERE NOT EXISTS(SELECT 1 FROM analytics.swing_final_oos_result_v1 r WHERE r.plan_item_id=i.plan_item_id)
              ORDER BY i.priority LIMIT 1 FOR UPDATE""")
            item = cursor.fetchone()
            assert item is not None
            plan_item,hypothesis,strategy,symbol,timeframe,parameters = item
            result_id,process_id,cohort_id,candidate_id = (uuid.uuid4() for _ in range(4))
            cursor.execute("""INSERT INTO analytics.swing_final_oos_result_v1(
              result_id,plan_item_id,holdout_fingerprint,holdout_start,holdout_end,trades,profit_factor,expectancy,
              folds_passed,adjusted_p_value,stressed_expectancy,capacity_rub,portfolio_correlation,
              statistical_pass,robustness_pass,holdout_pass,execution_pass,capacity_pass,portfolio_pass,
              verdict_code,promotion_allowed,reason_codes,execution_policy)
              VALUES(%s,%s,%s,now()-interval '60 days',now()-interval '30 days',40,1.4,25,4,0.01,12,1000000,0.2,
              true,true,true,true,true,true,'PASS',true,'[]'::jsonb,'{"probe":true}'::jsonb)""",
              (str(result_id),str(plan_item),"CONTRACT_PROBE:"+str(result_id)))
            cursor.execute("""INSERT INTO analytics.swing_candidate_lifecycle_v1(
              process_id,result_id,plan_item_id,stage_code,status_code,progress_pct,forward_not_before,gate_evidence,reason_codes)
              VALUES(%s,%s,%s,'FORWARD','PASS',100,now()-interval '20 days','{"probe":true}'::jsonb,'[]'::jsonb)""",
              (str(process_id),str(result_id),str(plan_item)))
            cursor.execute("""INSERT INTO analytics.swing_shadow_cohort_v1(
              swing_shadow_cohort_id,swing_shadow_candidate_id,factory_run_id,validation_run_id,hypothesis_id,
              strategy_family,symbol,timeframe,frozen_parameter_json,selection_pf,validation_pf,validation_expectancy,
              validation_folds_passed,adjusted_p_value,validation_status,observation_not_before,cohort_status,
              criteria_json,source_version)
              VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,1.4,1.3,20,4,0.01,'PASS',now()-interval '10 days','PASSED',
              '{"probe":true}'::jsonb,'SWING_LIFECYCLE_CONTRACT_PROBE_V1')""",
              (str(cohort_id),str(candidate_id),str(uuid.uuid4()),str(uuid.uuid4()),str(hypothesis),strategy,symbol,timeframe,psycopg2.extras.Json(parameters)))
            cursor.execute("""UPDATE analytics.swing_candidate_lifecycle_v1 SET stage_code='SHADOW',status_code='PASS',
              shadow_cohort_id=%s,progress_pct=100 WHERE process_id=%s""",(str(cohort_id),str(process_id)))
            cursor.execute("""INSERT INTO analytics.swing_paper_admission_v1(
              admission_id,process_id,shadow_cohort_id,admission_evidence,paper_allowed)
              VALUES(%s,%s,%s,'{"probe":true}'::jsonb,true)""",(str(uuid.uuid4()),str(process_id),str(cohort_id)))
            cursor.execute("""UPDATE analytics.swing_candidate_lifecycle_v1 SET stage_code='PAPER',status_code='READY',
              paper_allowed=true,live_allowed=false,progress_pct=100 WHERE process_id=%s""",(str(process_id),))
            cursor.execute("""INSERT INTO analytics.swing_paper_strategy_v1(
              process_id,candidate_key,strategy_family,symbol,timeframe,parameter_snapshot,status_code)
              VALUES(%s,%s,%s,%s,%s,%s,'ACTIVE')""",
              (str(process_id),uuid.uuid4().int%(2**62),strategy,symbol,timeframe,psycopg2.extras.Json(parameters)))
            cursor.execute("INSERT INTO analytics.swing_paper_position_v1(process_id,status_code) VALUES(%s,'FLAT')",(str(process_id),))
            cursor.execute("""SELECT l.stage_code,l.status_code,l.paper_allowed,l.live_allowed,a.paper_allowed,s.status_code,p.status_code
              FROM analytics.swing_candidate_lifecycle_v1 l JOIN analytics.swing_paper_admission_v1 a USING(process_id)
              JOIN analytics.swing_paper_strategy_v1 s USING(process_id) JOIN analytics.swing_paper_position_v1 p USING(process_id)
              WHERE l.process_id=%s""",(str(process_id),))
            assert cursor.fetchone() == ("PAPER","READY",True,False,True,"ACTIVE","FLAT")
    finally:
        connection.rollback()
        connection.close()
