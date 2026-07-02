from __future__ import annotations

import os
import json
import psycopg2
from psycopg2.extras import Json

DB = os.getenv("DATABASE_URL", "postgresql:///finam_core")
DOMAIN = os.getenv("KG_DOMAIN", "PAPER_RUNTIME")

REQUIRED_ENTITY_TYPES = [
    "TradeContextSnapshot",
    "Attribution",
    "RiskContext",
    "FeatureContext",
    "EdgeGate",
    "Fill",
    "ClosedTrade",
]

REQUIRED_LOCALES = ["ru", "en"]


def add_finding(cur, run_id, check_code, severity, object_type, object_key, details):
    cur.execute(
        """
        INSERT INTO knowledge_graph.validation_findings
        (run_id, domain, check_code, severity, object_type, object_key, details)
        VALUES (%s,%s,%s,%s,%s,%s,%s);
        """,
        (run_id, DOMAIN, check_code, severity, object_type, object_key, Json(details)),
    )


def main() -> None:
    with psycopg2.connect(DB) as conn:
        with conn.cursor() as cur:
            print("=== KNOWLEDGE_GRAPH_VALIDATION_V1 ===")

            cur.execute(
                """
                INSERT INTO knowledge_graph.validation_runs(domain, status)
                VALUES (%s, 'STARTED')
                RETURNING run_id;
                """,
                (DOMAIN,),
            )
            run_id = cur.fetchone()[0]

            cur.execute("SELECT count(*) FROM knowledge_graph.nodes WHERE domain=%s;", (DOMAIN,))
            nodes = cur.fetchone()[0]

            cur.execute("SELECT count(*) FROM knowledge_graph.edges WHERE domain=%s;", (DOMAIN,))
            edges = cur.fetchone()[0]

            cur.execute(
                """
                SELECT count(*)
                FROM knowledge_graph.nodes n
                WHERE n.domain=%s
                  AND NOT EXISTS (
                    SELECT 1 FROM knowledge_graph.edges e
                    WHERE e.domain=n.domain
                      AND (e.from_node_id=n.node_id OR e.to_node_id=n.node_id)
                  );
                """,
                (DOMAIN,),
            )
            orphan_nodes = cur.fetchone()[0]
            if orphan_nodes > 0:
                add_finding(cur, run_id, "ORPHAN_NODES", "WARN", "node", None, {"count": orphan_nodes})

            cur.execute(
                """
                SELECT count(*)
                FROM knowledge_graph.edges e
                LEFT JOIN knowledge_graph.nodes a ON a.node_id=e.from_node_id
                LEFT JOIN knowledge_graph.nodes b ON b.node_id=e.to_node_id
                WHERE e.domain=%s
                  AND (a.node_id IS NULL OR b.node_id IS NULL);
                """,
                (DOMAIN,),
            )
            broken_edges = cur.fetchone()[0]
            if broken_edges > 0:
                add_finding(cur, run_id, "BROKEN_EDGES", "ERROR", "edge", None, {"count": broken_edges})

            cur.execute(
                """
                SELECT count(*)
                FROM (
                    SELECT domain, source_table, source_pk, entity_type, count(*)
                    FROM knowledge_graph.nodes
                    WHERE domain=%s
                    GROUP BY domain, source_table, source_pk, entity_type
                    HAVING count(*) > 1
                ) d;
                """,
                (DOMAIN,),
            )
            duplicate_nodes = cur.fetchone()[0]
            if duplicate_nodes > 0:
                add_finding(cur, run_id, "DUPLICATE_NODES", "ERROR", "node", None, {"count": duplicate_nodes})

            cur.execute(
                """
                SELECT count(*)
                FROM (
                    SELECT from_node_id, to_node_id, edge_type, count(*)
                    FROM knowledge_graph.edges
                    WHERE domain=%s
                    GROUP BY from_node_id, to_node_id, edge_type
                    HAVING count(*) > 1
                ) d;
                """,
                (DOMAIN,),
            )
            duplicate_edges = cur.fetchone()[0]
            if duplicate_edges > 0:
                add_finding(cur, run_id, "DUPLICATE_EDGES", "ERROR", "edge", None, {"count": duplicate_edges})

            missing_i18n = 0
            for entity in REQUIRED_ENTITY_TYPES:
                for locale in REQUIRED_LOCALES:
                    cur.execute(
                        """
                        SELECT count(*)
                        FROM knowledge_graph.i18n_labels
                        WHERE object_type='entity_type'
                          AND object_key=%s
                          AND locale=%s;
                        """,
                        (entity, locale),
                    )
                    if cur.fetchone()[0] == 0:
                        missing_i18n += 1
                        add_finding(
                            cur,
                            run_id,
                            "MISSING_I18N_LABEL",
                            "WARN",
                            "entity_type",
                            entity,
                            {"locale": locale},
                        )

            cur.execute(
                """
                SELECT count(*)
                FROM knowledge_graph.semantic_terms
                WHERE enabled=true;
                """
            )
            semantic_terms = cur.fetchone()[0]

            cur.execute(
                """
                SELECT
                    count(*) FILTER (WHERE e.edge_type='HAS_ATTRIBUTION') AS has_attribution,
                    count(*) FILTER (WHERE e.edge_type='HAS_FEATURE_CONTEXT') AS has_feature_context,
                    count(*) FILTER (WHERE e.edge_type='HAS_RISK_CONTEXT') AS has_risk_context,
                    count(*) FILTER (WHERE e.edge_type='PRODUCED_FILL') AS produced_fill
                FROM knowledge_graph.edges e
                WHERE e.domain=%s;
                """,
                (DOMAIN,),
            )
            cov = cur.fetchone()
            has_attr, has_feature, has_risk, produced_fill = cov

            cur.execute(
                """
                SELECT count(*)
                FROM knowledge_graph.nodes
                WHERE domain=%s
                  AND entity_type='TradeContextSnapshot';
                """,
                (DOMAIN,),
            )
            snapshots = cur.fetchone()[0]

            payload = {
                "nodes": nodes,
                "edges": edges,
                "snapshots": snapshots,
                "orphan_nodes": orphan_nodes,
                "broken_edges": broken_edges,
                "duplicate_nodes": duplicate_nodes,
                "duplicate_edges": duplicate_edges,
                "missing_i18n": missing_i18n,
                "semantic_terms": semantic_terms,
                "coverage": {
                    "HAS_ATTRIBUTION": has_attr,
                    "HAS_FEATURE_CONTEXT": has_feature,
                    "HAS_RISK_CONTEXT": has_risk,
                    "PRODUCED_FILL": produced_fill,
                },
            }

            cur.execute(
                "SELECT count(*) FROM knowledge_graph.validation_findings WHERE run_id=%s;",
                (run_id,),
            )
            findings = cur.fetchone()[0]

            status = "OK" if broken_edges == 0 and duplicate_nodes == 0 and duplicate_edges == 0 else "FAILED"

            cur.execute(
                """
                UPDATE knowledge_graph.validation_runs
                SET status=%s,
                    finished_at=now(),
                    total_findings=%s,
                    payload=%s
                WHERE run_id=%s;
                """,
                (status, findings, Json(payload), run_id),
            )

            print(f"run_id={run_id}")
            print(f"domain={DOMAIN}")
            print(f"nodes={nodes}")
            print(f"edges={edges}")
            print(f"snapshots={snapshots}")
            print(f"orphan_nodes={orphan_nodes}")
            print(f"broken_edges={broken_edges}")
            print(f"duplicate_nodes={duplicate_nodes}")
            print(f"duplicate_edges={duplicate_edges}")
            print(f"missing_i18n={missing_i18n}")
            print(f"semantic_terms={semantic_terms}")
            print(f"has_attribution={has_attr}")
            print(f"has_feature_context={has_feature}")
            print(f"has_risk_context={has_risk}")
            print(f"produced_fill={produced_fill}")
            print(f"status={status}")
            print("runtime_changed=0")
            print("execution_changed=0")
            print("orders_changed=0")
            print("fills_changed=0")
            print("micro_live_allowed=0")
            print("VERDICT=KNOWLEDGE_GRAPH_VALIDATION_V1_READY")

            if status != "OK":
                raise SystemExit(2)


if __name__ == "__main__":
    main()
