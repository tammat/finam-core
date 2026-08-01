#!/usr/bin/env python3
from __future__ import annotations

import json,os
from datetime import datetime,timezone
from zoneinfo import ZoneInfo
import psycopg2
from psycopg2.extras import Json,RealDictCursor
from finam_core.session.session_manager import SessionManager

MSK=ZoneInfo('Europe/Moscow')

def main()->int:
 now=datetime.now(MSK); manager=SessionManager(); session=manager.get_regime('BRQ6@RTSX',market_data_live=False,now=now)
 with psycopg2.connect(os.environ['DATABASE_URL']) as conn,conn.cursor(cursor_factory=RealDictCursor) as cur:
  cur.execute("""SELECT event_code,risk_level,title_ru FROM analytics.market_event_risk_v1
   WHERE is_active AND starts_at<=clock_timestamp() AND (expires_at IS NULL OR expires_at>clock_timestamp())
   ORDER BY CASE risk_level WHEN 'SHOCK' THEN 1 WHEN 'ELEVATED' THEN 2 WHEN 'RECOVERY' THEN 3 ELSE 4 END LIMIT 1""")
  event=cur.fetchone() or {}; risk=str(event.get('risk_level') or 'NORMAL')
  cur.execute("""SELECT
   (SELECT max(ts) FROM market_bars WHERE symbol='IMOEX2' AND timeframe='M1') mx,
   (SELECT max(ts) FROM market_bars WHERE symbol LIKE 'VI%%@RTSX' AND timeframe='M1') rvi,
   (SELECT count(*) FROM market_bars WHERE symbol='IMOEX2' AND timeframe='M15'
     AND (ts AT TIME ZONE 'Europe/Moscow')::date=(clock_timestamp() AT TIME ZONE 'Europe/Moscow')::date
     AND ts+interval '15 minutes'<=clock_timestamp()) mx_m15,
   (SELECT count(*) FROM analytics.paper_research_position_projection_v1 p
     WHERE p.portfolio_scope LIKE 'FRESH_V5%%' AND abs(coalesce(nullif(p.state->>'qty','')::numeric,0))>0) positions,
   (SELECT count(*) FROM analytics.v5_oos_run_v1) oos"""); x=cur.fetchone()
  mx_fresh=bool(x['mx'] and 0<=(datetime.now(timezone.utc)-x['mx']).total_seconds()<=600)
  rvi_fresh=bool(x['rvi'] and 0<=(datetime.now(timezone.utc)-x['rvi']).total_seconds()<=1800)
  if session.get('reason')=='exchange_calendar_closed': verdict,reason='CALENDAR_CLOSED','EXCHANGE_CALENDAR_CLOSED'
  elif risk in {'SHOCK','ELEVATED'}: verdict,reason='SHADOW_ONLY',f'ACTIVE_EVENT_{risk}'
  elif int(x['mx_m15'] or 0)<2: verdict,reason='WAIT','MX_M15_WARMUP'
  elif not mx_fresh or not rvi_fresh: verdict,reason='BLOCK','MARKET_CONTEXT_NOT_FRESH'
  elif risk=='RECOVERY': verdict,reason='RECOVERY_CHECK','PER_SYMBOL_SHOCK_GATE_REQUIRED'
  else: verdict,reason='PAPER_READY','BASE_CONTEXT_READY'
  details={'event_title':event.get('title_ru'),'next_open':manager.next_entry_session(symbol='BRQ6@RTSX',now=now).isoformat()}
  cur.execute("""INSERT INTO analytics.monday_readiness_snapshot_v1(session_phase,event_code,risk_level,
   mx_last_ts,rvi_last_ts,mx_fresh,rvi_fresh,completed_mx_m15,active_positions,oos_runs,
   verdict_code,reason_code,details) VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
   (session.get('phase'),event.get('event_code'),risk,x['mx'],x['rvi'],mx_fresh,rvi_fresh,int(x['mx_m15'] or 0),
    int(x['positions'] or 0),int(x['oos'] or 0),verdict,reason,Json(details)))
 print(f'verdict={verdict} reason={reason} risk={risk} mx_fresh={int(mx_fresh)} rvi_fresh={int(rvi_fresh)} mx_m15={x["mx_m15"]}')
 print('paper_changed=0 real_changed=0');print('VERDICT=MONDAY_READINESS_SNAPSHOT_OK');return 0

if __name__=='__main__':raise SystemExit(main())
