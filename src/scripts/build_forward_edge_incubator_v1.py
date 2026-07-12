from __future__ import annotations

import hashlib
import json
import os
import uuid
from datetime import datetime
from zoneinfo import ZoneInfo

import psycopg2
import psycopg2.extras

DB=os.getenv("DATABASE_URL","postgresql:///finam_core")
SOURCE_VERSION="FORWARD_EDGE_INCUBATOR_V1"
MOSCOW=ZoneInfo("Europe/Moscow")

def main():
    cohort_id=str(uuid.uuid4()); activated_at=datetime.now(MOSCOW)
    with psycopg2.connect(DB) as conn:
      with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
        cur.execute("""CREATE TABLE IF NOT EXISTS analytics.forward_edge_incubator_v1(
          cohort_id uuid NOT NULL,incubator_candidate_id uuid NOT NULL,hypothesis_id uuid NOT NULL,
          source_trial_id uuid,source_kind text NOT NULL,strategy_family text NOT NULL,symbol text,timeframe text,
          frozen_parameter_json jsonb NOT NULL,frozen_fingerprint text NOT NULL,source_gross_pf numeric,
          activated_at timestamptz NOT NULL,observation_not_before timestamptz NOT NULL,
          minimum_observations integer NOT NULL,minimum_calendar_days integer NOT NULL,
          incubator_status text NOT NULL,trust_state text NOT NULL DEFAULT 'PENDING',paper_state text NOT NULL DEFAULT 'NOT_ELIGIBLE',
          promotion_allowed boolean NOT NULL DEFAULT false,live_allowed boolean NOT NULL DEFAULT false,
          source_version text NOT NULL,created_at timestamptz NOT NULL DEFAULT now(),PRIMARY KEY(cohort_id,incubator_candidate_id));
          CREATE TABLE IF NOT EXISTS analytics.forward_edge_observation_v1(
          observation_id uuid PRIMARY KEY,cohort_id uuid NOT NULL,incubator_candidate_id uuid NOT NULL,
          hypothesis_id uuid NOT NULL,signal_ts timestamptz NOT NULL,entry_ts timestamptz,exit_ts timestamptz,
          symbol text NOT NULL,timeframe text NOT NULL,regime_code text,session_code text,
          gross_pnl numeric,commission numeric,spread_cost numeric,slippage numeric,net_pnl numeric,
          observation_status text NOT NULL,data_quality_status text NOT NULL,
          source_version text NOT NULL,created_at timestamptz NOT NULL DEFAULT now(),
          UNIQUE(cohort_id,incubator_candidate_id,signal_ts));""")
        cur.execute("""CREATE OR REPLACE FUNCTION analytics.enforce_forward_observation_time_v1()
          RETURNS trigger LANGUAGE plpgsql AS $$
          DECLARE cutoff timestamptz;
          BEGIN
            SELECT observation_not_before INTO cutoff FROM analytics.forward_edge_incubator_v1
             WHERE cohort_id=NEW.cohort_id AND incubator_candidate_id=NEW.incubator_candidate_id;
            IF cutoff IS NULL THEN RAISE EXCEPTION 'UNKNOWN_FORWARD_INCUBATOR_CANDIDATE'; END IF;
            IF NEW.signal_ts < cutoff THEN RAISE EXCEPTION 'HISTORICAL_FORWARD_OBSERVATION_FORBIDDEN'; END IF;
            RETURN NEW;
          END $$;
          DROP TRIGGER IF EXISTS enforce_forward_observation_time_v1 ON analytics.forward_edge_observation_v1;
          CREATE TRIGGER enforce_forward_observation_time_v1 BEFORE INSERT OR UPDATE
           ON analytics.forward_edge_observation_v1 FOR EACH ROW
           EXECUTE FUNCTION analytics.enforce_forward_observation_time_v1();""")
        cur.execute("""SELECT replay_run_id FROM analytics.targeted_trade_level_replay_v1 ORDER BY created_at DESC LIMIT 1""")
        replay=cur.fetchone()
        cur.execute("""SELECT x.trial_id,x.hypothesis_id,x.strategy_family,x.gross_profit_factor,
          t.symbol,t.timeframe,h.parameter_json FROM analytics.targeted_trade_level_replay_v1 x
          JOIN analytics.hypothesis_trial_registry_v2 t USING(trial_id,hypothesis_id)
          JOIN analytics.canonical_hypothesis_registry_v1 h USING(hypothesis_id)
          WHERE x.replay_run_id=%s AND x.gross_profit_factor>=1.10 ORDER BY x.hypothesis_id""",(replay["replay_run_id"],))
        rows=[dict(r) for r in cur.fetchall()]
        for r in rows:
            frozen={"hypothesis_id":str(r["hypothesis_id"]),"family":r["strategy_family"],"symbol":r["symbol"],
                    "timeframe":r["timeframe"],"parameters":r["parameter_json"],"cost_model":"ACTUAL_WHEN_AVAILABLE"}
            canonical=json.dumps(frozen,sort_keys=True,separators=(",",":"),ensure_ascii=False)
            candidate_id=uuid.uuid5(uuid.UUID("7a201df9-352a-57cc-9466-e17599219e47"),canonical)
            cur.execute("""INSERT INTO analytics.forward_edge_incubator_v1 VALUES
              (%s,%s,%s,%s,'M5_COST_SENSITIVE',%s,%s,%s,%s,%s,%s,%s,%s,30,90,'ACCUMULATING','PENDING','NOT_ELIGIBLE',false,false,%s,now())""",
              (cohort_id,str(candidate_id),r["hypothesis_id"],r["trial_id"],r["strategy_family"],r["symbol"],r["timeframe"],
               psycopg2.extras.Json(r["parameter_json"]),hashlib.sha256(canonical.encode()).hexdigest(),r["gross_profit_factor"],
               activated_at,activated_at,SOURCE_VERSION))
        cur.execute("""SELECT h.hypothesis_id,h.parameter_json FROM analytics.swing_hypothesis_factory_v1 h
          JOIN analytics.swing_selection_validation_result_v1 v USING(factory_run_id,hypothesis_id)
          WHERE v.validation_status='VALIDATION_PASS' AND h.symbol='BR_ROLLING@RTSX' AND h.timeframe='D1'
          ORDER BY v.created_at DESC LIMIT 1""")
        swing=cur.fetchone()
        if swing:
            frozen={"hypothesis_id":str(swing["hypothesis_id"]),"family":"MOMENTUM","symbol":"BR_ROLLING@RTSX",
                    "timeframe":"D1","parameters":swing["parameter_json"],"artifact_gate":"FAILED_CALENDAR_STABILITY"}
            canonical=json.dumps(frozen,sort_keys=True,separators=(",",":"),ensure_ascii=False)
            candidate_id=uuid.uuid5(uuid.UUID("7a201df9-352a-57cc-9466-e17599219e47"),canonical)
            cur.execute("""INSERT INTO analytics.forward_edge_incubator_v1 VALUES
              (%s,%s,%s,NULL,'SWING_STABILITY_WATCH','MOMENTUM','BR_ROLLING@RTSX','D1',%s,%s,NULL,%s,%s,30,120,
               'WATCH_BLOCKED','NOT_ELIGIBLE','NOT_ELIGIBLE',false,false,%s,now())""",
              (cohort_id,str(candidate_id),swing["hypothesis_id"],psycopg2.extras.Json(swing["parameter_json"]),
               hashlib.sha256(canonical.encode()).hexdigest(),activated_at,activated_at,SOURCE_VERSION))
        cur.execute("SELECT source_kind,incubator_status,count(*) n FROM analytics.forward_edge_incubator_v1 WHERE cohort_id=%s GROUP BY 1,2",(cohort_id,))
        summary=cur.fetchall()
    print(f"cohort_id={cohort_id}");print(f"activated_at={activated_at.isoformat(timespec='seconds')}")
    for r in summary:print(f"source_kind={r['source_kind']} status={r['incubator_status']} candidates={r['n']}")
    print("historical_observations_imported=0");print("paper_created=0");print("live_allowed=0");print("VERDICT=FORWARD_EDGE_INCUBATOR_V1_FROZEN")
if __name__=="__main__":main()
