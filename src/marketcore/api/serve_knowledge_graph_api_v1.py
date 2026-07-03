from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import parse_qs, urlparse

import psycopg2
import psycopg2.extras

DB = os.getenv("DATABASE_URL", "postgresql:///finam_core")
HOST = os.getenv("KG_API_HOST", "127.0.0.1")
PORT = int(os.getenv("KG_API_PORT", "8095"))
API_VERSION = "v1"


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def response(status: str, data, metadata=None):
    return {
        "api_version": API_VERSION,
        "timestamp": now_iso(),
        "status": status,
        "data": data,
        "metadata": metadata or {},
    }


def fetch_all(sql: str, params=()):
    with psycopg2.connect(DB) as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(sql, params)
            return [dict(r) for r in cur.fetchall()]


def fetch_one(sql: str, params=()):
    rows = fetch_all(sql, params)
    return rows[0] if rows else None


class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        return

    def send_json(self, code: int, payload):
        raw = json.dumps(payload, ensure_ascii=False, default=str).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def do_GET(self):
        parsed = urlparse(self.path)
        q = parse_qs(parsed.query)
        path = parsed.path

        try:
            if path == "/api/kg/v1/health":
                data = fetch_one("SELECT count(*) AS nodes FROM knowledge_graph.v_api_kg_entity_summary_v1;")
                self.send_json(200, response("OK", {"service": "knowledge_graph_api_v1", **data}))
                return

            if path == "/api/kg/v1/statistics":
                rows = fetch_all("SELECT * FROM knowledge_graph.v_api_kg_statistics_v1 ORDER BY domain;")
                self.send_json(200, response("OK", rows))
                return

            if path == "/api/kg/v1/entity":
                node_id = q.get("node_id", [None])[0]
                source_pk = q.get("source_pk", [None])[0]
                entity_type = q.get("entity_type", [None])[0]
                domain = q.get("domain", ["PAPER_RUNTIME"])[0]

                if node_id:
                    entity = fetch_one(
                        "SELECT * FROM knowledge_graph.v_api_kg_entity_summary_v1 WHERE node_id=%s;",
                        (node_id,),
                    )
                elif source_pk and entity_type:
                    entity = fetch_one(
                        """
                        SELECT * FROM knowledge_graph.v_api_kg_entity_summary_v1
                        WHERE domain=%s AND source_pk=%s AND entity_type=%s
                        ORDER BY node_id DESC LIMIT 1;
                        """,
                        (domain, source_pk, entity_type),
                    )
                else:
                    self.send_json(400, response("ERROR", {}, {"error": "node_id or source_pk+entity_type required"}))
                    return

                if not entity:
                    self.send_json(404, response("NOT_FOUND", {}))
                    return

                relations = fetch_all(
                    """
                    SELECT *
                    FROM knowledge_graph.v_api_kg_relation_summary_v1
                    WHERE from_node_id=%s OR to_node_id=%s
                    ORDER BY edge_id
                    LIMIT 100;
                    """,
                    (entity["node_id"], entity["node_id"]),
                )
                self.send_json(200, response("OK", {"entity": entity, "relations": relations}))
                return

            if path == "/api/kg/v1/relations":
                node_id = q.get("node_id", [None])[0]
                edge_type = q.get("edge_type", [None])[0]
                if not node_id:
                    self.send_json(400, response("ERROR", {}, {"error": "node_id required"}))
                    return

                if edge_type:
                    rows = fetch_all(
                        """
                        SELECT * FROM knowledge_graph.v_api_kg_relation_summary_v1
                        WHERE (from_node_id=%s OR to_node_id=%s) AND edge_type=%s
                        ORDER BY edge_id LIMIT 200;
                        """,
                        (node_id, node_id, edge_type),
                    )
                else:
                    rows = fetch_all(
                        """
                        SELECT * FROM knowledge_graph.v_api_kg_relation_summary_v1
                        WHERE from_node_id=%s OR to_node_id=%s
                        ORDER BY edge_id LIMIT 200;
                        """,
                        (node_id, node_id),
                    )
                self.send_json(200, response("OK", rows))
                return

            if path == "/api/kg/v1/search":
                text = (q.get("q", [""])[0] or "").strip().lower()
                locale = q.get("locale", ["ru"])[0]
                if not text:
                    self.send_json(400, response("ERROR", {}, {"error": "q required"}))
                    return

                terms = fetch_all(
                    """
                    SELECT *
                    FROM knowledge_graph.v_api_kg_semantic_search_v1
                    WHERE locale=%s
                      AND (%s ILIKE '%%' || normalized_term || '%%'
                           OR normalized_term ILIKE '%%' || %s || '%%')
                    ORDER BY confidence DESC
                    LIMIT 20;
                    """,
                    (locale, text, text),
                )
                self.send_json(200, response("OK", {"query": text, "locale": locale, "terms": terms}))
                return

            if path == "/api/kg/v1/validation":
                rows = fetch_all("SELECT * FROM knowledge_graph.v_api_kg_validation_latest_v1 ORDER BY domain;")
                self.send_json(200, response("OK", rows))
                return

            if path == "/api/kg/v1/ontology":
                labels = fetch_all(
                    """
                    SELECT object_type, object_key, locale, label, short_label, description, ontology_version
                    FROM knowledge_graph.i18n_labels
                    ORDER BY object_type, object_key, locale;
                    """
                )
                self.send_json(200, response("OK", labels))
                return


            if path == "/api/kg/v1/paper-runtime":
                row = fetch_one("""
                    SELECT
                        paper_status,
                        closed_trades_total,
                        closed_trades_today,
                        signals_today,
                        fills_today,
                        signal_fills_today,
                        active_symbols,
                        pnl_today,
                        pnl_total,
                        last_closed_trade_at,
                        refreshed_at,
                        source_version
                    FROM marketcore_ui.paper_runtime_summary_v1
                    WHERE id=1;
                """)
                self.send_json(200, response("OK", row or {}, {"source": "marketcore_ui.paper_runtime_summary_v1"}))
                return

            if path == "/api/kg/v1/paper-edge-discovery":
                paper = fetch_one("""
                    SELECT
                        paper_status,
                        closed_trades_total,
                        closed_trades_today,
                        signals_today,
                        fills_today,
                        signal_fills_today,
                        active_symbols,
                        pnl_today,
                        pnl_total,
                        last_closed_trade_at,
                        refreshed_at,
                        source_version
                    FROM marketcore_ui.paper_runtime_summary_v1
                    WHERE id=1;
                """) or {}

                kg = fetch_one("""
                    SELECT domain, nodes, edges, entity_types, edge_types, last_node_update
                    FROM knowledge_graph.v_api_kg_statistics_v1
                    WHERE domain='PAPER_RUNTIME';
                """) or {}

                validation = fetch_one("""
                    SELECT domain, status, total_findings, finished_at
                    FROM knowledge_graph.v_api_kg_validation_latest_v1
                    WHERE domain='PAPER_RUNTIME';
                """) or {}

                data = {
                    "paper_runtime": paper,
                    "knowledge_graph": kg,
                    "validation": validation,
                    "next_action": "PAPER_EDGE_DISCOVERY_RESEARCH_CANDIDATES_V1",
                }

                self.send_json(200, response("OK", data, {
                    "source": "kg_api_read_models",
                    "ui_direct_sql": 0,
                }))
                return


            if path == "/api/kg/v1/paper-edge-research-candidates":
                limit = int(q.get("limit", ["20"])[0])
                rows = fetch_all("""
                    SELECT
                        candidate_rank,
                        symbol,
                        strategy,
                        timeframe,
                        side,
                        candidate_status,
                        expectancy,
                        profit_factor,
                        winrate,
                        trades,
                        net_pnl,
                        score,
                        source_table,
                        refreshed_at
                    FROM marketcore_ui.paper_edge_research_candidates_v1
                    ORDER BY candidate_rank
                    LIMIT %s;
                """, (limit,))
                self.send_json(200, response("OK", rows, {
                    "source": "marketcore_ui.paper_edge_research_candidates_v1",
                    "ui_direct_sql": 0
                }))
                return


            if path == "/api/kg/v1/paper-edge-top-candidates-detail":
                limit = int(q.get("limit", ["10"])[0])
                rows = fetch_all("""
                    SELECT
                        candidate_rank,
                        symbol,
                        strategy,
                        timeframe,
                        side,
                        candidate_status,
                        expectancy,
                        profit_factor,
                        winrate,
                        trades,
                        net_pnl,
                        score,
                        source_table,
                        refreshed_at,
                        CASE
                            WHEN COALESCE(trades,0) < 30 THEN 'LOW_SAMPLE'
                            WHEN COALESCE(profit_factor,0) >= 1.2
                             AND COALESCE(expectancy,0) > 0 THEN 'REVIEW_READY'
                            WHEN COALESCE(profit_factor,0) >= 1.0
                             AND COALESCE(expectancy,0) >= 0 THEN 'OBSERVE'
                            ELSE 'REJECT_REVIEW'
                        END AS detail_status,
                        CASE
                            WHEN COALESCE(trades,0) < 30 THEN 'Накопить выборку Paper Runtime'
                            WHEN COALESCE(profit_factor,0) >= 1.2
                             AND COALESCE(expectancy,0) > 0 THEN 'Передать в Edge Validation'
                            WHEN COALESCE(profit_factor,0) >= 1.0
                             AND COALESCE(expectancy,0) >= 0 THEN 'Наблюдать и проверить устойчивость'
                            ELSE 'Не продвигать без дополнительного анализа'
                        END AS next_step
                    FROM marketcore_ui.paper_edge_research_candidates_v1
                    ORDER BY candidate_rank
                    LIMIT %s;
                """, (limit,))
                self.send_json(200, response("OK", rows, {
                    "source": "marketcore_ui.paper_edge_research_candidates_v1",
                    "ui_direct_sql": 0,
                    "logic": "paper_edge_top_candidates_detail_v1"
                }))
                return


            if path == "/api/kg/v1/paper-edge-candidate-explainability":
                limit = int(q.get("limit", ["10"])[0])
                rows = fetch_all("""
                    SELECT
                        candidate_rank,
                        symbol,
                        strategy,
                        timeframe,
                        side,
                        candidate_status,
                        expectancy,
                        profit_factor,
                        winrate,
                        trades,
                        net_pnl,
                        score,
                        source_table,
                        refreshed_at,

                        CASE
                            WHEN COALESCE(trades,0) < 30 THEN 'LOW_SAMPLE'
                            WHEN COALESCE(profit_factor,0) >= 1.2
                             AND COALESCE(expectancy,0) > 0 THEN 'REVIEW_READY'
                            WHEN COALESCE(profit_factor,0) >= 1.0
                             AND COALESCE(expectancy,0) >= 0 THEN 'OBSERVE'
                            ELSE 'REJECT_REVIEW'
                        END AS explainability_status,

                        CASE
                            WHEN COALESCE(trades,0) < 30 THEN
                                'Кандидат найден, но выборка недостаточна для вывода об устойчивом преимуществе.'
                            WHEN COALESCE(profit_factor,0) >= 1.2
                             AND COALESCE(expectancy,0) > 0 THEN
                                'Кандидат имеет положительное матожидание и Profit Factor выше минимального порога.'
                            WHEN COALESCE(profit_factor,0) >= 1.0
                             AND COALESCE(expectancy,0) >= 0 THEN
                                'Кандидат не показывает явного отрицательного результата, но требует дополнительного наблюдения.'
                            ELSE
                                'Текущая статистика не подтверждает преимущество для продвижения.'
                        END AS why_selected,

                        CASE
                            WHEN COALESCE(trades,0) < 30 THEN
                                'Главный риск: малая выборка. Требуется накопить больше Paper-сделок.'
                            WHEN COALESCE(winrate,0) < 0.45 THEN
                                'Главный риск: низкая доля прибыльных сделок, требуется анализ распределения убытков.'
                            WHEN COALESCE(profit_factor,0) < 1.0 THEN
                                'Главный риск: Profit Factor ниже единицы.'
                            ELSE
                                'Ключевые риски: устойчивость по времени, режимам рынка и out-of-sample проверка.'
                        END AS risk_explanation,

                        concat(
                            'Trades=', COALESCE(trades,0),
                            '; PF=', COALESCE(round(profit_factor::numeric,4),0),
                            '; Expectancy=', COALESCE(round(expectancy::numeric,4),0),
                            '; WinRate=', COALESCE(round(winrate::numeric,4),0),
                            '; NetPnL=', COALESCE(round(net_pnl::numeric,4),0)
                        ) AS evidence_summary,

                        CASE
                            WHEN COALESCE(trades,0) < 30 THEN 'ACCUMULATE_SAMPLE'
                            WHEN COALESCE(profit_factor,0) >= 1.2
                             AND COALESCE(expectancy,0) > 0 THEN 'SEND_TO_EDGE_VALIDATION'
                            WHEN COALESCE(profit_factor,0) >= 1.0
                             AND COALESCE(expectancy,0) >= 0 THEN 'OBSERVE_MORE'
                            ELSE 'DO_NOT_PROMOTE'
                        END AS recommended_action

                    FROM marketcore_ui.paper_edge_research_candidates_v1
                    ORDER BY candidate_rank
                    LIMIT %s;
                """, (limit,))
                self.send_json(200, response("OK", rows, {
                    "source": "marketcore_ui.paper_edge_research_candidates_v1",
                    "ui_direct_sql": 0,
                    "logic": "paper_edge_candidate_explainability_v1"
                }))
                return


            if path == "/api/kg/v1/edge-validation-queue":
                limit = int(q.get("limit", ["50"])[0])
                rows = fetch_all("""
                    SELECT
                        queue_rank,
                        symbol,
                        strategy,
                        timeframe,
                        side,
                        candidate_status,
                        validation_status,
                        priority,
                        expectancy,
                        profit_factor,
                        winrate,
                        trades,
                        net_pnl,
                        score,
                        evidence_summary,
                        risk_notes,
                        recommended_action,
                        source_candidate_rank,
                        source_table,
                        refreshed_at
                    FROM marketcore_ui.edge_validation_queue_v1
                    ORDER BY queue_rank
                    LIMIT %s;
                """, (limit,))
                self.send_json(200, response("OK", rows, {
                    "source": "marketcore_ui.edge_validation_queue_v1",
                    "ui_direct_sql": 0,
                    "logic": "edge_validation_queue_v1"
                }))
                return


            if path == "/api/kg/v1/edge-validation-pipeline":
                limit = int(q.get("limit", ["50"])[0])
                rows = fetch_all("""
                    SELECT
                        pipeline_rank,
                        symbol,
                        strategy,
                        timeframe,
                        side,
                        queue_status,
                        priority,
                        sample_check_status,
                        pf_check_status,
                        expectancy_check_status,
                        robustness_status,
                        oos_status,
                        pipeline_status,
                        recommended_action,
                        expectancy,
                        profit_factor,
                        winrate,
                        trades,
                        net_pnl,
                        score,
                        evidence_summary,
                        risk_notes,
                        source_queue_rank,
                        refreshed_at
                    FROM marketcore_ui.edge_validation_pipeline_v1
                    ORDER BY pipeline_rank
                    LIMIT %s;
                """, (limit,))
                self.send_json(200, response("OK", rows, {
                    "source": "marketcore_ui.edge_validation_pipeline_v1",
                    "ui_direct_sql": 0,
                    "logic": "edge_validation_pipeline_v1"
                }))
                return


            if path == "/api/kg/v1/edge-robustness-check":
                limit = int(q.get("limit", ["50"])[0])
                rows = fetch_all("""
                    SELECT
                        robustness_rank,
                        symbol,
                        strategy,
                        timeframe,
                        side,
                        pipeline_status,
                        robustness_status,
                        sample_size_status,
                        pf_status,
                        expectancy_status,
                        winrate_status,
                        pnl_status,
                        robustness_score,
                        oos_required,
                        micro_live_ready,
                        expectancy,
                        profit_factor,
                        winrate,
                        trades,
                        net_pnl,
                        score,
                        evidence_summary,
                        weakness_summary,
                        recommended_action,
                        source_pipeline_rank,
                        refreshed_at
                    FROM marketcore_ui.edge_robustness_check_v1
                    ORDER BY robustness_rank
                    LIMIT %s;
                """, (limit,))
                self.send_json(200, response("OK", rows, {
                    "source": "marketcore_ui.edge_robustness_check_v1",
                    "ui_direct_sql": 0,
                    "logic": "edge_robustness_check_v1"
                }))
                return

            self.send_json(404, response("NOT_FOUND", {}, {"path": path}))

        except Exception as exc:
            self.send_json(500, response("ERROR", {}, {"error": type(exc).__name__, "message": str(exc)}))


def main():
    print(f"KNOWLEDGE_GRAPH_API_V1_START host={HOST} port={PORT}", flush=True)
    HTTPServer((HOST, PORT), Handler).serve_forever()


if __name__ == "__main__":
    main()
