from __future__ import annotations

import os
import signal
import subprocess
import sys
import time

from finam_core.storage.postgres_logger import PostgresLogger


def load_active_symbols(limit: int) -> list[str]:
    sql = """
    select symbol
    from runtime_active_universe
    where is_enabled = true
      and strategy is not null
      and strategy <> ''
      and strategy <> 'NO_TRADE'
    order by priority desc, score desc, updated_at desc
    limit %s
    """

    pg = PostgresLogger()
    with pg._connect() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, (limit,))
            return [str(r[0]) for r in cur.fetchall()]


def start_worker(symbol: str, run_secs: int) -> subprocess.Popen:
    env = os.environ.copy()
    env["PYTHONPATH"] = env.get("PYTHONPATH", "src")
    env.setdefault("EXECUTION_MODE", "paper")
    env.setdefault("ENABLE_RUNTIME_ACTIVE_UNIVERSE_GATE", "1")

    cmd = [
        sys.executable,
        "src/scripts/run_market_pipeline.py",
        "--symbol",
        symbol,
        "--run-secs",
        str(run_secs),
    ]

    print(f"RUNTIME_EXECUTION_START symbol={symbol} cmd={' '.join(cmd)}", flush=True)
    return subprocess.Popen(cmd, env=env)


def main() -> int:
    max_symbols = int(os.getenv("RUNTIME_EXECUTION_MAX_SYMBOLS", "3"))
    worker_run_secs = int(os.getenv("RUNTIME_EXECUTION_WORKER_RUN_SECS", "60"))
    supervisor_secs = int(os.getenv("RUNTIME_EXECUTION_SUPERVISOR_SECS", "90"))

    symbols = load_active_symbols(max_symbols)
    print(f"RUNTIME_EXECUTION_ACTIVE_SYMBOLS symbols={','.join(symbols)} total={len(symbols)}", flush=True)

    workers: dict[str, subprocess.Popen] = {}

    for symbol in symbols:
        workers[symbol] = start_worker(symbol, worker_run_secs)

    deadline = time.time() + supervisor_secs

    try:
        while time.time() < deadline:
            for symbol, proc in list(workers.items()):
                code = proc.poll()
                if code is not None:
                    print(f"RUNTIME_EXECUTION_WORKER_EXIT symbol={symbol} code={code}", flush=True)
                    del workers[symbol]

            if not workers:
                break

            time.sleep(2)

    finally:
        for symbol, proc in workers.items():
            if proc.poll() is None:
                print(f"RUNTIME_EXECUTION_STOP symbol={symbol}", flush=True)
                proc.send_signal(signal.SIGTERM)

        for _, proc in workers.items():
            try:
                proc.wait(timeout=10)
            except subprocess.TimeoutExpired:
                proc.kill()

    print("OK: runtime execution engine finished", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
