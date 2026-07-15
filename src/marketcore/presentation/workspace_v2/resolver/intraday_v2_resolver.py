from __future__ import annotations
from datetime import datetime, timezone
from decimal import Decimal
from zoneinfo import ZoneInfo
import psycopg2
import psycopg2.extras
from marketcore.presentation.workspace_v2.domain.intraday_snapshot_v2 import IntradaySnapshotV2

def _utc(v):
    if v is None:return None
    return (v.replace(tzinfo=timezone.utc) if v.tzinfo is None else v).astimezone(timezone.utc)

class IntradayV2Resolver:
    def resolve(self, *, timezone_code="Europe/Moscow", generated_at=None):
        now=_utc(generated_at) or datetime.now(timezone.utc); session_date=now.astimezone(ZoneInfo(timezone_code)).date()
        with psycopg2.connect("postgresql:///finam_core") as c:
            with c.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as x:
                x.execute('SELECT count(*) total,count(DISTINCT "Инструмент") instruments,coalesce(sum("P&L сделки"),0) pnl,max("Время") last_at FROM public.v_intraday_pnl_ru WHERE "Дата"=%s',(session_date,)); intraday=x.fetchone()
                x.execute("SELECT paper_status,signals_today,fills_today,pnl_today,refreshed_at FROM marketcore_ui.paper_runtime_summary_v1 WHERE id=1"); paper=x.fetchone() or {}
                x.execute("""SELECT (SELECT count(*) FROM public.shadow_runtime_orders) orders,(SELECT count(*) FROM public.shadow_runtime_fills) fills,(SELECT count(*) FROM public.shadow_runtime_positions WHERE qty<>0) positions,GREATEST((SELECT max(created_at) FROM public.shadow_runtime_orders),(SELECT max(created_at) FROM public.shadow_runtime_fills),(SELECT max(updated_at) FROM public.shadow_runtime_positions)) last_at"""); shadow=x.fetchone()
        return IntradaySnapshotV2(session_date,int(intraday["total"]),int(intraday["instruments"]),Decimal(intraday["pnl"]),_utc(intraday["last_at"]),str(paper.get("paper_status") or "UNAVAILABLE"),int(paper.get("signals_today") or 0),int(paper.get("fills_today") or 0),Decimal(paper.get("pnl_today") or 0),_utc(paper.get("refreshed_at")),int(shadow["orders"]),int(shadow["fills"]),int(shadow["positions"]),_utc(shadow["last_at"]),now)
