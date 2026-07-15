from __future__ import annotations
from datetime import datetime, timezone
import psycopg2
import psycopg2.extras
from marketcore.presentation.workspace_v2.domain.research_snapshot_v2 import ResearchSnapshotV2

def _utc(value):
    if value is None: return None
    return (value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value).astimezone(timezone.utc)

def _count_symbols(value):
    return len([item for item in str(value or "").split(",") if item.strip()])

class ResearchV2Resolver:
    def resolve(self, *, generated_at=None):
        now=_utc(generated_at) or datetime.now(timezone.utc)
        with psycopg2.connect("postgresql:///finam_core") as connection:
            with connection.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cursor:
                cursor.execute("SELECT status,active_symbols,failed_symbols,last_cycle_at FROM public.research_runtime_state ORDER BY updated_at DESC LIMIT 1")
                runtime=cursor.fetchone() or {}
                cursor.execute("SELECT research_candidates,oos_pass,paper_ready,refreshed_at FROM marketcore_ui.research_summary_v1 WHERE id=1")
                summary=cursor.fetchone() or {}
                cursor.execute("SELECT count(*) total,count(*) FILTER (WHERE status_code NOT IN ('DONE','FAILED')) pending,count(*) FILTER (WHERE status_code='FAILED') failed,max(updated_at) updated_at FROM analytics.research_queue_v1")
                queue=cursor.fetchone()
                cursor.execute("SELECT count(*) total,count(*) FILTER (WHERE verdict_code='OOS_PASS') passed,max(updated_at) updated_at FROM analytics.edge_oos_result_v1")
                oos=cursor.fetchone()
        return ResearchSnapshotV2(str(runtime.get("status") or "UNAVAILABLE"),_count_symbols(runtime.get("active_symbols")),_count_symbols(runtime.get("failed_symbols")),_utc(runtime.get("last_cycle_at")),int(summary.get("research_candidates") or 0),int(summary.get("oos_pass") or 0),int(summary.get("paper_ready") or 0),_utc(summary.get("refreshed_at")),int(queue["total"]),int(queue["pending"]),int(queue["failed"]),_utc(queue["updated_at"]),int(oos["total"]),int(oos["passed"]),_utc(oos["updated_at"]),now)
