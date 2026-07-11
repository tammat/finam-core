from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import parse_qs, urlparse, unquote

import psycopg2
import psycopg2.extras

from marketcore.services.profit_factory_kpi_service_v1 import (
    ProfitFactoryKpiServiceV1,
)

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

            if path == "/api/kg/v1/profit-factory/kpi-summary":
                scope = q.get("scope", ["REAL"])[0]
                try:
                    data = ProfitFactoryKpiServiceV1(DB).summary(scope=scope)
                except ValueError as exc:
                    self.send_json(400, response("ERROR", {}, {"error": str(exc)}))
                    return
                self.send_json(200, response("OK", data, {
                    "source": "analytics.profit_factory_kpi_summary_v1",
                    "trust_gate": "financial_kpi_eligible=true",
                }))
                return

            if path == "/api/kg/v1/profit-factory/kpi-candidates":
                scope = q.get("scope", ["REAL"])[0]
                try:
                    data = ProfitFactoryKpiServiceV1(DB).candidates(scope=scope)
                except ValueError as exc:
                    self.send_json(400, response("ERROR", [], {"error": str(exc)}))
                    return
                self.send_json(200, response("OK", data, {
                    "source": "analytics.profit_factory_kpi_candidate_v1",
                    "trust_gate": "financial_kpi_eligible=true",
                }))
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





            if path == "/api/kg/v1/strategy-workbench":
                from strategy.volatility_breakout.config import VolatilityBreakoutConfig
                from strategy.volatility_breakout.strategy import VolatilityBreakoutStrategy

                cfg_row = fetch_one("""
                    SELECT config_json
                    FROM analytics.strategy_configuration_v1
                    WHERE strategy_family='VOLATILITY_BREAKOUT'
                      AND strategy_version='v1'
                      AND active=true
                    ORDER BY updated_at DESC
                    LIMIT 1;
                """) or {}

                cfg_json = cfg_row.get("config_json") or {}
                strategy = VolatilityBreakoutStrategy(VolatilityBreakoutConfig.from_dict(cfg_json))

                feature_rows = fetch_all("""
                    SELECT
                        symbol,
                        asset_class,
                        timeframe,
                        bar_ts,
                        close,
                        range_pct,
                        body_pct,
                        return1_pct,
                        return5_pct,
                        volume_ratio20,
                        feature_quality_score,
                        market_quality_status,
                        source_version
                    FROM analytics.feature_snapshot_v1
                    WHERE bar_ts IS NOT NULL
                    ORDER BY bar_ts DESC, symbol, timeframe
                    LIMIT 200;
                """)

                rows = []
                signals = 0
                for f in feature_rows:
                    result = strategy.run(dict(f))
                    signal = result.signal
                    if signal is not None:
                        signals += 1

                    rows.append({
                        "symbol": f.get("symbol"),
                        "asset_class": f.get("asset_class"),
                        "timeframe": f.get("timeframe"),
                        "bar_ts": f.get("bar_ts"),
                        "strategy_family": strategy.family,
                        "strategy_version": strategy.version,
                        "reason": result.reason,
                        "signal_direction": signal.direction if signal else "FLAT",
                        "signal_score": signal.score if signal else 0,
                        "confidence": signal.confidence if signal else 0,
                        "passed_filters": result.diagnostics.passed_filters,
                        "failed_filters": result.diagnostics.failed_filters,
                        "feature_values": result.diagnostics.feature_values,
                        "thresholds": result.diagnostics.thresholds,
                        "score_breakdown": result.diagnostics.score_breakdown,
                        "execution_time_ms": result.diagnostics.execution_time_ms,
                    })

                payload = {
                    "summary": {
                        "features_checked": len(feature_rows),
                        "signals_found": signals,
                        "strategy_family": strategy.family,
                        "strategy_version": strategy.version,
                    },
                    "rows": rows,
                }
                self.send_json(200, response("OK", payload, {"source": "analytics.feature_snapshot_v1"}))
                return

            if path == "/api/kg/v1/feature-store":
                rows = fetch_all("""
                    SELECT
                        symbol,
                        asset_class,
                        timeframe,
                        bar_ts,
                        open,
                        high,
                        low,
                        close,
                        volume,
                        range_pct,
                        body_pct,
                        return1_pct,
                        return5_pct,
                        volume_ratio20,
                        feature_quality_score,
                        source_version,
                        refreshed_at
                    FROM analytics.feature_snapshot_v1
                    ORDER BY bar_ts DESC, symbol, timeframe
                    LIMIT 500;
                """)
                self.send_json(200, response("OK", rows, {"source": "analytics.feature_snapshot_v1"}))
                return

            if path == "/api/kg/v1/feature-store/summary":
                row = fetch_one("""
                    SELECT
                        count(*)::int AS feature_rows,
                        count(DISTINCT symbol)::int AS feature_symbols,
                        max(bar_ts) AS latest_bar_ts,
                        max(refreshed_at) AS refreshed_at,
                        avg(feature_quality_score)::numeric(10,4) AS avg_quality_score,
                        count(*) FILTER (WHERE return1_pct IS NOT NULL)::int AS with_return1,
                        count(*) FILTER (WHERE volume_ratio20 IS NOT NULL)::int AS with_volume_ratio20
                    FROM analytics.feature_snapshot_v1;
                """)
                self.send_json(200, response("OK", row or {}, {"source": "analytics.feature_snapshot_v1"}))
                return

            if path == "/api/kg/v1/feature-store/health":
                row = fetch_one("""
                    SELECT *
                    FROM analytics.feature_store_health_v1
                    WHERE health_id='GLOBAL';
                """)
                self.send_json(200, response("OK", row or {}, {"source": "analytics.feature_store_health_v1"}))
                return

            if path == "/api/kg/v1/edge-pipeline":
                rows = fetch_all("""
                    SELECT
                        symbol,
                        display_name,
                        asset_class,
                        timeframe,
                        strategy_family,
                        pipeline_stage,
                        overall_status,
                        ranking_score,
                        research_priority,
                        research_status,
                        validation_status,
                        validation_score,
                        robustness_status,
                        robustness_score,
                        oos_status,
                        oos_score,
                        backtest_status,
                        backtest_score,
                        paper_status,
                        paper_progress,
                        paper_trades,
                        risk_status,
                        trading_status,
                        runtime_status,
                        source_version,
                        refreshed_at
                    FROM analytics.edge_pipeline_snapshot_v1
                    ORDER BY ranking_score DESC, symbol, timeframe, strategy_family;
                """)
                self.send_json(200, response("OK", rows, {"source": "analytics.edge_pipeline_snapshot_v1"}))
                return

            if path == "/api/kg/v1/edge-pipeline/summary":
                row = fetch_one("""
                    SELECT
                        count(*)::int AS total,
                        count(*) FILTER (WHERE pipeline_stage=20)::int AS research,
                        count(*) FILTER (WHERE pipeline_stage=30)::int AS validation,
                        count(*) FILTER (WHERE pipeline_stage=40)::int AS robustness,
                        count(*) FILTER (WHERE pipeline_stage=50)::int AS oos,
                        count(*) FILTER (WHERE pipeline_stage=60)::int AS backtest,
                        count(*) FILTER (WHERE pipeline_stage=70)::int AS paper,
                        count(*) FILTER (WHERE pipeline_stage=80)::int AS risk,
                        count(*) FILTER (WHERE pipeline_stage=90)::int AS trading,
                        count(*) FILTER (WHERE pipeline_stage=100)::int AS live,
                        max(refreshed_at) AS refreshed_at
                    FROM analytics.edge_pipeline_snapshot_v1;
                """)
                self.send_json(200, response("OK", row or {}, {"source": "analytics.edge_pipeline_snapshot_v1"}))
                return

            if path.startswith("/api/kg/v1/edge-pipeline/stage/"):
                stage_raw = path.rsplit("/", 1)[-1]
                try:
                    stage = int(stage_raw)
                except ValueError:
                    self.send_json(400, response("ERROR", {}, {"error": "stage must be integer"}))
                    return

                rows = fetch_all("""
                    SELECT *
                    FROM analytics.edge_pipeline_snapshot_v1
                    WHERE pipeline_stage=%s
                    ORDER BY ranking_score DESC, symbol, timeframe, strategy_family;
                """, (stage,))
                self.send_json(200, response("OK", rows, {"source": "analytics.edge_pipeline_snapshot_v1", "stage": stage}))
                return

            if path.startswith("/api/kg/v1/edge-pipeline/"):
                parts = path.split("/")
                if len(parts) >= 7:
                    symbol = unquote(parts[5])
                    timeframe = unquote(parts[6])
                    row = fetch_one("""
                        SELECT *
                        FROM analytics.edge_pipeline_snapshot_v1
                        WHERE symbol=%s AND timeframe=%s
                        ORDER BY ranking_score DESC, strategy_family
                        LIMIT 1;
                    """, (symbol, timeframe))
                    if not row:
                        self.send_json(404, response("NOT_FOUND", {}, {"source": "analytics.edge_pipeline_snapshot_v1"}))
                        return
                    self.send_json(200, response("OK", row, {"source": "analytics.edge_pipeline_snapshot_v1"}))
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
                        queue_rank,
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
                    FROM marketcore_ui.market_universe_research_queue_v1
                    ORDER BY queue_rank
                    LIMIT %s;
                """, (limit,))
                self.send_json(200, response("OK", rows, {
                    "source": "marketcore_ui.market_universe_research_queue_v1",
                    "ui_direct_sql": 0
                }))
                return


            if path == "/api/kg/v1/paper-edge-top-candidates-detail":
                limit = int(q.get("limit", ["10"])[0])
                rows = fetch_all("""
                    SELECT
                        queue_rank,
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
                    FROM marketcore_ui.market_universe_research_queue_v1
                    ORDER BY queue_rank
                    LIMIT %s;
                """, (limit,))
                self.send_json(200, response("OK", rows, {
                    "source": "marketcore_ui.market_universe_research_queue_v1",
                    "ui_direct_sql": 0,
                    "logic": "paper_edge_top_candidates_detail_v1"
                }))
                return


            if path == "/api/kg/v1/paper-edge-candidate-explainability":
                limit = int(q.get("limit", ["10"])[0])
                rows = fetch_all("""
                    SELECT
                        queue_rank,
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

                    FROM marketcore_ui.market_universe_research_queue_v1
                    ORDER BY queue_rank
                    LIMIT %s;
                """, (limit,))
                self.send_json(200, response("OK", rows, {
                    "source": "marketcore_ui.market_universe_research_queue_v1",
                    "ui_direct_sql": 0,
                    "logic": "paper_edge_candidate_explainability_v1"
                }))
                return



            def dto(kind, code):
                c = str(code or "UNKNOWN")
                severity = "neutral"
                color = "gray"
                icon = "circle"
                if c in {"ACTIVE", "READY", "HEALTHY", "LONG"}:
                    severity, color, icon = "success", "green", "check-circle"
                elif c in {"DEGRADED", "WAIT_SAMPLE", "OBSERVE", "FLAT"}:
                    severity, color, icon = "warning", "orange", "triangle-alert"
                elif c in {"FAILED", "DISABLED", "REJECTED", "SHORT"}:
                    severity, color, icon = "danger", "red", "x-circle"
                return {
                    "code": c,
                    "display_key": f"{kind}.{c}",
                    "severity": severity,
                    "color": color,
                    "icon": icon,
                }


            if path == "/api/kg/v1/strategy-platform/governance":
                row = fetch_one("""
                    SELECT *
                    FROM analytics.strategy_platform_governance_v1
                    WHERE governance_scope='GLOBAL';
                """) or {}

                if row:
                    row["registry_status"] = dto("status", row.get("registry_status"))
                    row["configuration_status"] = dto("status", row.get("configuration_status"))
                    row["dependency_status"] = dto("status", row.get("dependency_status"))
                    row["builder_status"] = dto("status", row.get("builder_status"))
                    row["signal_store_status"] = dto("status", row.get("signal_store_status"))
                    row["api_status"] = dto("status", row.get("api_status"))
                    row["ui_status"] = dto("status", row.get("ui_status"))
                    row["integrity_status"] = dto("status", row.get("integrity_status"))
                    row["health_status"] = dto("health", row.get("health_status"))
                    row["readiness_status"] = dto("governance", row.get("readiness_status"))
                    row["overall_status"] = dto("health", row.get("overall_status"))

                self.send_json(200, response("OK", row, {"source": "analytics.strategy_platform_governance_v1"}))
                return





            if path == "/api/kg/v1/portfolio-platform/summary":
                row = fetch_one("""
                    SELECT
                        e.portfolio_scope,
                        e.cash::float AS cash,
                        e.positions_value::float AS positions_value,
                        e.equity::float AS equity,
                        e.realized_pnl::float AS realized_pnl,
                        e.unrealized_pnl::float AS unrealized_pnl,
                        e.total_pnl::float AS total_pnl,
                        e.gross_exposure::float AS gross_exposure,
                        e.net_exposure::float AS net_exposure,
                        e.source_version,
                        e.refreshed_at,
                        (SELECT count(*)::int FROM analytics.portfolio_position_snapshot_v1) AS position_rows,
                        (SELECT count(*)::int FROM analytics.portfolio_position_snapshot_v1 WHERE position_status='OPEN') AS open_position_rows
                    FROM analytics.portfolio_equity_snapshot_v1 e
                    WHERE e.portfolio_scope='GLOBAL';
                """) or {}
                health_code = "HEALTHY" if row else "DEGRADED"
                row["health"] = dto("health", health_code)
                self.send_json(200, response("OK", row, {"source": "analytics.portfolio_equity_snapshot_v1"}))
                return

            if path == "/api/kg/v1/portfolio-platform/positions":
                rows = fetch_all("""
                    SELECT
                        id,
                        symbol,
                        asset_class,
                        quantity::float AS quantity,
                        avg_price::float AS avg_price,
                        last_price::float AS last_price,
                        market_value::float AS market_value,
                        unrealized_pnl::float AS unrealized_pnl,
                        realized_pnl::float AS realized_pnl,
                        exposure::float AS exposure,
                        position_status,
                        source_version,
                        refreshed_at
                    FROM analytics.portfolio_position_snapshot_v1
                    ORDER BY symbol;
                """)
                for r in rows:
                    r["position_status"] = dto("status", r.get("position_status"))
                self.send_json(200, response("OK", rows, {"source": "analytics.portfolio_position_snapshot_v1"}))
                return

            if path == "/api/kg/v1/portfolio-platform/equity":
                row = fetch_one("""
                    SELECT
                        portfolio_scope,
                        cash::float AS cash,
                        positions_value::float AS positions_value,
                        equity::float AS equity,
                        realized_pnl::float AS realized_pnl,
                        unrealized_pnl::float AS unrealized_pnl,
                        total_pnl::float AS total_pnl,
                        gross_exposure::float AS gross_exposure,
                        net_exposure::float AS net_exposure,
                        source_version,
                        refreshed_at
                    FROM analytics.portfolio_equity_snapshot_v1
                    WHERE portfolio_scope='GLOBAL';
                """) or {}
                self.send_json(200, response("OK", row, {"source": "analytics.portfolio_equity_snapshot_v1"}))
                return

            if path == "/api/kg/v1/portfolio-platform/configuration":
                rows = fetch_all("""
                    SELECT
                        portfolio_name,
                        enabled,
                        config_json,
                        source_version,
                        updated_at
                    FROM analytics.portfolio_configuration_v1
                    ORDER BY portfolio_name;
                """)
                for r in rows:
                    r["enabled_status"] = dto("status", "ACTIVE" if r.get("enabled") else "DISABLED")
                self.send_json(200, response("OK", rows, {"source": "analytics.portfolio_configuration_v1"}))
                return

            if path == "/api/kg/v1/portfolio-platform/governance":
                row = fetch_one("""
                    SELECT *
                    FROM analytics.portfolio_governance_v1
                    WHERE governance_scope='GLOBAL';
                """) or {}
                if row:
                    row["builder_status"] = dto("status", row.get("builder_status"))
                    row["position_status"] = dto("status", row.get("position_status"))
                    row["equity_status"] = dto("status", row.get("equity_status"))
                    row["api_status"] = dto("status", row.get("api_status"))
                    row["ui_status"] = dto("status", row.get("ui_status"))
                    row["readiness"] = dto("governance", row.get("readiness_code"))
                    row["recommendation"] = dto("recommendation", row.get("recommendation_code"))
                self.send_json(200, response("OK", row, {"source": "analytics.portfolio_governance_v1"}))
                return

            if path == "/api/kg/v1/trading-platform/summary":
                row = fetch_one("""
                    SELECT
                        count(*)::int AS intent_rows,
                        count(*) FILTER (WHERE paper_allowed=true)::int AS paper_allowed_rows,
                        count(*) FILTER (WHERE shadow_allowed=true)::int AS shadow_allowed_rows,
                        count(*) FILTER (WHERE micro_live_allowed=true)::int AS micro_live_allowed_rows,
                        count(*) FILTER (WHERE live_allowed=true)::int AS live_allowed_rows,
                        count(*) FILTER (WHERE order_sent=true)::int AS order_sent_rows,
                        count(*) FILTER (WHERE trading_decision_code='PAPER_INTENT_READY')::int AS paper_ready_rows,
                        count(*) FILTER (WHERE trading_decision_code='TRADING_BLOCK')::int AS block_rows,
                        max(signal_ts) AS latest_signal_ts,
                        max(refreshed_at) AS refreshed_at
                    FROM analytics.trading_order_intent_v1;
                """) or {}
                unsafe = int(row.get("micro_live_allowed_rows") or 0) + int(row.get("live_allowed_rows") or 0) + int(row.get("order_sent_rows") or 0)
                health_code = "HEALTHY" if unsafe == 0 and int(row.get("intent_rows") or 0) > 0 else "DEGRADED"
                row["health"] = dto("health", health_code)
                self.send_json(200, response("OK", row, {"source": "analytics.trading_order_intent_v1"}))
                return

            if path == "/api/kg/v1/trading-platform/intents":
                limit = int(q.get("limit", ["500"])[0])
                rows = fetch_all("""
                    SELECT
                        id,
                        risk_decision_id,
                        symbol,
                        asset_class,
                        timeframe,
                        strategy_family,
                        strategy_version,
                        signal_ts,
                        risk_score::float AS risk_score,
                        order_side,
                        order_type,
                        quantity::float AS quantity,
                        trading_decision_code,
                        recommendation_code,
                        paper_allowed,
                        shadow_allowed,
                        micro_live_allowed,
                        live_allowed,
                        order_sent,
                        broker_order_id,
                        source_version,
                        refreshed_at
                    FROM analytics.trading_order_intent_v1
                    ORDER BY signal_ts DESC, risk_score DESC
                    LIMIT %s;
                """, (limit,))
                for r in rows:
                    r["trading_decision"] = dto("trading", r.pop("trading_decision_code"))
                    r["recommendation"] = dto("recommendation", r.pop("recommendation_code"))
                    r["order_side_status"] = dto("signal", r.get("order_side"))
                    r["order_sent_status"] = dto("status", "ACTIVE" if r.get("order_sent") else "DISABLED")
                self.send_json(200, response("OK", rows, {"source": "analytics.trading_order_intent_v1"}))
                return

            if path == "/api/kg/v1/trading-platform/configuration":
                rows = fetch_all("""
                    SELECT
                        trading_name,
                        enabled,
                        config_json,
                        source_version,
                        updated_at
                    FROM analytics.trading_configuration_v1
                    ORDER BY trading_name;
                """)
                for r in rows:
                    r["enabled_status"] = dto("status", "ACTIVE" if r.get("enabled") else "DISABLED")
                self.send_json(200, response("OK", rows, {"source": "analytics.trading_configuration_v1"}))
                return

            if path == "/api/kg/v1/trading-platform/governance":
                row = fetch_one("""
                    SELECT *
                    FROM analytics.trading_governance_v1
                    WHERE governance_scope='GLOBAL';
                """) or {}
                if row:
                    row["builder_status"] = dto("status", row.get("builder_status"))
                    row["order_intent_status"] = dto("status", row.get("order_intent_status"))
                    row["api_status"] = dto("status", row.get("api_status"))
                    row["ui_status"] = dto("status", row.get("ui_status"))
                    row["readiness"] = dto("governance", row.get("readiness_code"))
                    row["recommendation"] = dto("recommendation", row.get("recommendation_code"))
                self.send_json(200, response("OK", row, {"source": "analytics.trading_governance_v1"}))
                return

            if path == "/api/kg/v1/risk-platform/summary":
                row = fetch_one("""
                    SELECT
                        count(*)::int AS risk_rows,
                        count(*) FILTER (WHERE risk_decision_code='RISK_ALLOW')::int AS allow_rows,
                        count(*) FILTER (WHERE risk_decision_code='RISK_OBSERVE')::int AS observe_rows,
                        count(*) FILTER (WHERE risk_decision_code='RISK_BLOCK')::int AS block_rows,
                        count(*) FILTER (WHERE ready_for_paper=true)::int AS ready_for_paper_rows,
                        count(*) FILTER (WHERE ready_for_live=true OR ready_for_micro_live=true)::int AS unsafe_live_rows,
                        avg(risk_score)::float AS avg_risk_score,
                        avg(position_risk_score)::float AS avg_position_risk_score,
                        avg(exposure_risk_score)::float AS avg_exposure_risk_score,
                        max(signal_ts) AS latest_signal_ts,
                        max(refreshed_at) AS refreshed_at
                    FROM analytics.risk_decision_snapshot_v1;
                """) or {}
                health_code = "HEALTHY" if int(row.get("unsafe_live_rows") or 0) == 0 and int(row.get("risk_rows") or 0) > 0 else "DEGRADED"
                row["health"] = dto("health", health_code)
                self.send_json(200, response("OK", row, {"source": "analytics.risk_decision_snapshot_v1"}))
                return

            if path == "/api/kg/v1/risk-platform/decisions":
                limit = int(q.get("limit", ["500"])[0])
                rows = fetch_all("""
                    SELECT
                        id,
                        edge_decision_id,
                        symbol,
                        asset_class,
                        timeframe,
                        strategy_family,
                        strategy_version,
                        signal_ts,
                        edge_score::float AS edge_score,
                        validation_score::float AS validation_score,
                        risk_score::float AS risk_score,
                        position_risk_score::float AS position_risk_score,
                        exposure_risk_score::float AS exposure_risk_score,
                        daily_loss_risk_score::float AS daily_loss_risk_score,
                        correlation_risk_score::float AS correlation_risk_score,
                        kill_switch_score::float AS kill_switch_score,
                        risk_decision_code,
                        recommendation_code,
                        ready_for_paper,
                        ready_for_shadow,
                        ready_for_micro_live,
                        ready_for_live,
                        source_version,
                        refreshed_at
                    FROM analytics.risk_decision_snapshot_v1
                    ORDER BY signal_ts DESC, risk_score DESC
                    LIMIT %s;
                """, (limit,))
                for r in rows:
                    r["risk_decision"] = dto("risk", r.pop("risk_decision_code"))
                    r["recommendation"] = dto("recommendation", r.pop("recommendation_code"))
                self.send_json(200, response("OK", rows, {"source": "analytics.risk_decision_snapshot_v1"}))
                return

            if path == "/api/kg/v1/risk-platform/configuration":
                rows = fetch_all("""
                    SELECT
                        risk_name,
                        enabled,
                        config_json,
                        source_version,
                        updated_at
                    FROM analytics.risk_configuration_v1
                    ORDER BY risk_name;
                """)
                for r in rows:
                    r["enabled_status"] = dto("status", "ACTIVE" if r.get("enabled") else "DISABLED")
                self.send_json(200, response("OK", rows, {"source": "analytics.risk_configuration_v1"}))
                return

            if path == "/api/kg/v1/risk-platform/governance":
                row = fetch_one("""
                    SELECT *
                    FROM analytics.risk_governance_v1
                    WHERE governance_scope='GLOBAL';
                """) or {}
                if row:
                    row["rule_engine_status"] = dto("status", row.get("rule_engine_status"))
                    row["builder_status"] = dto("status", row.get("builder_status"))
                    row["decision_status"] = dto("status", row.get("decision_status"))
                    row["api_status"] = dto("status", row.get("api_status"))
                    row["ui_status"] = dto("status", row.get("ui_status"))
                    row["readiness"] = dto("governance", row.get("readiness_code"))
                    row["recommendation"] = dto("recommendation", row.get("recommendation_code"))
                self.send_json(200, response("OK", row, {"source": "analytics.risk_governance_v1"}))
                return

            if path == "/api/kg/v1/edge-platform/summary":
                row = fetch_one("""
                    SELECT
                        count(*)::int AS edge_rows,
                        count(*) FILTER (WHERE decision_code='ALLOW')::int AS allow_rows,
                        count(*) FILTER (WHERE decision_code='OBSERVE')::int AS observe_rows,
                        count(*) FILTER (WHERE decision_code='BLOCK')::int AS block_rows,
                        count(*) FILTER (WHERE ready_for_paper=true)::int AS ready_for_paper_rows,
                        count(*) FILTER (WHERE ready_for_live=true OR ready_for_micro_live=true)::int AS unsafe_live_rows,
                        avg(edge_score)::float AS avg_edge_score,
                        avg(validation_score)::float AS avg_validation_score,
                        max(signal_ts) AS latest_signal_ts,
                        max(refreshed_at) AS refreshed_at
                    FROM analytics.edge_decision_snapshot_v1;
                """) or {}
                health_code = "HEALTHY" if int(row.get("unsafe_live_rows") or 0) == 0 and int(row.get("edge_rows") or 0) > 0 else "DEGRADED"
                row["health"] = dto("health", health_code)
                self.send_json(200, response("OK", row, {"source": "analytics.edge_decision_snapshot_v1"}))
                return

            if path == "/api/kg/v1/edge-platform/decisions":
                limit = int(q.get("limit", ["500"])[0])
                rows = fetch_all("""
                    SELECT
                        id,
                        signal_id,
                        symbol,
                        asset_class,
                        timeframe,
                        strategy_family,
                        strategy_version,
                        signal_ts,
                        edge_score::float AS edge_score,
                        validation_score::float AS validation_score,
                        governance_score::float AS governance_score,
                        decision_code,
                        recommendation_code,
                        ready_for_research,
                        ready_for_replay,
                        ready_for_paper,
                        ready_for_shadow,
                        ready_for_micro_live,
                        ready_for_live,
                        source_version,
                        refreshed_at
                    FROM analytics.edge_decision_snapshot_v1
                    ORDER BY signal_ts DESC, edge_score DESC
                    LIMIT %s;
                """, (limit,))
                for r in rows:
                    r["decision"] = dto("decision", r.pop("decision_code"))
                    r["recommendation"] = dto("recommendation", r.pop("recommendation_code"))
                self.send_json(200, response("OK", rows, {"source": "analytics.edge_decision_snapshot_v1"}))
                return

            if path == "/api/kg/v1/edge-platform/configuration":
                rows = fetch_all("""
                    SELECT
                        edge_name,
                        enabled,
                        config_json,
                        source_version,
                        updated_at
                    FROM analytics.edge_configuration_v1
                    ORDER BY edge_name;
                """)
                for r in rows:
                    r["enabled_status"] = dto("status", "ACTIVE" if r.get("enabled") else "DISABLED")
                self.send_json(200, response("OK", rows, {"source": "analytics.edge_configuration_v1"}))
                return

            if path == "/api/kg/v1/edge-platform/governance":
                row = fetch_one("""
                    SELECT *
                    FROM analytics.edge_governance_v1
                    WHERE governance_scope='GLOBAL';
                """) or {}
                if row:
                    row["score_engine_status"] = dto("status", row.get("score_engine_status"))
                    row["validation_status"] = dto("status", row.get("validation_status"))
                    row["decision_status"] = dto("status", row.get("decision_status"))
                    row["api_status"] = dto("status", row.get("api_status"))
                    row["ui_status"] = dto("status", row.get("ui_status"))
                    row["readiness"] = dto("governance", row.get("readiness_code"))
                    row["recommendation"] = dto("recommendation", row.get("recommendation_code"))
                self.send_json(200, response("OK", row, {"source": "analytics.edge_governance_v1"}))
                return

            if path == "/api/kg/v1/strategy-platform/summary":
                row = fetch_one("""
                    SELECT
                        (SELECT count(*)::int FROM analytics.strategy_registry_v1) AS strategies_total,
                        (SELECT count(*)::int FROM analytics.strategy_registry_v1 WHERE enabled=true) AS strategies_enabled,
                        (SELECT count(*)::int FROM analytics.strategy_registry_v1 WHERE paper_enabled=true) AS paper_enabled,
                        (SELECT count(*)::int FROM analytics.strategy_registry_v1 WHERE live_enabled=true) AS live_enabled,
                        (SELECT count(*)::int FROM analytics.strategy_configuration_v1 WHERE active=true) AS active_configs,
                        (SELECT count(*)::int FROM analytics.strategy_feature_dependency_v1) AS dependencies_total,
                        (SELECT count(*)::int FROM analytics.strategy_signal_snapshot_v1) AS signals_total,
                        (SELECT count(*)::int FROM analytics.strategy_signal_snapshot_v1 WHERE execution_allowed=true) AS execution_allowed,
                        (SELECT max(signal_ts) FROM analytics.strategy_signal_snapshot_v1) AS latest_signal_ts;
                """) or {}
                health_code = "HEALTHY" if int(row.get("strategies_enabled") or 0) > 0 and int(row.get("active_configs") or 0) > 0 else "DEGRADED"
                row["health"] = dto("health", health_code)
                self.send_json(200, response("OK", row, {"source": "analytics.strategy_*"}))
                return

            if path == "/api/kg/v1/strategy-platform/registry":
                rows = fetch_all("""
                    SELECT
                        strategy_family,
                        strategy_name,
                        strategy_version,
                        category,
                        enabled,
                        paper_enabled,
                        risk_enabled,
                        live_enabled,
                        priority,
                        description,
                        status,
                        updated_at
                    FROM analytics.strategy_registry_v1
                    ORDER BY priority, strategy_family, strategy_version;
                """)
                for r in rows:
                    r["status"] = dto("status", r.get("status"))
                    r["enabled_status"] = dto("status", "ACTIVE" if r.get("enabled") else "DISABLED")
                self.send_json(200, response("OK", rows, {"source": "analytics.strategy_registry_v1"}))
                return

            if path == "/api/kg/v1/strategy-platform/configuration":
                rows = fetch_all("""
                    SELECT
                        strategy_family,
                        strategy_version,
                        config_version,
                        active,
                        config_json,
                        updated_at
                    FROM analytics.strategy_configuration_v1
                    ORDER BY strategy_family, strategy_version, config_version;
                """)
                for r in rows:
                    r["active_status"] = dto("status", "ACTIVE" if r.get("active") else "DISABLED")
                self.send_json(200, response("OK", rows, {"source": "analytics.strategy_configuration_v1"}))
                return

            if path == "/api/kg/v1/strategy-platform/dependencies":
                rows = fetch_all("""
                    SELECT
                        strategy_family,
                        strategy_version,
                        feature_name,
                        required,
                        weight
                    FROM analytics.strategy_feature_dependency_v1
                    ORDER BY strategy_family, strategy_version, feature_name;
                """)
                self.send_json(200, response("OK", rows, {"source": "analytics.strategy_feature_dependency_v1"}))
                return

            if path == "/api/kg/v1/strategy-platform/signals":
                limit = int(q.get("limit", ["500"])[0])
                rows = fetch_all("""
                    SELECT
                        symbol,
                        asset_class,
                        timeframe,
                        strategy_family,
                        signal_ts,
                        signal_direction,
                        signal_strength,
                        signal_score,
                        confidence,
                        signal_status,
                        feature_quality_score,
                        market_quality_status,
                        paper_allowed,
                        risk_allowed,
                        execution_allowed,
                        feature_version,
                        strategy_version,
                        refreshed_at
                    FROM analytics.strategy_signal_snapshot_v1
                    ORDER BY signal_ts DESC, signal_score DESC
                    LIMIT %s;
                """, (limit,))
                for r in rows:
                    r["signal_direction"] = dto("signal", r.get("signal_direction"))
                    r["signal_status"] = dto("status", r.get("signal_status"))
                    r["market_quality_status"] = dto("status", r.get("market_quality_status"))
                self.send_json(200, response("OK", rows, {"source": "analytics.strategy_signal_snapshot_v1"}))
                return

            if path == "/api/kg/v1/strategy-platform/health":
                row = fetch_one("""
                    SELECT
                        (SELECT count(*)::int FROM analytics.strategy_registry_v1) AS registry_rows,
                        (SELECT count(*)::int FROM analytics.strategy_registry_v1 WHERE enabled=true) AS enabled_strategies,
                        (SELECT count(*)::int FROM analytics.strategy_configuration_v1 WHERE active=true) AS active_configs,
                        (SELECT count(*)::int FROM analytics.strategy_feature_dependency_v1) AS dependency_rows,
                        (SELECT count(*)::int FROM analytics.strategy_signal_snapshot_v1) AS signal_rows,
                        (SELECT count(*)::int FROM analytics.strategy_signal_snapshot_v1 WHERE execution_allowed=true) AS unsafe_execution_rows;
                """) or {}
                health_code = "HEALTHY"
                if int(row.get("enabled_strategies") or 0) <= 0 or int(row.get("active_configs") or 0) <= 0:
                    health_code = "DEGRADED"
                if int(row.get("unsafe_execution_rows") or 0) > 0:
                    health_code = "FAILED"
                row["health"] = dto("health", health_code)
                self.send_json(200, response("OK", row, {"source": "analytics.strategy_platform"}))
                return

            if path == "/api/kg/v1/strategy-platform/workbench":
                from strategy.volatility_breakout.config import VolatilityBreakoutConfig
                from strategy.volatility_breakout.strategy import VolatilityBreakoutStrategy

                cfg_row = fetch_one("""
                    SELECT config_json
                    FROM analytics.strategy_configuration_v1
                    WHERE strategy_family='VOLATILITY_BREAKOUT'
                      AND strategy_version='v1'
                      AND active=true
                    ORDER BY updated_at DESC
                    LIMIT 1;
                """) or {}

                strategy = VolatilityBreakoutStrategy(
                    VolatilityBreakoutConfig.from_dict(cfg_row.get("config_json") or {})
                )

                features = fetch_all("""
                    SELECT
                        symbol, asset_class, timeframe, bar_ts, close,
                        range_pct, body_pct, return1_pct, return5_pct,
                        volume_ratio20, feature_quality_score,
                        market_quality_status, source_version
                    FROM analytics.feature_snapshot_v1
                    WHERE bar_ts IS NOT NULL
                    ORDER BY bar_ts DESC, symbol, timeframe
                    LIMIT 200;
                """)

                rows = []
                signals = 0
                for f in features:
                    result = strategy.run(dict(f))
                    signal = result.signal
                    if signal:
                        signals += 1
                    rows.append({
                        "symbol": f.get("symbol"),
                        "timeframe": f.get("timeframe"),
                        "bar_ts": f.get("bar_ts"),
                        "strategy_family": strategy.family,
                        "strategy_version": strategy.version,
                        "reason": dto("status", result.reason),
                        "signal_direction": dto("signal", signal.direction if signal else "FLAT"),
                        "signal_score": signal.score if signal else 0,
                        "confidence": signal.confidence if signal else 0,
                        "passed_filters": result.diagnostics.passed_filters,
                        "failed_filters": result.diagnostics.failed_filters,
                        "feature_values": result.diagnostics.feature_values,
                        "thresholds": result.diagnostics.thresholds,
                        "score_breakdown": result.diagnostics.score_breakdown,
                        "execution_time_ms": result.diagnostics.execution_time_ms,
                    })

                payload = {
                    "summary": {
                        "features_checked": len(features),
                        "signals_found": signals,
                        "strategy_family": strategy.family,
                        "strategy_version": strategy.version,
                    },
                    "rows": rows,
                }
                self.send_json(200, response("OK", payload, {"source": "analytics.feature_snapshot_v1"}))
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
                        source_queue_rank,
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


            if path == "/api/kg/v1/marketcore-ui-route-health-matrix":
                rows = fetch_all("""
                    SELECT
                        route,
                        label_ru,
                        group_key,
                        group_title_ru,
                        menu_order,
                        http_status,
                        http_ok,
                        contains_shell_marker,
                        content_length,
                        issue,
                        checked_at
                    FROM marketcore_ui.marketcore_ui_route_health_matrix_v1
                    ORDER BY group_key, menu_order, route;
                """)
                self.send_json(200, response("OK", rows, {
                    "source": "marketcore_ui.marketcore_ui_route_health_matrix_v1",
                    "ui_direct_sql": 0,
                    "logic": "marketcore_ui_8080_route_health_matrix_v1"
                }))
                return


            if path == "/api/kg/v1/paper-edge-market-data-binding":
                limit = int(q.get("limit", ["50"])[0])
                rows = fetch_all("""
                    SELECT
                        binding_rank,
                        symbol,
                        strategy,
                        timeframe,
                        side,
                        market_symbol,
                        market_timeframe,
                        bars_source_table,
                        bars_total,
                        latest_bar_ts,
                        latest_close,
                        latest_volume,
                        market_data_age_sec,
                        market_data_status,
                        binding_status,
                        binding_reason,
                        recommended_action,
                        source_queue_rank,
                        refreshed_at
                    FROM marketcore_ui.paper_edge_market_data_binding_v1
                    ORDER BY binding_rank
                    LIMIT %s;
                """, (limit,))
                self.send_json(200, response("OK", rows, {
                    "source": "marketcore_ui.paper_edge_market_data_binding_v1",
                    "ui_direct_sql": 0,
                    "logic": "paper_edge_discovery_market_data_binding_v1"
                }))
                return


            if path == "/api/kg/v1/paper-edge-market-data-freshness":
                limit = int(q.get("limit", ["100"])[0])
                rows = fetch_all("""
                    SELECT
                        freshness_rank,
                        row_type,
                        candidate_symbol,
                        candidate_strategy,
                        candidate_timeframe,
                        side,
                        market_symbol,
                        market_timeframe,
                        source_table,
                        bars_total,
                        latest_bar_ts,
                        latest_close,
                        latest_volume,
                        market_data_age_sec,
                        freshness_status,
                        binding_status,
                        diagnosis,
                        recommended_action,
                        source_rank,
                        refreshed_at
                    FROM marketcore_ui.paper_edge_market_data_freshness_v1
                    ORDER BY freshness_rank
                    LIMIT %s;
                """, (limit,))
                self.send_json(200, response("OK", rows, {
                    "source": "marketcore_ui.paper_edge_market_data_freshness_v1",
                    "ui_direct_sql": 0,
                    "logic": "paper_edge_discovery_market_data_freshness_v1"
                }))
                return


            if path == "/api/kg/v1/paper-edge-market-symbol-alias-plan":
                limit = int(q.get("limit", ["100"])[0])
                rows = fetch_all("""
                    SELECT
                        plan_rank,
                        candidate_symbol,
                        candidate_root,
                        candidate_strategy,
                        candidate_timeframe,
                        side,
                        alias_symbol,
                        alias_timeframe,
                        alias_source_table,
                        alias_bars_total,
                        alias_latest_bar_ts,
                        alias_market_data_age_sec,
                        alias_match_type,
                        alias_confidence,
                        alias_status,
                        diagnosis,
                        recommended_action,
                        source_freshness_rank,
                        refreshed_at
                    FROM marketcore_ui.paper_edge_market_symbol_alias_plan_v1
                    ORDER BY plan_rank
                    LIMIT %s;
                """, (limit,))
                self.send_json(200, response("OK", rows, {
                    "source": "marketcore_ui.paper_edge_market_symbol_alias_plan_v1",
                    "ui_direct_sql": 0,
                    "logic": "paper_edge_discovery_market_symbol_alias_plan_v1"
                }))
                return


            if path == "/api/kg/v1/market-universe-ranking":
                limit = int(q.get("limit", ["100"])[0])
                rows = fetch_all("""
                    SELECT
                        rank, symbol, timeframe, asset_class,
                        bars_total, latest_ts, latest_close, latest_volume, data_age_sec,
                        freshness_score, history_score, liquidity_score, timeframe_score,
                        asset_priority_score, total_score,
                        ranking_status, recommended_action, refreshed_at
                    FROM marketcore_ui.market_universe_ranking_v1
                    ORDER BY rank
                    LIMIT %s;
                """, (limit,))
                self.send_json(200, response("OK", rows, {
                    "source": "marketcore_ui.market_universe_ranking_v1",
                    "ui_direct_sql": 0,
                    "logic": "market_universe_ranking_v1"
                }))
                return


            if path == "/api/kg/v1/market-universe-research-queue":
                limit = int(q.get("limit", ["50"])[0])
                rows = fetch_all("""
                    SELECT
                        queue_rank,
                        symbol,
                        timeframe,
                        asset_class,
                        total_score,
                        ranking_status,
                        research_priority,
                        research_status,
                        recommended_strategy_family,
                        recommended_action,
                        source_rank,
                        refreshed_at
                    FROM marketcore_ui.market_universe_research_queue_v1
                    ORDER BY queue_rank
                    LIMIT %s;
                """, (limit,))
                self.send_json(200, response("OK", rows, {
                    "source": "marketcore_ui.market_universe_research_queue_v1",
                    "ui_direct_sql": 0,
                    "logic": "market_universe_research_queue_v1"
                }))
                return


            if path == "/api/kg/v1/edge-discovery-use-market-universe":
                row = fetch_one("""
                    SELECT
                        legacy_source,
                        new_source,
                        legacy_rows,
                        legacy_symbols,
                        queue_rows,
                        queue_symbols,
                        ranking_rows,
                        universe_rows,
                        migration_status,
                        diagnosis,
                        recommended_action,
                        runtime_changed,
                        execution_changed,
                        orders_changed,
                        fills_changed,
                        micro_live_allowed,
                        refreshed_at,
                        source_version
                    FROM marketcore_ui.edge_discovery_use_market_universe_v1
                    WHERE id=1;
                """)
                self.send_json(200, response("OK", row or {}, {
                    "source": "marketcore_ui.edge_discovery_use_market_universe_v1",
                    "ui_direct_sql": 0,
                    "logic": "edge_discovery_use_market_universe_v1"
                }))
                return


            if path == "/api/kg/v1/edge-validation-use-market-universe":
                limit = int(q.get("limit", ["50"])[0])
                rows = fetch_all("""
                    SELECT
                        validation_rank,
                        symbol,
                        timeframe,
                        asset_class,
                        strategy,
                        side,
                        source_queue_rank,
                        total_score,
                        research_priority,
                        ranking_status,
                        validation_status,
                        validation_stage,
                        recommended_action,
                        refreshed_at
                    FROM marketcore_ui.edge_validation_use_market_universe_v1
                    ORDER BY validation_rank
                    LIMIT %s;
                """, (limit,))
                self.send_json(200, response("OK", rows, {
                    "source": "marketcore_ui.edge_validation_use_market_universe_v1",
                    "ui_direct_sql": 0,
                    "logic": "edge_validation_use_market_universe_v1"
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
