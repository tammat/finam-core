from __future__ import annotations

import os
import time
from typing import Any

import psycopg2
from psycopg2.extras import Json

DB = os.getenv("DATABASE_URL", "postgresql:///finam_core")
DOMAIN = "PAPER_RUNTIME"
ONTOLOGY_VERSION = "FINAM_CORE_EXPLAINABILITY_KG_ONTOLOGY_V1"


def ms(start: float) -> int:
    return int((time.monotonic() - start) * 1000)


def stage(name: str, fn) -> int:
    print(f"BUILD_STAGE={name} status=START", flush=True)
    t0 = time.monotonic()
    rows = fn()
    print(
        f"BUILD_STAGE={name} status=DONE elapsed_ms={ms(t0)} rows_written={rows}",
        flush=True,
    )
    return rows


def main() -> None:
    t_total = time.monotonic()

    with psycopg2.connect(DB) as conn:
        with conn.cursor() as cur:
            print("=== KNOWLEDGE_GRAPH_PAPER_RUNTIME_BUILD_V2 ===", flush=True)

            def cleanup() -> int:
                cur.execute("DELETE FROM knowledge_graph.edges WHERE domain=%s;", (DOMAIN,))
                cur.execute("DELETE FROM knowledge_graph.nodes WHERE domain=%s;", (DOMAIN,))
                return cur.rowcount

            def trade_context_nodes() -> int:
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
                        id::text,
                        NULL,
                        id::text,
                        symbol,
                        strategy,
                        timeframe,
                        trade_source,
                        'FULL',
                        jsonb_build_object(
                            'id', id,
                            'trade_id', trade_id,
                            'db_trade_id', db_trade_id,
                            'ts', ts
                        ),
                        %s
                    FROM public.trade_context_snapshots
                    WHERE trade_source='paper'
                    ON CONFLICT DO NOTHING;
                """, (DOMAIN, ONTOLOGY_VERSION))
                return cur.rowcount

            def json_nodes(entity_type: str, path: str, confidence: str) -> int:
                cur.execute("""
                    INSERT INTO knowledge_graph.nodes (
                        domain, entity_type, source_table, source_pk, source_path,
                        external_id, symbol, strategy, timeframe, trade_source,
                        confidence, payload, ontology_version
                    )
                    SELECT
                        %s,
                        %s,
                        'public.trade_context_snapshots',
                        id::text,
                        %s,
                        id::text || ':' || %s,
                        symbol,
                        strategy,
                        timeframe,
                        trade_source,
                        %s,
                        snapshot #> %s::text[],
                        %s
                    FROM public.trade_context_snapshots
                    WHERE trade_source='paper'
                      AND snapshot #> %s::text[] IS NOT NULL
                      AND snapshot #> %s::text[] <> '{}'::jsonb
                    ON CONFLICT DO NOTHING;
                """, (
                    DOMAIN,
                    entity_type,
                    path,
                    entity_type,
                    confidence,
                    path.split("."),
                    ONTOLOGY_VERSION,
                    path.split("."),
                    path.split("."),
                ))
                return cur.rowcount

            def risk_nodes() -> int:
                cur.execute("""
                    INSERT INTO knowledge_graph.nodes (
                        domain, entity_type, source_table, source_pk, source_path,
                        external_id, symbol, strategy, timeframe, trade_source,
                        confidence, payload, ontology_version
                    )
                    SELECT
                        %s,
                        'RiskContext',
                        'public.trade_risk_context',
                        id::text,
                        NULL,
                        closed_trade_id::text,
                        symbol,
                        strategy,
                        timeframe,
                        trade_source,
                        'FULL',
                        jsonb_build_object(
                            'id', id,
                            'closed_trade_id', closed_trade_id,
                            'heat_status', heat_status,
                            'risk_multiplier', risk_multiplier,
                            'allow_new_entries', allow_new_entries,
                            'governance_mode', governance_mode,
                            'context_quality', context_quality
                        ),
                        %s
                    FROM public.trade_risk_context
                    WHERE trade_source='paper'
                    ON CONFLICT DO NOTHING;
                """, (DOMAIN, ONTOLOGY_VERSION))
                return cur.rowcount

            def signal_quality_nodes() -> int:
                cur.execute("""
                    INSERT INTO knowledge_graph.nodes (
                        domain, entity_type, source_table, source_pk, source_path,
                        external_id, symbol, strategy, timeframe, trade_source,
                        confidence, payload, ontology_version
                    )
                    SELECT
                        %s,
                        'SignalQuality',
                        'public.signal_quality_audit_v1',
                        id::text,
                        NULL,
                        signal_id,
                        symbol,
                        strategy,
                        timeframe,
                        'paper',
                        'FULL',
                        jsonb_build_object(
                            'id', id,
                            'signal_id', signal_id,
                            'filled', filled,
                            'fill_id', fill_id,
                            'trade_id', trade_id,
                            'pnl', pnl,
                            'win', win,
                            'outcome_class', outcome_class,
                            'confidence', confidence,
                            'rr', rr
                        ),
                        %s
                    FROM public.signal_quality_audit_v1
                    WHERE signal_id IS NOT NULL
                    ON CONFLICT DO NOTHING;
                """, (DOMAIN, ONTOLOGY_VERSION))
                return cur.rowcount

            def fill_nodes() -> int:
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
                        NULL,
                        NULL,
                        'paper',
                        'FULL',
                        jsonb_build_object(
                            'fill_id', fill_id,
                            'ts', ts,
                            'side', side,
                            'qty', qty,
                            'price', price,
                            'commission', commission,
                            'order_id', order_id
                        ),
                        %s
                    FROM public.fills
                    WHERE fill_id LIKE 'paper_%%'
                    ON CONFLICT DO NOTHING;
                """, (DOMAIN, ONTOLOGY_VERSION))
                return cur.rowcount

            def closed_trade_nodes() -> int:
                cur.execute("""
                    INSERT INTO knowledge_graph.nodes (
                        domain, entity_type, source_table, source_pk, source_path,
                        external_id, symbol, strategy, timeframe, trade_source,
                        confidence, payload, ontology_version
                    )
                    SELECT
                        %s,
                        'ClosedTrade',
                        'public.closed_trades',
                        id::text,
                        NULL,
                        id::text,
                        symbol,
                        strategy,
                        timeframe,
                        trade_source,
                        'FULL',
                        jsonb_build_object(
                            'id', id,
                            'side', side,
                            'entry_price', entry_price,
                            'exit_price', exit_price,
                            'qty', qty,
                            'gross_pnl', gross_pnl,
                            'net_pnl', net_pnl,
                            'commission', commission,
                            'closed_at', closed_at,
                            'opened_at', opened_at,
                            'quality_score', quality_score
                        ),
                        %s
                    FROM public.closed_trades
                    WHERE trade_source='paper'
                    ON CONFLICT DO NOTHING;
                """, (DOMAIN, ONTOLOGY_VERSION))
                return cur.rowcount

            def edges_same_snapshot(edge_type: str, to_type: str) -> int:
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
                      AND src.entity_type='TradeContextSnapshot'
                    ON CONFLICT DO NOTHING;
                """, (DOMAIN, edge_type, ONTOLOGY_VERSION, to_type, DOMAIN))
                return cur.rowcount

            def edge_snapshot_to_fill() -> int:
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
                        'PARTIAL',
                        'public.trade_context_snapshots',
                        src.source_pk,
                        '{}'::jsonb,
                        %s
                    FROM knowledge_graph.nodes src
                    JOIN public.trade_context_snapshots tcs
                      ON tcs.id::text=src.source_pk
                    JOIN knowledge_graph.nodes dst
                      ON dst.domain=src.domain
                     AND dst.entity_type='Fill'
                     AND dst.external_id=(tcs.snapshot #>> '{attribution,fill_id}')
                    WHERE src.domain=%s
                      AND src.entity_type='TradeContextSnapshot'
                      AND tcs.trade_source='paper'
                      AND tcs.snapshot #>> '{attribution,fill_id}' IS NOT NULL
                    ON CONFLICT DO NOTHING;
                """, (DOMAIN, ONTOLOGY_VERSION, DOMAIN))
                return cur.rowcount

            def edge_snapshot_to_risk() -> int:
                cur.execute("""
                    INSERT INTO knowledge_graph.edges (
                        domain, from_node_id, to_node_id, edge_type,
                        confidence, source_table, source_pk, payload, ontology_version
                    )
                    SELECT
                        %s,
                        src.node_id,
                        dst.node_id,
                        'HAS_RISK_CONTEXT',
                        'PARTIAL',
                        'public.trade_context_snapshots',
                        src.source_pk,
                        '{}'::jsonb,
                        %s
                    FROM knowledge_graph.nodes src
                    JOIN public.trade_context_snapshots tcs
                      ON tcs.id::text=src.source_pk
                    JOIN knowledge_graph.nodes dst
                      ON dst.domain=src.domain
                     AND dst.entity_type='RiskContext'
                     AND dst.external_id=tcs.db_trade_id::text
                    WHERE src.domain=%s
                      AND src.entity_type='TradeContextSnapshot'
                      AND tcs.trade_source='paper'
                      AND tcs.db_trade_id IS NOT NULL
                    ON CONFLICT DO NOTHING;
                """, (DOMAIN, ONTOLOGY_VERSION, DOMAIN))
                return cur.rowcount

            def validation() -> int:
                cur.execute("SELECT count(*) FROM knowledge_graph.nodes WHERE domain=%s;", (DOMAIN,))
                nodes = cur.fetchone()[0]
                cur.execute("SELECT count(*) FROM knowledge_graph.edges WHERE domain=%s;", (DOMAIN,))
                edges = cur.fetchone()[0]
                print(f"domain={DOMAIN}", flush=True)
                print(f"nodes={nodes}", flush=True)
                print(f"edges={edges}", flush=True)
                if nodes <= 0:
                    raise RuntimeError("KG nodes not built")
                return nodes + edges

            stage("00_CLEANUP", cleanup)
            stage("10_TRADE_CONTEXT_SNAPSHOT_NODES", trade_context_nodes)
            stage("20_ATTRIBUTION_NODES", lambda: json_nodes("Attribution", "attribution", "FULL"))
            stage("30_EDGE_GATE_NODES", lambda: json_nodes("EdgeGate", "attribution.trade_context_snapshot.edge_gate", "PARTIAL"))
            stage("40_FEATURE_CONTEXT_NODES", lambda: json_nodes("FeatureContext", "feature_context", "PARTIAL"))
            stage("50_EXIT_POLICY_CONTEXT_NODES", lambda: json_nodes("ExitPolicyContext", "exit_policy_context", "PARTIAL"))
            stage("60_RISK_CONTEXT_NODES", risk_nodes)
            stage("70_SIGNAL_QUALITY_NODES", signal_quality_nodes)
            stage("80_FILL_NODES", fill_nodes)
            stage("90_CLOSED_TRADE_NODES", closed_trade_nodes)

            stage("100_EDGE_HAS_ATTRIBUTION", lambda: edges_same_snapshot("HAS_ATTRIBUTION", "Attribution"))
            stage("110_EDGE_HAS_EDGE_GATE", lambda: edges_same_snapshot("HAS_EDGE_GATE", "EdgeGate"))
            stage("120_EDGE_HAS_FEATURE_CONTEXT", lambda: edges_same_snapshot("HAS_FEATURE_CONTEXT", "FeatureContext"))
            stage("130_EDGE_HAS_EXIT_POLICY", lambda: edges_same_snapshot("HAS_EXIT_POLICY", "ExitPolicyContext"))
            stage("140_EDGE_PRODUCED_FILL", edge_snapshot_to_fill)
            stage("150_EDGE_HAS_RISK_CONTEXT", edge_snapshot_to_risk)
            stage("160_VALIDATION", validation)

            print(f"total_elapsed_ms={ms(t_total)}", flush=True)
            print("runtime_changed=0")
            print("execution_changed=0")
            print("orders_changed=0")
            print("fills_changed=0")
            print("micro_live_allowed=0")
            print("VERDICT=KNOWLEDGE_GRAPH_PAPER_RUNTIME_BUILD_V2_READY")


if __name__ == "__main__":
    main()
