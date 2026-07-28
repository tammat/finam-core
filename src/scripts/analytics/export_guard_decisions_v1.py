from __future__ import annotations

import json
import os
from pathlib import Path

import psycopg
from psycopg.rows import dict_row

from finam_core.analytics.statistics_repository import build_psycopg_url


OUTPUT_PATH = Path("config/generated/guard_decisions_v1.json")


def export_guard_decisions() -> int:
    database_url = os.getenv("DATABASE_URL") or build_psycopg_url()

    with psycopg.connect(database_url, row_factory=dict_row) as conn:
        with conn.cursor() as cur:
            cur.execute("""
            SELECT
                symbol,
                strategy,
                timeframe,
                session_type,
                regime,
                volatility_regime,
                closed_total,
                winrate,
                profit_factor,
                expectancy,
                guard_decision,
                guard_reason,
                calculated_at
            FROM guard_decision_report_v1
            ORDER BY symbol, strategy, timeframe, session_type, regime, volatility_regime
            """)
            rows = [dict(r) for r in cur.fetchall()]

    payload = {
        "version": "guard_decisions_v1",
        "source": "guard_decision_report_v1",
        "items": [
            {
                **r,
                "calculated_at": r["calculated_at"].isoformat() if r.get("calculated_at") else None,
            }
            for r in rows
        ],
    }

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    # The exporter can run under an administrative account while the market
    # pipeline runs as an unprivileged service user. Keep the generated
    # contract readable after every atomic refresh.
    OUTPUT_PATH.chmod(0o644)

    print(f"GUARD_DECISIONS_EXPORT_V1_OK path={OUTPUT_PATH} rows={len(rows)}", flush=True)
    return len(rows)


def main() -> int:
    export_guard_decisions()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
