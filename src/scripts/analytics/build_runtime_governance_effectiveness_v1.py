from __future__ import annotations

import argparse
import subprocess

import psycopg
from psycopg.rows import dict_row

from finam_core.analytics.statistics_repository import build_psycopg_url


SOURCE = "paper_pipeline_phase2_runtime"


SUMMARY_SQL = """
SELECT
    count(*) AS total_rows,
    count(*) FILTER (WHERE allowed = true) AS allowed_rows,
    count(*) FILTER (WHERE allowed = false) AS blocked_rows,
    count(*) FILTER (WHERE action = 'ALLOW') AS allow_action_rows,
    count(*) FILTER (WHERE action = 'SOFT_BLOCK') AS soft_block_rows,
    count(*) FILTER (WHERE action = 'FAILED_OPEN') AS failed_open_rows,
    round(avg(expectancy_points)::numeric, 6) AS avg_expectancy_points,
    min(created_at) AS first_event_ts,
    max(created_at) AS last_event_ts
FROM runtime_governance_live_accumulation_v1
WHERE raw_json->>'source' = %(source)s
  AND created_at >= now() - (%(window_hours)s * interval '1 hour');
"""


SESSION_SIDE_SQL = """
SELECT
    hour_msk,
    side,
    count(*) AS total_rows,
    count(*) FILTER (WHERE allowed = true) AS allowed_rows,
    count(*) FILTER (WHERE allowed = false) AS blocked_rows,
    round(
        (
            count(*) FILTER (WHERE allowed = true)::numeric
            / NULLIF(count(*), 0)
        ),
        6
    ) AS allow_rate,
    round(avg(expectancy_points)::numeric, 6) AS avg_expectancy_points,
    min(expectancy_points) AS min_expectancy_points,
    max(expectancy_points) AS max_expectancy_points
FROM runtime_governance_live_accumulation_v1
WHERE raw_json->>'source' = %(source)s
  AND created_at >= now() - (%(window_hours)s * interval '1 hour')
GROUP BY hour_msk, side
ORDER BY hour_msk, side;
"""


REASON_SQL = """
SELECT
    action,
    reason,
    session_action,
    strict_reason,
    decay_state,
    count(*) AS total_rows,
    count(*) FILTER (WHERE allowed = true) AS allowed_rows,
    count(*) FILTER (WHERE allowed = false) AS blocked_rows,
    round(avg(expectancy_points)::numeric, 6) AS avg_expectancy_points
FROM runtime_governance_live_accumulation_v1
WHERE raw_json->>'source' = %(source)s
  AND created_at >= now() - (%(window_hours)s * interval '1 hour')
GROUP BY action, reason, session_action, strict_reason, decay_state
ORDER BY total_rows DESC, action, reason
LIMIT 30;
"""


SYMBOL_SQL = """
SELECT
    symbol,
    side,
    count(*) AS total_rows,
    count(*) FILTER (WHERE allowed = true) AS allowed_rows,
    count(*) FILTER (WHERE allowed = false) AS blocked_rows,
    round(avg(expectancy_points)::numeric, 6) AS avg_expectancy_points,
    max(created_at) AS last_event_ts
FROM runtime_governance_live_accumulation_v1
WHERE raw_json->>'source' = %(source)s
  AND created_at >= now() - (%(window_hours)s * interval '1 hour')
GROUP BY symbol, side
ORDER BY total_rows DESC, symbol, side
LIMIT 30;
"""


KPI_SQL = """
SELECT
    count(*) AS total_rows,
    count(*) FILTER (WHERE allowed = true) AS allowed_rows,
    count(*) FILTER (WHERE allowed = false) AS blocked_rows,

    coalesce(sum(
        CASE
            WHEN allowed = false AND expectancy_points < 0
            THEN abs(expectancy_points)
            ELSE 0
        END
    ), 0)::float AS saved_loss_points,

    coalesce(sum(
        CASE
            WHEN allowed = false AND expectancy_points > 0
            THEN expectancy_points
            ELSE 0
        END
    ), 0)::float AS missed_profit_points,

    coalesce(avg(expectancy_points) FILTER (WHERE allowed = true), 0)::float AS allowed_avg_expectancy_points,
    coalesce(avg(expectancy_points) FILTER (WHERE allowed = false), 0)::float AS blocked_avg_expectancy_points
FROM runtime_governance_live_accumulation_v1
WHERE raw_json->>'source' = %(source)s
  AND created_at >= now() - (%(window_hours)s * interval '1 hour');
"""


SYMBOL_ALPHA_SQL = """
SELECT
    symbol,
    side,
    count(*) AS total_rows,
    count(*) FILTER (WHERE allowed = true) AS allowed_rows,
    count(*) FILTER (WHERE allowed = false) AS blocked_rows,

    coalesce(sum(
        CASE
            WHEN allowed = false AND expectancy_points < 0
            THEN abs(expectancy_points)
            ELSE 0
        END
    ), 0)::float AS saved_loss_points,

    coalesce(sum(
        CASE
            WHEN allowed = false AND expectancy_points > 0
            THEN expectancy_points
            ELSE 0
        END
    ), 0)::float AS missed_profit_points
FROM runtime_governance_live_accumulation_v1
WHERE raw_json->>'source' = %(source)s
  AND created_at >= now() - (%(window_hours)s * interval '1 hour')
GROUP BY symbol, side
ORDER BY (coalesce(sum(CASE WHEN allowed = false AND expectancy_points < 0 THEN abs(expectancy_points) ELSE 0 END), 0) - coalesce(sum(CASE WHEN allowed = false AND expectancy_points > 0 THEN expectancy_points ELSE 0 END), 0)) DESC, count(*) DESC, symbol, side;
"""


SESSION_ALPHA_SQL = """
SELECT
    hour_msk,
    side,
    count(*) AS total_rows,
    count(*) FILTER (WHERE allowed = true) AS allowed_rows,
    count(*) FILTER (WHERE allowed = false) AS blocked_rows,

    coalesce(sum(
        CASE
            WHEN allowed = false AND expectancy_points < 0
            THEN abs(expectancy_points)
            ELSE 0
        END
    ), 0)::float AS saved_loss_points,

    coalesce(sum(
        CASE
            WHEN allowed = false AND expectancy_points > 0
            THEN expectancy_points
            ELSE 0
        END
    ), 0)::float AS missed_profit_points
FROM runtime_governance_live_accumulation_v1
WHERE raw_json->>'source' = %(source)s
  AND created_at >= now() - (%(window_hours)s * interval '1 hour')
GROUP BY hour_msk, side
ORDER BY (coalesce(sum(CASE WHEN allowed = false AND expectancy_points < 0 THEN abs(expectancy_points) ELSE 0 END), 0) - coalesce(sum(CASE WHEN allowed = false AND expectancy_points > 0 THEN expectancy_points ELSE 0 END), 0)) DESC, hour_msk, side;
"""


def git_clean() -> bool:
    result = subprocess.run(
        ["git", "status", "--short"],
        capture_output=True,
        text=True,
        check=False,
    )
    return result.stdout.strip() == ""


def quality_status(total_rows: int, avg_expectancy: float | None, blocked_rows: int) -> str:
    if total_rows == 0:
        return "NO_DATA"

    if total_rows < 30:
        return "INSUFFICIENT_SAMPLE"

    if avg_expectancy is None:
        return "NO_EXPECTANCY"

    if blocked_rows > 0 and avg_expectancy < 0:
        return "GOVERNANCE_BLOCKING_NEGATIVE_EDGE"

    if avg_expectancy >= 0:
        return "GOVERNANCE_NEUTRAL_OR_POSITIVE"

    return "GOVERNANCE_REVIEW_REQUIRED"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--window-hours", type=int, default=24 * 7)
    args = parser.parse_args()

    with psycopg.connect(build_psycopg_url(), row_factory=dict_row) as conn:
        with conn.cursor() as cur:
            params = {
                "source": SOURCE,
                "window_hours": args.window_hours,
            }

            cur.execute(SUMMARY_SQL, params)
            summary = dict(cur.fetchone())

            cur.execute(SESSION_SIDE_SQL, params)
            session_rows = [dict(row) for row in cur.fetchall()]

            cur.execute(REASON_SQL, params)
            reason_rows = [dict(row) for row in cur.fetchall()]

            cur.execute(SYMBOL_SQL, params)
            symbol_rows = [dict(row) for row in cur.fetchall()]

            cur.execute(KPI_SQL, params)
            kpi = dict(cur.fetchone())

            cur.execute(SYMBOL_ALPHA_SQL, params)
            symbol_alpha_rows = [dict(row) for row in cur.fetchall()]

            cur.execute(SESSION_ALPHA_SQL, params)
            session_alpha_rows = [dict(row) for row in cur.fetchall()]

    total_rows = int(summary["total_rows"] or 0)
    blocked_rows = int(summary["blocked_rows"] or 0)
    avg_expectancy_raw = summary["avg_expectancy_points"]
    avg_expectancy = float(avg_expectancy_raw) if avg_expectancy_raw is not None else None

    status = quality_status(
        total_rows=total_rows,
        avg_expectancy=avg_expectancy,
        blocked_rows=blocked_rows,
    )

    saved_loss = float(kpi.get("saved_loss_points") or 0.0)
    missed_profit = float(kpi.get("missed_profit_points") or 0.0)
    governance_alpha = saved_loss - missed_profit

    print("RUNTIME_GOVERNANCE_EFFECTIVENESS_V1")
    print(
        "RUNTIME_GOVERNANCE_EFFECTIVENESS_SUMMARY",
        f"status={status}",
        f"git_clean={git_clean()}",
        f"source={SOURCE}",
        f"window_hours={args.window_hours}",
        f"total_rows={summary['total_rows']}",
        f"allowed_rows={summary['allowed_rows']}",
        f"blocked_rows={summary['blocked_rows']}",
        f"allow_action_rows={summary['allow_action_rows']}",
        f"soft_block_rows={summary['soft_block_rows']}",
        f"failed_open_rows={summary['failed_open_rows']}",
        f"avg_expectancy_points={summary['avg_expectancy_points']}",
        f"first_event_ts={summary['first_event_ts']}",
        f"last_event_ts={summary['last_event_ts']}",
        flush=True,
    )

    print(
        "RUNTIME_GOVERNANCE_EFFECTIVENESS_KPI",
        f"saved_loss_points={saved_loss:.6f}",
        f"missed_profit_points={missed_profit:.6f}",
        f"governance_alpha_points={governance_alpha:.6f}",
        f"allowed_avg_expectancy_points={float(kpi.get('allowed_avg_expectancy_points') or 0.0):.6f}",
        f"blocked_avg_expectancy_points={float(kpi.get('blocked_avg_expectancy_points') or 0.0):.6f}",
        f"total_rows={kpi.get('total_rows')}",
        f"allowed_rows={kpi.get('allowed_rows')}",
        f"blocked_rows={kpi.get('blocked_rows')}",
        flush=True,
    )

    for row in session_rows:
        print(
            "RUNTIME_GOVERNANCE_EFFECTIVENESS_SESSION_SIDE",
            f"hour_msk={row['hour_msk']}",
            f"side={row['side']}",
            f"total_rows={row['total_rows']}",
            f"allowed_rows={row['allowed_rows']}",
            f"blocked_rows={row['blocked_rows']}",
            f"allow_rate={row['allow_rate']}",
            f"avg_expectancy_points={row['avg_expectancy_points']}",
            f"min_expectancy_points={row['min_expectancy_points']}",
            f"max_expectancy_points={row['max_expectancy_points']}",
            flush=True,
        )

    for row in reason_rows:
        print(
            "RUNTIME_GOVERNANCE_EFFECTIVENESS_REASON",
            f"action={row['action']}",
            f"reason={row['reason']}",
            f"session_action={row['session_action']}",
            f"strict_reason={row['strict_reason']}",
            f"decay_state={row['decay_state']}",
            f"total_rows={row['total_rows']}",
            f"allowed_rows={row['allowed_rows']}",
            f"blocked_rows={row['blocked_rows']}",
            f"avg_expectancy_points={row['avg_expectancy_points']}",
            flush=True,
        )

    for row in symbol_rows:
        print(
            "RUNTIME_GOVERNANCE_EFFECTIVENESS_SYMBOL",
            f"symbol={row['symbol']}",
            f"side={row['side']}",
            f"total_rows={row['total_rows']}",
            f"allowed_rows={row['allowed_rows']}",
            f"blocked_rows={row['blocked_rows']}",
            f"avg_expectancy_points={row['avg_expectancy_points']}",
            f"last_event_ts={row['last_event_ts']}",
            flush=True,
        )

    for row in symbol_alpha_rows:
        saved = float(row.get("saved_loss_points") or 0.0)
        missed = float(row.get("missed_profit_points") or 0.0)
        alpha = saved - missed
        print(
            "RUNTIME_GOVERNANCE_EFFECTIVENESS_SYMBOL_ALPHA",
            f"symbol={row['symbol']}",
            f"side={row['side']}",
            f"saved_loss_points={saved:.6f}",
            f"missed_profit_points={missed:.6f}",
            f"governance_alpha_points={alpha:.6f}",
            f"total_rows={row['total_rows']}",
            f"allowed_rows={row['allowed_rows']}",
            f"blocked_rows={row['blocked_rows']}",
            flush=True,
        )

    for row in session_alpha_rows:
        saved = float(row.get("saved_loss_points") or 0.0)
        missed = float(row.get("missed_profit_points") or 0.0)
        alpha = saved - missed
        print(
            "RUNTIME_GOVERNANCE_EFFECTIVENESS_SESSION_ALPHA",
            f"hour_msk={row['hour_msk']}",
            f"side={row['side']}",
            f"saved_loss_points={saved:.6f}",
            f"missed_profit_points={missed:.6f}",
            f"governance_alpha_points={alpha:.6f}",
            f"total_rows={row['total_rows']}",
            f"allowed_rows={row['allowed_rows']}",
            f"blocked_rows={row['blocked_rows']}",
            flush=True,
        )

    print(
        f"RUNTIME_GOVERNANCE_EFFECTIVENESS_V1_OK status={status}",
        flush=True,
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
