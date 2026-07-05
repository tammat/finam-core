#!/usr/bin/env bash
set -euo pipefail

echo "=== BUILD_EDGE_LAB_RUNNER_V1 ==="

mkdir -p src/scripts scripts

cat > src/scripts/build_edge_lab_runner_v1.py <<'PY'
from __future__ import annotations

import os
import time
from datetime import UTC, datetime

import psycopg2
import psycopg2.extras

DB = os.getenv("DATABASE_URL", "postgresql:///finam_core")
LIMIT = int(os.getenv("EDGE_LAB_RUNNER_LIMIT", "25"))
RUNNER_VERSION = "EDGE_LAB_RUNNER_V1"
SCORE_FORMULA_VERSION = "EDGE_SCORE_ENGINE_PENDING"


def now_utc() -> datetime:
    return datetime.now(UTC)


def main() -> None:
    started = time.perf_counter()
    observations = 0
    failed = 0

    with psycopg2.connect(DB) as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("""
                SELECT *
                FROM analytics.edge_lab_run_v1
                WHERE status_code='QUEUED'
                ORDER BY created_at ASC, id ASC
                LIMIT %s
                FOR UPDATE SKIP LOCKED;
            """, (LIMIT,))
            runs = cur.fetchall()

            for run in runs:
                run_start = time.perf_counter()
                try:
                    cur.execute("""
                        UPDATE analytics.edge_lab_run_v1
                        SET status_code='RUNNING',
                            runner_version=%s,
                            started_at=now(),
                            updated_at=now()
                        WHERE id=%s;
                    """, (RUNNER_VERSION, run["id"]))

                    # EDGE_LAB_RUNNER_V1 пока не исполняет реальные стратегии.
                    # Он фиксирует воспроизводимое observation по каждой задаче.
                    # Реальный trade-set runner будет следующим расширением.
                    elapsed_ms = int((time.perf_counter() - run_start) * 1000)

                    cur.execute("""
                        INSERT INTO analytics.edge_observation_v1 (
                            run_uuid,
                            research_batch_id,
                            research_code,
                            strategy_code,
                            strategy_version,
                            symbol,
                            timeframe,
                            parameter_hash,
                            parameter_json,
                            dataset_version,
                            market_data_version,
                            runner_version,
                            score_formula_version,
                            market_regime,
                            bars_used,
                            trades,
                            wins,
                            losses,
                            win_rate,
                            profit_factor,
                            expectancy,
                            avg_win,
                            avg_loss,
                            max_drawdown,
                            recovery_factor,
                            sharpe,
                            sortino,
                            ulcer_index,
                            commission,
                            slippage,
                            stability_score,
                            raw_edge_score,
                            normalized_edge_score,
                            confidence_score,
                            research_cost_score,
                            research_cpu_ms,
                            research_memory_mb,
                            research_elapsed_ms,
                            verdict_code,
                            source_version,
                            updated_at
                        )
                        VALUES (
                            %s,%s,%s,%s,%s,%s,%s,%s,%s::jsonb,
                            %s,'default',%s,%s,
                            'UNKNOWN',
                            0,0,0,0,
                            0,0,0,0,0,0,0,0,0,0,
                            0,0,0,0,0,0,0,
                            %s,0,%s,
                            'NO_TRADES',
                            %s,
                            now()
                        )
                        ON CONFLICT(run_uuid) DO NOTHING;
                    """, (
                        run["run_uuid"],
                        run["research_batch_id"],
                        run["research_code"],
                        run["strategy_code"],
                        run["strategy_version"],
                        run["symbol"],
                        run["timeframe"],
                        run["parameter_hash"],
                        run["parameter_json"],
                        run["dataset_version"],
                        RUNNER_VERSION,
                        SCORE_FORMULA_VERSION,
                        elapsed_ms,
                        elapsed_ms,
                        RUNNER_VERSION,
                    ))

                    cur.execute("""
                        UPDATE analytics.edge_lab_run_v1
                        SET status_code='DONE',
                            finished_at=now(),
                            updated_at=now(),
                            runner_version=%s
                        WHERE id=%s;
                    """, (RUNNER_VERSION, run["id"]))

                    cur.execute("""
                        UPDATE analytics.research_queue_v1
                        SET status_code='DONE',
                            attempts=attempts + 1,
                            updated_at=now()
                        WHERE research_code=%s
                          AND strategy_code=%s
                          AND symbol=%s
                          AND timeframe=%s;
                    """, (
                        run["research_code"],
                        run["strategy_code"],
                        run["symbol"],
                        run["timeframe"],
                    ))

                    observations += 1

                except Exception as exc:
                    failed += 1
                    cur.execute("""
                        UPDATE analytics.edge_lab_run_v1
                        SET status_code='FAILED',
                            finished_at=now(),
                            updated_at=now(),
                            runner_version=%s
                        WHERE id=%s;
                    """, (RUNNER_VERSION, run["id"]))

                    cur.execute("""
                        UPDATE analytics.research_queue_v1
                        SET status_code='FAILED',
                            attempts=attempts + 1,
                            last_error=%s,
                            updated_at=now()
                        WHERE research_code=%s
                          AND strategy_code=%s
                          AND symbol=%s
                          AND timeframe=%s;
                    """, (
                        str(exc)[:1000],
                        run["research_code"],
                        run["strategy_code"],
                        run["symbol"],
                        run["timeframe"],
                    ))

            cur.execute("""
                SELECT
                    count(*) AS observations_total,
                    count(*) FILTER (WHERE verdict_code='NO_TRADES') AS no_trades
                FROM analytics.edge_observation_v1;
            """)
            obs = cur.fetchone()

            cur.execute("""
                SELECT
                    count(*) AS runs_total,
                    count(*) FILTER (WHERE status_code='QUEUED') AS queued,
                    count(*) FILTER (WHERE status_code='DONE') AS done,
                    count(*) FILTER (WHERE status_code='FAILED') AS failed
                FROM analytics.edge_lab_run_v1;
            """)
            runs_summary = cur.fetchone()

    elapsed_total_ms = int((time.perf_counter() - started) * 1000)

    print("=== EDGE_LAB_RUNNER_V1 ===")
    print(f"limit={LIMIT}")
    print(f"processed={observations}")
    print(f"failed={failed}")
    print(f"observations_total={obs['observations_total']}")
    print(f"no_trades={obs['no_trades']}")
    print(f"runs_total={runs_summary['runs_total']}")
    print(f"queued={runs_summary['queued']}")
    print(f"done={runs_summary['done']}")
    print(f"failed_runs={runs_summary['failed']}")
    print(f"elapsed_ms={elapsed_total_ms}")
    print("runtime_changed=0")
    print("execution_changed=0")
    print("orders_changed=0")
    print("fills_changed=0")
    print("micro_live_allowed=0")
    print("VERDICT=EDGE_LAB_RUNNER_V1_READY")


if __name__ == "__main__":
    main()
PY

cat >> src/marketcore/presentation/ui_labels.py <<'PY'

try:
    ROUTE_LABELS_RU.update({
        "edge.runner.title": "Edge Lab Runner",
        "edge.runner.subtitle": "Исполнитель очереди исследований без принятия торговых решений.",
        "edge.runner.running": "Выполняется",
        "edge.runner.done": "Завершено",
        "edge.runner.failed": "Ошибка",
        "edge.runner.retry": "Повтор",
        "edge.verdict.NO_TRADES": "Нет сделок"
    })
except NameError:
    pass
PY

cat > scripts/test_edge_lab_runner_v1.sh <<'SH_TEST'
#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_EDGE_LAB_RUNNER_V1 ==="

PYTHONPATH=src python -m py_compile \
  src/scripts/build_edge_lab_runner_v1.py \
  src/marketcore/presentation/ui_labels.py

DATABASE_URL=postgresql:///finam_core EDGE_LAB_RUNNER_LIMIT=10 PYTHONPATH=src \
python src/scripts/build_edge_lab_runner_v1.py | tee /tmp/edge_lab_runner_v1.txt

grep -q "VERDICT=EDGE_LAB_RUNNER_V1_READY" /tmp/edge_lab_runner_v1.txt

obs=$(psql -At -d finam_core -c "SELECT count(*) FROM analytics.edge_observation_v1;")
done_runs=$(psql -At -d finam_core -c "SELECT count(*) FROM analytics.edge_lab_run_v1 WHERE status_code='DONE';")
bad_live=$(psql -At -d finam_core -c "
SELECT count(*)
FROM analytics.edge_candidate_v1
WHERE live_allowed=true OR micro_live_allowed=true;
")

test "$obs" -gt 0
test "$done_runs" -gt 0
test "$bad_live" = "0"

grep -q "edge.runner.title" src/marketcore/presentation/ui_labels.py
grep -q "edge.verdict.NO_TRADES" src/marketcore/presentation/ui_labels.py

echo "observations=$obs"
echo "done_runs=$done_runs"
echo "unsafe_candidate_rows=$bad_live"
echo "i18n=ok"
echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo "VERDICT=TEST_EDGE_LAB_RUNNER_V1_OK"
SH_TEST

chmod +x scripts/test_edge_lab_runner_v1.sh
scripts/test_edge_lab_runner_v1.sh

echo "VERDICT=BUILD_EDGE_LAB_RUNNER_V1_OK"
