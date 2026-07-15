from __future__ import annotations
from datetime import datetime,timezone
import psycopg2
import psycopg2.extras
from marketcore.presentation.workspace_v2.domain.program_snapshot_v2 import ProgramSnapshotV2
def _utc(v):
    if v is None:return None
    return (v.replace(tzinfo=timezone.utc) if v.tzinfo is None else v).astimezone(timezone.utc)
class ProgramV2Resolver:
    def resolve(self,*,generated_at=None):
        now=_utc(generated_at) or datetime.now(timezone.utc)
        with psycopg2.connect("postgresql:///finam_core") as c:
            with c.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as x:
                x.execute("SELECT quarter,platform_status,research_status,top3_status,paper_status,marketcore_status,refreshed_at FROM marketcore_ui.program_summary_v1 WHERE id=1");s=x.fetchone() or {}
                x.execute("SELECT count(*) total,count(*) FILTER (WHERE micro_live_ready) ready,count(*) FILTER (WHERE micro_live_allowed) allowed,max(refreshed_at) refreshed_at FROM marketcore_ui.micro_live_readiness_v1");r=x.fetchone()
        return ProgramSnapshotV2(str(s.get("quarter") or "UNAVAILABLE"),str(s.get("platform_status") or "UNAVAILABLE"),str(s.get("research_status") or "UNAVAILABLE"),str(s.get("top3_status") or "UNAVAILABLE"),str(s.get("paper_status") or "UNAVAILABLE"),str(s.get("marketcore_status") or "UNAVAILABLE"),_utc(s.get("refreshed_at")),int(r["total"]),int(r["ready"]),int(r["allowed"]),_utc(r["refreshed_at"]),now)
