from __future__ import annotations

import json
import os
import time
from datetime import datetime,timedelta
from decimal import Decimal
from typing import Any
from zoneinfo import ZoneInfo

import psycopg2
import psycopg2.extras
import requests


DB=os.getenv("DATABASE_URL","postgresql:///finam_core")
SOURCE_VERSION="MOEX_BRENT_ONLINE_V1"
MOSCOW=ZoneInfo("Europe/Moscow")


def fetch(secid:str,date_from:str,date_till:str)->list[dict[str,Any]]:
    rows=[]; start=0
    while True:
        response=requests.get(f"https://iss.moex.com/iss/engines/futures/markets/forts/securities/{secid}/candles.json",
            params={"from":date_from,"till":date_till,"interval":1,"start":start,"iss.meta":"off"},timeout=20)
        response.raise_for_status(); block=response.json().get("candles",{}); raw=block.get("data",[])
        rows.extend(dict(zip(block.get("columns",[]),item)) for item in raw)
        if len(raw)<100: break
        start+=len(raw); time.sleep(.1)
    return rows


def number(value:Any):
    return Decimal(str(value)) if value is not None else None


def main()->None:
    now=datetime.now(MOSCOW); output=[]
    with psycopg2.connect(DB) as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("SELECT pg_try_advisory_xact_lock(hashtext(%s)) acquired",(SOURCE_VERSION,))
            if not cur.fetchone()["acquired"]: print("status=SKIPPED_ALREADY_RUNNING"); return
            cur.execute("""SELECT contract_symbol,expiration_date FROM public.futures_contract_universe
                WHERE root_symbol='BR' AND is_active AND expiration_date>=current_date ORDER BY expiration_date LIMIT 3""")
            contracts=cur.fetchall()
            for contract in contracts:
                symbol=contract["contract_symbol"]; secid=symbol.split("@",1)[0]
                cur.execute("SELECT max(ts) latest FROM public.market_bars WHERE symbol=%s AND timeframe='M1'",(symbol,))
                previous=cur.fetchone()["latest"]; date_from=((previous or now-timedelta(days=3)).date()-timedelta(days=1)).isoformat()
                candles=fetch(secid,date_from,now.date().isoformat()); closed=[]
                for candle in candles:
                    end=candle.get("end")
                    if end and datetime.fromisoformat(str(end)).replace(tzinfo=MOSCOW)<=now: closed.append(candle)
                for candle in closed:
                    cur.execute("""INSERT INTO public.market_bars(symbol,timeframe,ts,open,high,low,close,volume,source)
                        VALUES(%s,'M1',%s,%s,%s,%s,%s,%s,%s) ON CONFLICT(symbol,timeframe,ts) DO UPDATE SET
                        open=excluded.open,high=excluded.high,low=excluded.low,close=excluded.close,volume=excluded.volume,source=excluded.source""",
                        (symbol,candle["begin"],number(candle.get("open")),number(candle.get("high")),number(candle.get("low")),number(candle.get("close")),number(candle.get("volume") or 0),SOURCE_VERSION))
                cur.execute("""WITH m AS (SELECT *,date_trunc('hour',ts)+floor(extract(minute FROM ts)/5)*interval '5 min' bucket
                        FROM public.market_bars WHERE symbol=%s AND timeframe='M1' AND ts>=%s::date), c AS (
                        SELECT bucket ts,(array_agg(open ORDER BY ts))[1] open,max(high) high,min(low) low,
                        (array_agg(close ORDER BY ts DESC))[1] close,sum(coalesce(volume,0)) volume FROM m
                        WHERE bucket+interval '5 min'<=now() GROUP BY bucket HAVING count(DISTINCT ts)=5)
                    INSERT INTO public.market_bars(symbol,timeframe,ts,open,high,low,close,volume,source)
                    SELECT %s,'M5',ts,open,high,low,close,volume,%s FROM c ON CONFLICT(symbol,timeframe,ts) DO UPDATE SET
                    open=excluded.open,high=excluded.high,low=excluded.low,close=excluded.close,volume=excluded.volume,source=excluded.source""",
                    (symbol,date_from,symbol,SOURCE_VERSION)); m5=cur.rowcount
                output.append({"symbol":symbol,"m1":len(closed),"m5":m5,"expiration":str(contract["expiration_date"])})
    print(json.dumps({"status":"ONLINE","rows":output},ensure_ascii=False)); print("VERDICT=MOEX_BRENT_ONLINE_V1_OK")


if __name__=="__main__": main()
