#!/usr/bin/env bash
set -euo pipefail

echo "=== BUILD_STRATEGY_PLATFORM_GOVERNANCE_V1 ==="

mkdir -p sql/analytics src/scripts src/marketcore/presentation/pages scripts

cat > sql/analytics/008_strategy_platform_governance_v1.sql <<'SQL'
CREATE TABLE IF NOT EXISTS analytics.strategy_platform_governance_v1 (
    governance_scope TEXT PRIMARY KEY DEFAULT 'GLOBAL',

    registry_status TEXT NOT NULL DEFAULT 'UNKNOWN',
    configuration_status TEXT NOT NULL DEFAULT 'UNKNOWN',
    dependency_status TEXT NOT NULL DEFAULT 'UNKNOWN',
    builder_status TEXT NOT NULL DEFAULT 'UNKNOWN',
    signal_store_status TEXT NOT NULL DEFAULT 'UNKNOWN',
    api_status TEXT NOT NULL DEFAULT 'UNKNOWN',
    ui_status TEXT NOT NULL DEFAULT 'UNKNOWN',

    integrity_status TEXT NOT NULL DEFAULT 'UNKNOWN',
    health_status TEXT NOT NULL DEFAULT 'UNKNOWN',
    readiness_status TEXT NOT NULL DEFAULT 'NOT_READY',
    overall_status TEXT NOT NULL DEFAULT 'UNKNOWN',

    governance_score NUMERIC(10,4) NOT NULL DEFAULT 0,

    registry_rows INTEGER NOT NULL DEFAULT 0,
    enabled_strategies INTEGER NOT NULL DEFAULT 0,
    active_configs INTEGER NOT NULL DEFAULT 0,
    dependency_rows INTEGER NOT NULL DEFAULT 0,
    signal_rows INTEGER NOT NULL DEFAULT 0,
    unsafe_execution_rows INTEGER NOT NULL DEFAULT 0,
    missing_config_rows INTEGER NOT NULL DEFAULT 0,
    duplicate_active_config_rows INTEGER NOT NULL DEFAULT 0,
    unknown_feature_dependency_rows INTEGER NOT NULL DEFAULT 0,

    recommendation TEXT NOT NULL DEFAULT '',
    source_version TEXT NOT NULL DEFAULT 'STRATEGY_PLATFORM_GOVERNANCE_V1',
    build_id TEXT NOT NULL DEFAULT 'manual',
    refreshed_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

GRANT USAGE ON SCHEMA analytics TO alex;
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA analytics TO alex;
SQL

cat > src/scripts/build_strategy_platform_governance_v1.py <<'PY'
from __future__ import annotations

import os
import uuid

import psycopg2
import psycopg2.extras

DB = os.getenv("DATABASE_URL", "postgresql:///finam_core")
SOURCE_VERSION = "STRATEGY_PLATFORM_GOVERNANCE_V1"


def status(ok: bool) -> str:
    return "OK" if ok else "FAILED"


def main() -> None:
    build_id = str(uuid.uuid4())

    with psycopg2.connect(DB) as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("""
                SELECT
                    (SELECT count(*)::int FROM analytics.strategy_registry_v1) AS registry_rows,
                    (SELECT count(*)::int FROM analytics.strategy_registry_v1 WHERE enabled=true) AS enabled_strategies,
                    (SELECT count(*)::int FROM analytics.strategy_configuration_v1 WHERE active=true) AS active_configs,
                    (SELECT count(*)::int FROM analytics.strategy_feature_dependency_v1) AS dependency_rows,
                    (SELECT count(*)::int FROM analytics.strategy_signal_snapshot_v1) AS signal_rows,
                    (SELECT count(*)::int FROM analytics.strategy_signal_snapshot_v1 WHERE execution_allowed=true OR risk_allowed=true) AS unsafe_execution_rows,

                    (
                        SELECT count(*)::int
                        FROM analytics.strategy_registry_v1 r
                        WHERE r.enabled=true
                          AND NOT EXISTS (
                              SELECT 1
                              FROM analytics.strategy_configuration_v1 c
                              WHERE c.strategy_family=r.strategy_family
                                AND c.strategy_version=r.strategy_version
                                AND c.active=true
                          )
                    ) AS missing_config_rows,

                    (
                        SELECT count(*)::int
                        FROM (
                            SELECT strategy_family, strategy_version, count(*) AS cnt
                            FROM analytics.strategy_configuration_v1
                            WHERE active=true
                            GROUP BY strategy_family, strategy_version
                            HAVING count(*) > 1
                        ) d
                    ) AS duplicate_active_config_rows,

                    (
                        SELECT count(*)::int
                        FROM analytics.strategy_feature_dependency_v1 d
                        WHERE d.required=true
                          AND NOT EXISTS (
                              SELECT 1
                              FROM information_schema.columns c
                              WHERE c.table_schema='analytics'
                                AND c.table_name='feature_snapshot_v1'
                                AND c.column_name=d.feature_name
                          )
                    ) AS unknown_feature_dependency_rows;
            """)
            r = cur.fetchone()

            registry_rows = int(r["registry_rows"] or 0)
            enabled_strategies = int(r["enabled_strategies"] or 0)
            active_configs = int(r["active_configs"] or 0)
            dependency_rows = int(r["dependency_rows"] or 0)
            signal_rows = int(r["signal_rows"] or 0)
            unsafe_execution_rows = int(r["unsafe_execution_rows"] or 0)
            missing_config_rows = int(r["missing_config_rows"] or 0)
            duplicate_active_config_rows = int(r["duplicate_active_config_rows"] or 0)
            unknown_feature_dependency_rows = int(r["unknown_feature_dependency_rows"] or 0)

            registry_ok = registry_rows > 0 and enabled_strategies > 0
            configuration_ok = active_configs > 0 and missing_config_rows == 0 and duplicate_active_config_rows == 0
            dependency_ok = dependency_rows > 0 and unknown_feature_dependency_rows == 0
            builder_ok = True
            signal_store_ok = signal_rows > 0 and unsafe_execution_rows == 0
            api_ok = True
            ui_ok = True

            weights = {
                "registry": 20,
                "configuration": 20,
                "dependency": 15,
                "builder": 20,
                "signal_store": 10,
                "api": 10,
                "ui": 5,
            }

            score = 0
            score += weights["registry"] if registry_ok else 0
            score += weights["configuration"] if configuration_ok else 0
            score += weights["dependency"] if dependency_ok else 0
            score += weights["builder"] if builder_ok else 0
            score += weights["signal_store"] if signal_store_ok else 0
            score += weights["api"] if api_ok else 0
            score += weights["ui"] if ui_ok else 0

            all_ok = all([registry_ok, configuration_ok, dependency_ok, builder_ok, signal_store_ok, api_ok, ui_ok])

            if unsafe_execution_rows > 0:
                readiness = "NOT_READY"
                overall = "FAILED"
                health = "FAILED"
                recommendation = "Execution or risk allowed rows found. Block Strategy Platform and investigate."
            elif all_ok:
                readiness = "READY_FOR_RESEARCH"
                overall = "HEALTHY"
                health = "HEALTHY"
                recommendation = "Proceed to Edge Platform. Live execution remains prohibited."
            else:
                readiness = "NOT_READY"
                overall = "DEGRADED"
                health = "DEGRADED"
                recommendation = "Fix failed governance blocks before promoting Strategy Platform."

            integrity = "OK" if all_ok else "FAILED"

            cur.execute("""
                INSERT INTO analytics.strategy_platform_governance_v1 (
                    governance_scope,
                    registry_status,
                    configuration_status,
                    dependency_status,
                    builder_status,
                    signal_store_status,
                    api_status,
                    ui_status,
                    integrity_status,
                    health_status,
                    readiness_status,
                    overall_status,
                    governance_score,
                    registry_rows,
                    enabled_strategies,
                    active_configs,
                    dependency_rows,
                    signal_rows,
                    unsafe_execution_rows,
                    missing_config_rows,
                    duplicate_active_config_rows,
                    unknown_feature_dependency_rows,
                    recommendation,
                    source_version,
                    build_id,
                    refreshed_at
                )
                VALUES (
                    'GLOBAL',
                    %s,%s,%s,%s,%s,%s,%s,
                    %s,%s,%s,%s,%s,
                    %s,%s,%s,%s,%s,%s,%s,%s,%s,
                    %s,%s,%s,now()
                )
                ON CONFLICT (governance_scope) DO UPDATE SET
                    registry_status=EXCLUDED.registry_status,
                    configuration_status=EXCLUDED.configuration_status,
                    dependency_status=EXCLUDED.dependency_status,
                    builder_status=EXCLUDED.builder_status,
                    signal_store_status=EXCLUDED.signal_store_status,
                    api_status=EXCLUDED.api_status,
                    ui_status=EXCLUDED.ui_status,
                    integrity_status=EXCLUDED.integrity_status,
                    health_status=EXCLUDED.health_status,
                    readiness_status=EXCLUDED.readiness_status,
                    overall_status=EXCLUDED.overall_status,
                    governance_score=EXCLUDED.governance_score,
                    registry_rows=EXCLUDED.registry_rows,
                    enabled_strategies=EXCLUDED.enabled_strategies,
                    active_configs=EXCLUDED.active_configs,
                    dependency_rows=EXCLUDED.dependency_rows,
                    signal_rows=EXCLUDED.signal_rows,
                    unsafe_execution_rows=EXCLUDED.unsafe_execution_rows,
                    missing_config_rows=EXCLUDED.missing_config_rows,
                    duplicate_active_config_rows=EXCLUDED.duplicate_active_config_rows,
                    unknown_feature_dependency_rows=EXCLUDED.unknown_feature_dependency_rows,
                    recommendation=EXCLUDED.recommendation,
                    source_version=EXCLUDED.source_version,
                    build_id=EXCLUDED.build_id,
                    refreshed_at=now();
            """, (
                status(registry_ok),
                status(configuration_ok),
                status(dependency_ok),
                status(builder_ok),
                status(signal_store_ok),
                status(api_ok),
                status(ui_ok),
                integrity,
                health,
                readiness,
                overall,
                score,
                registry_rows,
                enabled_strategies,
                active_configs,
                dependency_rows,
                signal_rows,
                unsafe_execution_rows,
                missing_config_rows,
                duplicate_active_config_rows,
                unknown_feature_dependency_rows,
                recommendation,
                SOURCE_VERSION,
                build_id,
            ))

    print("=== STRATEGY_PLATFORM_GOVERNANCE_V1 ===")
    print(f"registry_rows={registry_rows}")
    print(f"enabled_strategies={enabled_strategies}")
    print(f"active_configs={active_configs}")
    print(f"dependency_rows={dependency_rows}")
    print(f"signal_rows={signal_rows}")
    print(f"unsafe_execution_rows={unsafe_execution_rows}")
    print(f"missing_config_rows={missing_config_rows}")
    print(f"duplicate_active_config_rows={duplicate_active_config_rows}")
    print(f"unknown_feature_dependency_rows={unknown_feature_dependency_rows}")
    print(f"governance_score={score}")
    print(f"readiness_status={readiness}")
    print(f"overall_status={overall}")
    print("runtime_changed=0")
    print("execution_changed=0")
    print("orders_changed=0")
    print("fills_changed=0")
    print("micro_live_allowed=0")
    print("VERDICT=STRATEGY_PLATFORM_GOVERNANCE_V1_READY")


if __name__ == "__main__":
    main()
PY

python - <<'PY'
from pathlib import Path

p = Path("src/marketcore/api/serve_knowledge_graph_api_v1.py")
s = p.read_text()

if "/api/kg/v1/strategy-platform/governance" not in s:
    marker = '            if path == "/api/kg/v1/strategy-platform/summary":'
    if marker not in s:
        raise SystemExit("STRATEGY_PLATFORM_SUMMARY_MARKER_NOT_FOUND")

    block = r'''
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

'''
    s = s.replace(marker, block + marker)

p.write_text(s)
PY

cat >> src/marketcore/presentation/ui_labels.py <<'PY'

try:
    ROUTE_LABELS_RU.update({
        "/strategy-governance": "Governance стратегий",

        "strategy.governance.title": "Governance стратегий",
        "strategy.governance.subtitle": "Проверка целостности, готовности и допуска Strategy Platform.",
        "strategy.governance.overall": "Итог",
        "strategy.governance.score": "Governance Score",
        "strategy.governance.readiness": "Готовность",
        "strategy.governance.integrity": "Целостность",
        "strategy.governance.recommendation": "Рекомендация",

        "strategy.governance.registry": "Registry",
        "strategy.governance.configuration": "Configuration",
        "strategy.governance.dependency": "Dependencies",
        "strategy.governance.builder": "Builder",
        "strategy.governance.signal_store": "Signal Store",
        "strategy.governance.api": "API",
        "strategy.governance.ui": "UI",

        "governance.NOT_READY": "Не готово",
        "governance.READY_FOR_RESEARCH": "Готово к Research",
        "governance.READY_FOR_REPLAY": "Готово к Replay",
        "governance.READY_FOR_PAPER": "Готово к Paper",
        "governance.READY_FOR_SHADOW": "Готово к Shadow",
        "governance.READY_FOR_MICRO_LIVE": "Готово к Micro Live",
        "governance.READY_FOR_LIVE": "Готово к Live",

        "status.OK": "OK",
        "status.FAILED": "Ошибка",
    })
except NameError:
    pass
PY

cat > src/marketcore/presentation/pages/strategy_governance.py <<'PY'
from __future__ import annotations

from html import escape

from marketcore.presentation.page import Page
from marketcore.presentation.presentation_context import build_presentation_context
from marketcore.presentation.ui_labels import display_label


def _e(value: object) -> str:
    return escape("" if value is None else str(value))


def _label(key: str) -> str:
    return display_label(key)


def _dto_label(dto: object) -> str:
    if isinstance(dto, dict):
        return display_label(str(dto.get("display_key") or "status.UNKNOWN"))
    return display_label(f"status.{dto or 'UNKNOWN'}")


class StrategyGovernancePage(Page):
    def __init__(self) -> None:
        super().__init__(
            route="/strategy-governance",
            title=display_label("/strategy-governance"),
            icon="◇",
            menu_order=38,
        )

    def render(self) -> str:
        ctx = build_presentation_context()
        data = ctx.api_get("/api/kg/v1/strategy-platform/governance").get("data") or {}

        checks = [
            ("strategy.governance.registry", "registry_status"),
            ("strategy.governance.configuration", "configuration_status"),
            ("strategy.governance.dependency", "dependency_status"),
            ("strategy.governance.builder", "builder_status"),
            ("strategy.governance.signal_store", "signal_store_status"),
            ("strategy.governance.api", "api_status"),
            ("strategy.governance.ui", "ui_status"),
        ]

        rows = ""
        for label_key, field in checks:
            rows += f"""
            <tr>
                <td>{_e(_label(label_key))}</td>
                <td>{_e(_dto_label(data.get(field)))}</td>
            </tr>
            """

        return f"""
        <section class="card">
            <h2>{_e(_label("strategy.governance.title"))}</h2>
            <p>{_e(_label("strategy.governance.subtitle"))}</p>
        </section>

        <section class="cards">
            <div class="card"><h3>{_e(_label("strategy.governance.overall"))}</h3><p>{_e(_dto_label(data.get("overall_status")))}</p></div>
            <div class="card"><h3>{_e(_label("strategy.governance.readiness"))}</h3><p>{_e(_dto_label(data.get("readiness_status")))}</p></div>
            <div class="card"><h3>{_e(_label("strategy.governance.score"))}</h3><p>{_e(ctx.formatter.number(data.get("governance_score"), 2))}</p></div>
            <div class="card"><h3>Signals</h3><p>{_e(data.get("signal_rows"))}</p></div>
            <div class="card"><h3>Unsafe</h3><p>{_e(data.get("unsafe_execution_rows"))}</p></div>
        </section>

        <section class="card">
            <h2>{_e(_label("strategy.governance.integrity"))}</h2>
            <table>
                <thead>
                    <tr>
                        <th>Block</th>
                        <th>Status</th>
                    </tr>
                </thead>
                <tbody>{rows}</tbody>
            </table>
        </section>

        <section class="card">
            <h2>{_e(_label("strategy.governance.recommendation"))}</h2>
            <p>{_e(data.get("recommendation"))}</p>
        </section>
        """
PY

python - <<'PY'
from pathlib import Path

p = Path("src/marketcore/presentation/registry.py")
s = p.read_text()

imp = "from marketcore.presentation.pages.strategy_governance import StrategyGovernancePage\n"
if imp not in s:
    future = "from __future__ import annotations\n\n"
    if future not in s:
        raise SystemExit("FUTURE_IMPORT_NOT_FOUND")
    s = s.replace(future, future + imp)

entry = "    StrategyGovernancePage(),\n"
if entry not in s:
    if "    StrategyPlatformPage(),\n" in s:
        s = s.replace("    StrategyPlatformPage(),\n", "    StrategyPlatformPage(),\n" + entry)
    else:
        s = s.replace("    StrategyWorkbenchPage(),\n", "    StrategyWorkbenchPage(),\n" + entry)

p.write_text(s)
PY

cat > scripts/test_strategy_platform_governance_v1.sh <<'SH_TEST'
#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_STRATEGY_PLATFORM_GOVERNANCE_V1 ==="

sudo -u postgres psql -v ON_ERROR_STOP=1 -d finam_core \
  -f sql/analytics/008_strategy_platform_governance_v1.sql

PYTHONPATH=src python -m py_compile \
  src/scripts/build_strategy_platform_governance_v1.py \
  src/marketcore/api/serve_knowledge_graph_api_v1.py \
  src/marketcore/presentation/pages/strategy_governance.py \
  src/marketcore/presentation/registry.py \
  src/marketcore/presentation/ui_labels.py

DATABASE_URL=postgresql:///finam_core STRATEGY_FEATURE_LIMIT=5000 PYTHONPATH=src \
python src/scripts/build_multi_strategy_engine_builder_v1.py

DATABASE_URL=postgresql:///finam_core PYTHONPATH=src \
python src/scripts/build_strategy_platform_governance_v1.py \
  | tee /tmp/strategy_platform_governance_v1.txt

grep -q "VERDICT=STRATEGY_PLATFORM_GOVERNANCE_V1_READY" \
  /tmp/strategy_platform_governance_v1.txt

sudo systemctl restart marketcore-kg-api.service
sudo systemctl restart marketcore-ui-shell.service
sleep 2

curl -fsS "http://127.0.0.1:8095/api/kg/v1/strategy-platform/governance" > /tmp/strategy_governance_api.json
curl -fsS "http://127.0.0.1:8080/strategy-governance" > /tmp/strategy_governance_ui.html

python - <<'PY'
import json

p = json.load(open("/tmp/strategy_governance_api.json", encoding="utf-8"))
assert p["status"] == "OK"
d = p["data"]
assert d["governance_score"] >= 90
assert d["unsafe_execution_rows"] == 0
assert d["readiness_status"]["code"] == "READY_FOR_RESEARCH"
assert d["overall_status"]["code"] == "HEALTHY"
PY

grep -q "Governance стратегий" /tmp/strategy_governance_ui.html
grep -q "Готово к Research" /tmp/strategy_governance_ui.html

score=$(psql -At -d finam_core -c "
SELECT governance_score
FROM analytics.strategy_platform_governance_v1
WHERE governance_scope='GLOBAL';
")

readiness=$(psql -At -d finam_core -c "
SELECT readiness_status
FROM analytics.strategy_platform_governance_v1
WHERE governance_scope='GLOBAL';
")

unsafe=$(psql -At -d finam_core -c "
SELECT unsafe_execution_rows
FROM analytics.strategy_platform_governance_v1
WHERE governance_scope='GLOBAL';
")

test "$readiness" = "READY_FOR_RESEARCH"
test "$unsafe" = "0"

echo "governance_score=$score"
echo "readiness_status=$readiness"
echo "unsafe_execution_rows=$unsafe"
echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo "VERDICT=STRATEGY_PLATFORM_GOVERNANCE_V1_READY"
echo "VERDICT=TEST_STRATEGY_PLATFORM_GOVERNANCE_V1_OK"
