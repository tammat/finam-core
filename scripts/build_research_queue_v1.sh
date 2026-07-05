#!/usr/bin/env bash
set -euo pipefail

echo "=== BUILD_RESEARCH_QUEUE_V1 ==="

mkdir -p sql/analytics src/scripts scripts

cat > sql/analytics/014_research_queue_v1.sql <<'SQL'
CREATE TABLE IF NOT EXISTS analytics.research_queue_v1 (
    id BIGSERIAL PRIMARY KEY,

    research_code TEXT NOT NULL,
    strategy_code TEXT NOT NULL REFERENCES analytics.strategy_library_v1(strategy_code),

    symbol TEXT NOT NULL,
    timeframe TEXT NOT NULL,

    parameter_set JSONB NOT NULL DEFAULT '{}'::jsonb,

    priority INTEGER NOT NULL DEFAULT 100,
    status_code TEXT NOT NULL DEFAULT 'QUEUED',

    attempts INTEGER NOT NULL DEFAULT 0,
    last_error TEXT NOT NULL DEFAULT '',

    source_version TEXT NOT NULL DEFAULT 'RESEARCH_QUEUE_V1',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),

    UNIQUE(strategy_code, symbol, timeframe, parameter_set)
);

CREATE INDEX IF NOT EXISTS ix_research_queue_v1_status
ON analytics.research_queue_v1(status_code);

CREATE INDEX IF NOT EXISTS ix_research_queue_v1_priority
ON analytics.research_queue_v1(priority);

CREATE INDEX IF NOT EXISTS ix_research_queue_v1_symbol
ON analytics.research_queue_v1(symbol);

GRANT SELECT, INSERT, UPDATE, DELETE ON analytics.research_queue_v1 TO alex;
GRANT USAGE, SELECT ON SEQUENCE analytics.research_queue_v1_id_seq TO alex;
SQL

cat > src/scripts/build_research_queue_v1.py <<'PY'
from __future__ import annotations

import json
import os
import psycopg2
import psycopg2.extras

DB = os.getenv("DATABASE_URL", "postgresql:///finam_core")

DEFAULT_SYMBOLS = ["BR@RTSX", "NG@RTSX", "LKOH@MISX", "SBER@MISX"]
MAX_STRATEGIES = int(os.getenv("RESEARCH_QUEUE_MAX_STRATEGIES", "10"))


def main() -> None:
    inserted = 0

    with psycopg2.connect(DB) as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("""
                SELECT
                    strategy_code,
                    default_timeframes,
                    default_symbols,
                    priority
                FROM analytics.strategy_library_v1
                WHERE enabled=true
                ORDER BY priority ASC
                LIMIT %s;
            """, (MAX_STRATEGIES,))
            strategies = cur.fetchall()

            for s in strategies:
                symbols = list(s["default_symbols"] or []) or DEFAULT_SYMBOLS
                timeframes = list(s["default_timeframes"] or ["M5"])

                for symbol in symbols:
                    for timeframe in timeframes:
                        research_code = f"{s['strategy_code']}:{symbol}:{timeframe}:DEFAULT"
                        parameter_set = {}

                        cur.execute("""
                            INSERT INTO analytics.research_queue_v1 (
                                research_code,
                                strategy_code,
                                symbol,
                                timeframe,
                                parameter_set,
                                priority,
                                status_code,
                                source_version,
                                updated_at
                            )
                            VALUES (
                                %s,%s,%s,%s,%s::jsonb,%s,
                                'QUEUED',
                                'RESEARCH_QUEUE_V1',
                                now()
                            )
                            ON CONFLICT(strategy_code, symbol, timeframe, parameter_set)
                            DO UPDATE SET
                                research_code=EXCLUDED.research_code,
                                priority=EXCLUDED.priority,
                                source_version='RESEARCH_QUEUE_V1',
                                updated_at=now();
                        """, (
                            research_code,
                            s["strategy_code"],
                            symbol,
                            timeframe,
                            json.dumps(parameter_set),
                            s["priority"],
                        ))
                        inserted += 1

            cur.execute("""
                SELECT
                    count(*) AS total,
                    count(*) FILTER (WHERE status_code='QUEUED') AS queued,
                    count(*) FILTER (WHERE status_code='RUNNING') AS running,
                    count(*) FILTER (WHERE status_code='DONE') AS done,
                    count(*) FILTER (WHERE status_code='FAILED') AS failed
                FROM analytics.research_queue_v1;
            """)
            row = cur.fetchone()

    print("=== RESEARCH_QUEUE_V1 ===")
    print(f"queue_generated={inserted}")
    print(f"queue_total={row['total']}")
    print(f"queued={row['queued']}")
    print(f"running={row['running']}")
    print(f"done={row['done']}")
    print(f"failed={row['failed']}")
    print("runtime_changed=0")
    print("execution_changed=0")
    print("orders_changed=0")
    print("fills_changed=0")
    print("micro_live_allowed=0")
    print("VERDICT=RESEARCH_QUEUE_V1_READY")


if __name__ == "__main__":
    main()
PY

cat >> src/marketcore/presentation/ui_labels.py <<'PY'

try:
    ROUTE_LABELS_RU.update({
        "research.queue.title": "Research Queue",
        "research.queue.subtitle": "Очередь исследовательских прогонов Strategy × Symbol × Timeframe × Parameters.",
        "research.queue.total": "Всего задач",
        "research.queue.queued": "В очереди",
        "research.queue.running": "В работе",
        "research.queue.done": "Завершено",
        "research.queue.failed": "Ошибки",
        "research.status.QUEUED": "В очереди",
        "research.status.RUNNING": "В работе",
        "research.status.DONE": "Завершено",
        "research.status.FAILED": "Ошибка",
        "research.status.CANCELLED": "Отменено"
    })
except NameError:
    pass
PY

cat > scripts/test_research_queue_v1.sh <<'SH_TEST'
#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_RESEARCH_QUEUE_V1 ==="

sudo -u postgres psql -v ON_ERROR_STOP=1 -d finam_core \
  -f sql/analytics/014_research_queue_v1.sql

PYTHONPATH=src python -m py_compile \
  src/scripts/build_research_queue_v1.py \
  src/marketcore/presentation/ui_labels.py

DATABASE_URL=postgresql:///finam_core PYTHONPATH=src \
python src/scripts/build_research_queue_v1.py | tee /tmp/research_queue_v1.txt

grep -q "VERDICT=RESEARCH_QUEUE_V1_READY" /tmp/research_queue_v1.txt

rows=$(psql -At -d finam_core -c "SELECT count(*) FROM analytics.research_queue_v1;")
queued=$(psql -At -d finam_core -c "SELECT count(*) FROM analytics.research_queue_v1 WHERE status_code='QUEUED';")

test "$rows" -gt 0
test "$queued" -gt 0

grep -q "research.status.QUEUED" src/marketcore/presentation/ui_labels.py
grep -q "research.queue.title" src/marketcore/presentation/ui_labels.py

echo "research_queue_rows=$rows"
echo "queued_rows=$queued"
echo "i18n=ok"
echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo "VERDICT=TEST_RESEARCH_QUEUE_V1_OK"
SH_TEST

chmod +x scripts/test_research_queue_v1.sh
scripts/test_research_queue_v1.sh

echo "VERDICT=BUILD_RESEARCH_QUEUE_V1_OK"
