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


            if path == "/api/kg/v1/edge-oos-validation":
                limit = int(q.get("limit", ["50"])[0])
                rows = fetch_all("""
                    SELECT
                        oos_rank,
                        symbol,
                        strategy,
                        timeframe,
                        side,
                        robustness_status,
                        oos_status,
                        oos_readiness,
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
                        oos_reason,
                        recommended_action,
                        source_robustness_rank,
                        refreshed_at
                    FROM marketcore_ui.edge_oos_validation_v1
                    ORDER BY oos_rank
                    LIMIT %s;
                """, (limit,))
                self.send_json(200, response("OK", rows, {
                    "source": "marketcore_ui.edge_oos_validation_v1",
                    "ui_direct_sql": 0,
                    "logic": "edge_oos_validation_v1"
                }))
                return


            if path == "/api/kg/v1/edge-oos-backtest":
                limit = int(q.get("limit", ["50"])[0])
                rows = fetch_all("""
                    SELECT
                        backtest_rank,
                        symbol,
                        strategy,
                        timeframe,
                        side,
                        robustness_status,
                        oos_status,
                        oos_readiness,
                        backtest_status,
                        total_trades,
                        in_sample_trades,
                        oos_trades,
                        in_sample_pnl,
                        oos_pnl,
                        in_sample_expectancy,
                        oos_expectancy,
                        in_sample_profit_factor,
                        oos_profit_factor,
                        in_sample_winrate,
                        oos_winrate,
                        stability_score,
                        micro_live_candidate,
                        pass_reason,
                        fail_reason,
                        recommended_action,
                        source_oos_rank,
                        refreshed_at
                    FROM marketcore_ui.edge_oos_backtest_v1
                    ORDER BY backtest_rank
                    LIMIT %s;
                """, (limit,))
                self.send_json(200, response("OK", rows, {
                    "source": "marketcore_ui.edge_oos_backtest_v1",
                    "ui_direct_sql": 0,
                    "logic": "edge_oos_backtest_v1"
                }))
                return


            if path == "/api/kg/v1/micro-live-readiness":
                limit = int(q.get("limit", ["50"])[0])
                rows = fetch_all("""
                    SELECT
                        readiness_rank,
                        symbol,
                        strategy,
                        timeframe,
                        side,
                        backtest_status,
                        oos_status,
                        robustness_status,
                        readiness_status,
                        micro_live_ready,
                        micro_live_allowed,
                        total_trades,
                        in_sample_trades,
                        oos_trades,
                        in_sample_pnl,
                        oos_pnl,
                        in_sample_expectancy,
                        oos_expectancy,
                        in_sample_profit_factor,
                        oos_profit_factor,
                        in_sample_winrate,
                        oos_winrate,
                        stability_score,
                        block_reason,
                        evidence_summary,
                        recommended_action,
                        source_backtest_rank,
                        refreshed_at
                    FROM marketcore_ui.micro_live_readiness_v1
                    ORDER BY readiness_rank
                    LIMIT %s;
                """, (limit,))
                self.send_json(200, response("OK", rows, {
                    "source": "marketcore_ui.micro_live_readiness_v1",
                    "ui_direct_sql": 0,
                    "logic": "micro_live_readiness_v1",
                    "orders_changed": 0,
                    "execution_changed": 0
                }))
                return


            if path == "/api/kg/v1/paper-sample-accumulation-monitor":
                limit = int(q.get("limit", ["50"])[0])
                rows = fetch_all("""
                    SELECT
                        monitor_rank,
                        symbol,
                        strategy,
                        timeframe,
                        side,
                        readiness_status,
                        backtest_status,
                        oos_status,
                        robustness_status,
                        total_trades,
                        required_total_trades,
                        remaining_total_trades,
                        oos_trades,
                        required_oos_trades,
                        remaining_oos_trades,
                        sample_status,
                        progress_pct,
                        micro_live_ready,
                        micro_live_allowed,
                        block_reason,
                        recommended_action,
                        source_readiness_rank,
                        refreshed_at
                    FROM marketcore_ui.paper_sample_accumulation_monitor_v1
                    ORDER BY monitor_rank
                    LIMIT %s;
                """, (limit,))
                self.send_json(200, response("OK", rows, {
                    "source": "marketcore_ui.paper_sample_accumulation_monitor_v1",
                    "ui_direct_sql": 0,
                    "logic": "paper_sample_accumulation_monitor_v1",
                    "orders_changed": 0,
                    "execution_changed": 0
                }))
                return


            if path == "/api/kg/v1/paper-runtime-sample-collection":
                row = fetch_one("""
                    SELECT
                        candidates_total,
                        sample_ready,
                        wait_both_sample,
                        wait_total_sample,
                        wait_oos_sample,
                        min_remaining_total_trades,
                        min_remaining_oos_trades,
                        avg_progress_pct,
                        max_progress_pct,
                        collection_status,
                        phase_status,
                        recommended_action,
                        micro_live_allowed,
                        refreshed_at,
                        source_version
                    FROM marketcore_ui.paper_runtime_sample_collection_v1
                    WHERE id=1;
                """)
                self.send_json(200, response("OK", row or {}, {
                    "source": "marketcore_ui.paper_runtime_sample_collection_v1",
                    "ui_direct_sql": 0,
                    "logic": "paper_runtime_sample_collection_dashboard_link_v1"
                }))
                return


            if path == "/api/kg/v1/paper-sample-collection-timer-health":
                row = fetch_one("""
                    SELECT
                        timer_unit,
                        service_unit,
                        timer_active_state,
                        timer_sub_state,
                        timer_unit_file_state,
                        timer_next_elapse,
                        timer_last_trigger,
                        timer_healthy,
                        service_active_state,
                        service_sub_state,
                        service_result,
                        service_exec_main_status,
                        service_last_exit,
                        service_healthy,
                        sample_summary_exists,
                        sample_summary_refreshed_at,
                        sample_summary_age_sec,
                        sample_summary_stale,
                        candidates_total,
                        sample_ready,
                        collection_status,
                        phase_status,
                        micro_live_allowed,
                        timer_health_status,
                        health_reason,
                        recommended_action,
                        refreshed_at,
                        source_version
                    FROM marketcore_ui.paper_runtime_sample_collection_timer_health_v1
                    WHERE id=1;
                """)
                self.send_json(200, response("OK", row or {}, {
                    "source": "marketcore_ui.paper_runtime_sample_collection_timer_health_v1",
                    "ui_direct_sql": 0,
                    "logic": "paper_runtime_sample_collection_timer_health_v1"
                }))
                return


            if path == "/api/kg/v1/paper-runtime-sample-collection-phase-close":
                row = fetch_one("""
                    SELECT
                        phase_name,
                        engineering_status,
                        operational_status,
                        candidates_total,
                        sample_ready,
                        wait_both_sample,
                        wait_total_sample,
                        wait_oos_sample,
                        min_remaining_total_trades,
                        min_remaining_oos_trades,
                        avg_progress_pct,
                        max_progress_pct,
                        collection_status,
                        collection_phase_status,
                        timer_health_status,
                        timer_healthy,
                        service_healthy,
                        sample_summary_stale,
                        sample_summary_age_sec,
                        micro_live_ready_rows,
                        micro_live_allowed_rows,
                        micro_live_allowed,
                        close_status,
                        close_reason,
                        recommended_action,
                        next_phase,
                        refreshed_at,
                        source_version
                    FROM marketcore_ui.paper_runtime_sample_collection_phase_close_v1
                    WHERE id=1;
                """)
                self.send_json(200, response("OK", row or {}, {
                    "source": "marketcore_ui.paper_runtime_sample_collection_phase_close_v1",
                    "ui_direct_sql": 0,
                    "logic": "paper_runtime_sample_collection_phase_close_v1"
                }))
                return


            if path == "/api/kg/v1/phase-ii-paper-edge-discovery-summary":
                row = fetch_one("""
                    SELECT
                        phase_name,
                        phase_result_status,
                        engineering_status,
                        operational_status,
                        close_status,
                        timer_health_status,
                        collection_status,
                        collection_phase_status,
                        candidates_total,
                        sample_ready,
                        wait_both_sample,
                        wait_total_sample,
                        wait_oos_sample,
                        min_remaining_total_trades,
                        min_remaining_oos_trades,
                        avg_progress_pct,
                        max_progress_pct,
                        paper_candidates_rows,
                        validation_queue_rows,
                        validation_pipeline_rows,
                        robustness_rows,
                        oos_validation_rows,
                        oos_backtest_rows,
                        micro_live_readiness_rows,
                        sample_monitor_rows,
                        micro_live_ready_rows,
                        micro_live_allowed_rows,
                        micro_live_allowed,
                        conclusion,
                        recommended_action,
                        next_phase,
                        refreshed_at,
                        source_version
                    FROM marketcore_ui.phase_ii_paper_edge_discovery_summary_v1
                    WHERE id=1;
                """)
                self.send_json(200, response("OK", row or {}, {
                    "source": "marketcore_ui.phase_ii_paper_edge_discovery_summary_v1",
                    "ui_direct_sql": 0,
                    "logic": "phase_ii_paper_edge_discovery_summary_v1"
                }))
                return


            if path == "/api/kg/v1/paper-runtime-sample-collection-operations":
                limit = int(q.get("limit", ["50"])[0])
                rows = fetch_all("""
                    SELECT
                        operation_rank,
                        symbol,
                        strategy,
                        timeframe,
                        side,
                        sample_status,
                        readiness_status,
                        backtest_status,
                        oos_status,
                        robustness_status,
                        total_trades,
                        required_total_trades,
                        remaining_total_trades,
                        oos_trades,
                        required_oos_trades,
                        remaining_oos_trades,
                        progress_pct,
                        operation_priority,
                        operation_status,
                        operation_reason,
                        recommended_action,
                        next_check,
                        timer_health_status,
                        collection_status,
                        phase_status,
                        micro_live_ready,
                        micro_live_allowed,
                        source_monitor_rank,
                        refreshed_at
                    FROM marketcore_ui.paper_runtime_sample_collection_operations_v1
                    ORDER BY operation_rank
                    LIMIT %s;
                """, (limit,))
                self.send_json(200, response("OK", rows, {
                    "source": "marketcore_ui.paper_runtime_sample_collection_operations_v1",
                    "ui_direct_sql": 0,
                    "logic": "paper_runtime_sample_collection_operations_v1",
                    "orders_changed": 0,
                    "execution_changed": 0
                }))
                return


            if path == "/api/kg/v1/paper-sample-operations-timer-health":
                row = fetch_one("""
                    SELECT
                        timer_unit,
                        service_unit,
                        timer_active_state,
                        timer_sub_state,
                        timer_unit_file_state,
                        timer_next_elapse,
                        timer_last_trigger,
                        timer_healthy,
                        service_active_state,
                        service_sub_state,
                        service_result,
                        service_exec_main_status,
                        service_last_exit,
                        service_healthy,
                        operations_rows,
                        operations_high_rows,
                        operations_near_ready_rows,
                        operations_collecting_rows,
                        operations_micro_live_allowed_rows,
                        operations_refreshed_at,
                        operations_age_sec,
                        operations_stale,
                        phase_result_status,
                        engineering_status,
                        operational_status,
                        phase_timer_health_status,
                        next_phase,
                        health_status,
                        health_reason,
                        recommended_action,
                        micro_live_allowed,
                        refreshed_at,
                        source_version
                    FROM marketcore_ui.paper_runtime_sample_collection_operations_timer_health_v1
                    WHERE id=1;
                """)
                self.send_json(200, response("OK", row or {}, {
                    "source": "marketcore_ui.paper_runtime_sample_collection_operations_timer_health_v1",
                    "ui_direct_sql": 0,
                    "logic": "paper_runtime_sample_collection_operations_timer_health_v1"
                }))
                return


            if path == "/api/kg/v1/paper-sample-operations-daily-summary":
                row = fetch_one("""
                    SELECT
                        summary_date,
                        phase_result_status,
                        engineering_status,
                        operational_status,
                        phase_close_status,
                        sample_collection_status,
                        sample_phase_status,
                        timer_health_status,
                        operations_health_status,
                        operations_rows,
                        operations_high_rows,
                        operations_near_ready_rows,
                        operations_collecting_rows,
                        candidates_total,
                        sample_ready,
                        wait_both_sample,
                        avg_progress_pct,
                        max_progress_pct,
                        min_remaining_total_trades,
                        min_remaining_oos_trades,
                        micro_live_allowed_rows,
                        micro_live_allowed,
                        daily_status,
                        conclusion,
                        recommended_action,
                        refreshed_at,
                        source_version
                    FROM marketcore_ui.paper_runtime_sample_collection_operations_daily_summary_v1
                    WHERE id=1;
                """)
                self.send_json(200, response("OK", row or {}, {
                    "source": "marketcore_ui.paper_runtime_sample_collection_operations_daily_summary_v1",
                    "ui_direct_sql": 0,
                    "logic": "paper_runtime_sample_collection_operations_daily_summary_v1"
                }))
                return


            if path == "/api/kg/v1/marketcore-ui-systemd-health":
                row = fetch_one("""
                    SELECT
                        kg_api_unit,
                        ui_shell_unit,
                        kg_api_active_state,
                        kg_api_sub_state,
                        kg_api_result,
                        kg_api_main_status,
                        kg_api_healthy,
                        ui_shell_active_state,
                        ui_shell_sub_state,
                        ui_shell_result,
                        ui_shell_main_status,
                        ui_shell_healthy,
                        kg_api_port,
                        ui_shell_port,
                        kg_api_http_ok,
                        ui_home_http_ok,
                        ui_risk_http_ok,
                        ui_settings_http_ok,
                        kg_api_health_status,
                        ui_shell_health_status,
                        overall_status,
                        open_url,
                        risk_url,
                        settings_url,
                        health_reason,
                        recommended_action,
                        runtime_changed,
                        execution_changed,
                        orders_changed,
                        fills_changed,
                        micro_live_allowed,
                        refreshed_at,
                        source_version
                    FROM marketcore_ui.marketcore_ui_systemd_8080_health_v1
                    WHERE id=1;
                """)
                self.send_json(200, response("OK", row or {}, {
                    "source": "marketcore_ui.marketcore_ui_systemd_8080_health_v1",
                    "ui_direct_sql": 0,
                    "logic": "marketcore_ui_systemd_8080_health_v1"
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
