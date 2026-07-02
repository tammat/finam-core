from __future__ import annotations

import os
import psycopg2

DB = os.getenv("DATABASE_URL", "postgresql:///finam_core")
DOMAIN = "PAPER_RUNTIME"
ONTOLOGY_VERSION = "FINAM_CORE_EXPLAINABILITY_KG_ONTOLOGY_V1"

def main() -> None:
    with psycopg2.connect(DB) as conn:
        with conn.cursor() as cur:
            print("=== KNOWLEDGE_GRAPH_PAPER_RUNTIME_BUILD_V1 ===")

            cur.execute("DELETE FROM knowledge_graph.edges WHERE domain=%s;", (DOMAIN,))
            cur.execute("DELETE FROM knowledge_graph.nodes WHERE domain=%s;", (DOMAIN,))

            cur.execute("""
                INSERT INTO knowledge_graph.nodes (
                    domain, entity_type, source_table, source_pk, source_path,
                    external_id, symbol, strategy, timeframe, trade_source,
                    confidence, payload, ontology_version
                )
                SELECT
                    %s,
                    'TradeContextSnapshot',
                    'public.trade_context_snapshots',
                    snapshot_id::text,
                    NULL,
                    snapshot_id::text,
                    symbol,
                    strategy,
                    timeframe,
                    trade_source,
                    'FULL',
                    jsonb_build_object(
                        'snapshot_id', snapshot_id,
                        'trade_id', trade_id,
                        'db_trade_id', db_trade_id,
                        'runtime_trade_id', runtime_trade_id,
                        'ts', ts
                    ),
                    %s
                FROM marketcore_ui.paper_runtime_explainability_v1;
            """, (DOMAIN, ONTOLOGY_VERSION))

            for entity_type, source_path, payload_col, confidence in [
                ("Attribution", "{attribution}", "attribution", "FULL"),
                ("EdgeGate", "{edge_gate}", "edge_gate", "PARTIAL"),
                ("RiskContext", "{risk_context}", "risk_context", "PARTIAL"),
                ("FeatureContext", "{feature_context}", "feature_context", "PARTIAL"),
                ("ExitPolicyContext", "{exit_policy_context}", "exit_policy_context", "PARTIAL"),
                ("Explanation", "{explainability}", "explainability", "PARTIAL"),
            ]:
                cur.execute(f"""
                    INSERT INTO knowledge_graph.nodes (
                        domain, entity_type, source_table, source_pk, source_path,
                        external_id, symbol, strategy, timeframe, trade_source,
                        confidence, payload, ontology_version
                    )
                    SELECT
                        %s,
                        %s,
                        'marketcore_ui.paper_runtime_explainability_v1',
                        snapshot_id::text,
                        %s,
                        snapshot_id::text || ':' || %s,
                        symbol,
                        strategy,
                        timeframe,
                        trade_source,
                        %s,
                        COALESCE({payload_col}, '{{}}'::jsonb),
                        %s
                    FROM marketcore_ui.paper_runtime_explainability_v1
                    WHERE {payload_col} IS NOT NULL
                      AND {payload_col} <> '{{}}'::jsonb;
                """, (DOMAIN, entity_type, source_path, entity_type, confidence, ONTOLOGY_VERSION))

            cur.execute("""
                INSERT INTO knowledge_graph.nodes (
                    domain, entity_type, source_table, source_pk, source_path,
                    external_id, symbol, strategy, timeframe, trade_source,
                    confidence, payload, ontology_version
                )
                SELECT
                    %s,
                    'Fill',
                    'public.fills',
                    fill_id,
                    NULL,
                    fill_id,
                    symbol,
                    strategy,
                    timeframe,
                    trade_source,
                    'FULL',
                    jsonb_build_object(
                        'fill_id', fill_id,
                        'fill_price', fill_price,
                        'fill_qty', fill_qty,
                        'fill_commission', fill_commission
                    ),
                    %s
                FROM marketcore_ui.paper_runtime_explainability_v1
                WHERE fill_id IS NOT NULL
                GROUP BY fill_id, symbol, strategy, timeframe, trade_source, fill_price, fill_qty, fill_commission;
            """, (DOMAIN, ONTOLOGY_VERSION))

            edge_specs = [
                ("HAS_ATTRIBUTION", "TradeContextSnapshot", "Attribution"),
                ("HAS_EDGE_GATE", "TradeContextSnapshot", "EdgeGate"),
                ("HAS_RISK_CONTEXT", "TradeContextSnapshot", "RiskContext"),
                ("HAS_FEATURE_CONTEXT", "TradeContextSnapshot", "FeatureContext"),
                ("HAS_EXIT_POLICY", "TradeContextSnapshot", "ExitPolicyContext"),
                ("EXPLAINED_BY", "TradeContextSnapshot", "Explanation"),
            ]

            for edge_type, from_type, to_type in edge_specs:
                cur.execute("""
                    INSERT INTO knowledge_graph.edges (
                        domain, from_node_id, to_node_id, edge_type,
                        confidence, source_table, source_pk, payload, ontology_version
                    )
                    SELECT
                        %s,
                        src.node_id,
                        dst.node_id,
                        %s,
                        dst.confidence,
                        dst.source_table,
                        dst.source_pk,
                        '{}'::jsonb,
                        %s
                    FROM knowledge_graph.nodes src
                    JOIN knowledge_graph.nodes dst
                      ON dst.domain=src.domain
                     AND dst.source_pk=src.source_pk
                     AND dst.entity_type=%s
                    WHERE src.domain=%s
                      AND src.entity_type=%s
                    ON CONFLICT DO NOTHING;
                """, (DOMAIN, edge_type, ONTOLOGY_VERSION, to_type, DOMAIN, from_type))

            cur.execute("""
                INSERT INTO knowledge_graph.edges (
                    domain, from_node_id, to_node_id, edge_type,
                    confidence, source_table, source_pk, payload, ontology_version
                )
                SELECT
                    %s,
                    src.node_id,
                    dst.node_id,
                    'PRODUCED_FILL',
                    'FULL',
                    'marketcore_ui.paper_runtime_explainability_v1',
                    src.source_pk,
                    '{}'::jsonb,
                    %s
                FROM knowledge_graph.nodes src
                JOIN marketcore_ui.paper_runtime_explainability_v1 v
                  ON v.snapshot_id::text=src.source_pk
                JOIN knowledge_graph.nodes dst
                  ON dst.domain=src.domain
                 AND dst.entity_type='Fill'
                 AND dst.external_id=v.fill_id
                WHERE src.domain=%s
                  AND src.entity_type='TradeContextSnapshot'
                  AND v.fill_id IS NOT NULL
                ON CONFLICT DO NOTHING;
            """, (DOMAIN, ONTOLOGY_VERSION, DOMAIN))

            cur.execute("SELECT count(*) FROM knowledge_graph.nodes WHERE domain=%s;", (DOMAIN,))
            nodes = cur.fetchone()[0]

            cur.execute("SELECT count(*) FROM knowledge_graph.edges WHERE domain=%s;", (DOMAIN,))
            edges = cur.fetchone()[0]

            print(f"domain={DOMAIN}")
            print(f"nodes={nodes}")
            print(f"edges={edges}")
            print("runtime_changed=0")
            print("execution_changed=0")
            print("orders_changed=0")
            print("fills_changed=0")
            print("micro_live_allowed=0")
            print("VERDICT=KNOWLEDGE_GRAPH_PAPER_RUNTIME_BUILD_V1_READY")

if __name__ == "__main__":
    main()
