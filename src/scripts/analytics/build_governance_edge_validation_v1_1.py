from __future__ import annotations

import argparse
import subprocess

import psycopg
from psycopg.rows import dict_row

from finam_core.analytics.statistics_repository import build_psycopg_url


SOURCE = "paper_pipeline_phase2_runtime"


def sample_quality(rows: int) -> str:
    if rows < 50:
        return "LOW"
    if rows < 150:
        return "MEDIUM"
    if rows < 300:
        return "HIGH"
    return "VERY_HIGH"


SUMMARY_SQL = """
select
    count(*)::int as baseline_rows,
    count(*) filter (where allowed is true)::int as governance_rows,
    count(*) filter (where allowed is false)::int as blocked_rows,
    avg(expectancy_points)::float as baseline_expectancy,
    avg(expectancy_points) filter (where allowed is true)::float as governance_expectancy,
    coalesce(sum(case when allowed is false and expectancy_points < 0 then abs(expectancy_points) else 0 end), 0)::float as saved_loss_points,
    coalesce(sum(case when allowed is false and expectancy_points > 0 then expectancy_points else 0 end), 0)::float as missed_profit_points
from runtime_governance_live_accumulation_v1
where raw_json->>'source' = %(source)s
  and created_at >= now() - (%(window_hours)s * interval '1 hour');
"""


SYMBOL_SQL = """
select
    symbol,
    side,
    count(*)::int as baseline_rows,
    count(*) filter (where allowed is true)::int as governance_rows,
    count(*) filter (where allowed is false)::int as blocked_rows,
    avg(expectancy_points)::float as baseline_expectancy,
    avg(expectancy_points) filter (where allowed is true)::float as governance_expectancy,
    coalesce(sum(case when allowed is false and expectancy_points < 0 then abs(expectancy_points) else 0 end), 0)::float as saved_loss_points,
    coalesce(sum(case when allowed is false and expectancy_points > 0 then expectancy_points else 0 end), 0)::float as missed_profit_points
from runtime_governance_live_accumulation_v1
where raw_json->>'source' = %(source)s
  and created_at >= now() - (%(window_hours)s * interval '1 hour')
group by symbol, side
order by baseline_rows desc, symbol, side;
"""


REASON_SQL = """
select
    action,
    reason,
    session_action,
    strict_reason,
    count(*)::int as total_rows,
    coalesce(sum(case when allowed is false and expectancy_points < 0 then abs(expectancy_points) else 0 end), 0)::float as saved_loss_points,
    coalesce(sum(case when allowed is false and expectancy_points > 0 then expectancy_points else 0 end), 0)::float as missed_profit_points
from runtime_governance_live_accumulation_v1
where raw_json->>'source' = %(source)s
  and created_at >= now() - (%(window_hours)s * interval '1 hour')
group by action, reason, session_action, strict_reason
order by total_rows desc;
"""



SIDE_SQL = """
select
    side,
    count(*)::int as baseline_rows,
    count(*) filter (where allowed is true)::int as governance_rows,
    count(*) filter (where allowed is false)::int as blocked_rows,
    avg(expectancy_points)::float as baseline_expectancy,
    avg(expectancy_points) filter (where allowed is true)::float as governance_expectancy,
    coalesce(sum(case when allowed is false and expectancy_points < 0 then abs(expectancy_points) else 0 end), 0)::float as saved_loss_points,
    coalesce(sum(case when allowed is false and expectancy_points > 0 then expectancy_points else 0 end), 0)::float as missed_profit_points
from runtime_governance_live_accumulation_v1
where raw_json->>'source' = %(source)s
  and created_at >= now() - (%(window_hours)s * interval '1 hour')
group by side
order by side;
"""


ALPHA_RANK_SQL = """
select
    symbol,
    side,
    count(*)::int as baseline_rows,
    count(*) filter (where allowed is true)::int as governance_rows,
    count(*) filter (where allowed is false)::int as blocked_rows,
    coalesce(sum(case when allowed is false and expectancy_points < 0 then abs(expectancy_points) else 0 end), 0)::float as saved_loss_points,
    coalesce(sum(case when allowed is false and expectancy_points > 0 then expectancy_points else 0 end), 0)::float as missed_profit_points
from runtime_governance_live_accumulation_v1
where raw_json->>'source' = %(source)s
  and created_at >= now() - (%(window_hours)s * interval '1 hour')
group by symbol, side
order by
    (
        coalesce(sum(case when allowed is false and expectancy_points < 0 then abs(expectancy_points) else 0 end), 0)
        -
        coalesce(sum(case when allowed is false and expectancy_points > 0 then expectancy_points else 0 end), 0)
    ) desc,
    baseline_rows desc,
    symbol,
    side
limit 30;
"""


def git_clean() -> bool:
    result = subprocess.run(["git", "status", "--short"], capture_output=True, text=True, check=False)
    return result.stdout.strip() == ""


def fmt(value) -> str:
    if value is None:
        return "нет_данных"
    return f"{float(value):.6f}"


def alpha(saved_loss: float, missed_profit: float) -> float:
    return float(saved_loss or 0.0) - float(missed_profit or 0.0)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--window-hours", type=int, default=24 * 7)
    args = parser.parse_args()

    params = {"source": SOURCE, "window_hours": args.window_hours}

    with psycopg.connect(build_psycopg_url(), row_factory=dict_row) as conn:
        with conn.cursor() as cur:
            cur.execute(SUMMARY_SQL, params)
            summary = dict(cur.fetchone() or {})

            cur.execute(SYMBOL_SQL, params)
            symbols = [dict(row) for row in cur.fetchall()]

            cur.execute(REASON_SQL, params)
            reasons = [dict(row) for row in cur.fetchall()]

            cur.execute(SIDE_SQL, params)
            side_rows = [dict(row) for row in cur.fetchall()]

            cur.execute(ALPHA_RANK_SQL, params)
            alpha_rank_rows = [dict(row) for row in cur.fetchall()]

    saved = float(summary.get("saved_loss_points") or 0.0)
    missed = float(summary.get("missed_profit_points") or 0.0)
    gov_alpha = alpha(saved, missed)
    total_loss_or_missed = saved + missed
    governance_efficiency = saved / total_loss_or_missed if total_loss_or_missed > 0 else 0.0
    baseline_rows = int(summary.get("baseline_rows") or 0)

    baseline_exp = summary.get("baseline_expectancy")
    governance_exp = summary.get("governance_expectancy")
    delta_exp = None
    if baseline_exp is not None and governance_exp is not None:
        delta_exp = float(governance_exp) - float(baseline_exp)

    print("GOVERNANCE_EDGE_VALIDATION_V1_1", flush=True)

    print(
        "GOVERNANCE_EDGE_SAMPLE_QUALITY",
        f"baseline_rows={baseline_rows}",
        f"quality={sample_quality(baseline_rows)}",
        flush=True,
    )

    print(
        "GOVERNANCE_EDGE_EFFICIENCY",
        f"saved_loss_points={saved:.6f}",
        f"missed_profit_points={missed:.6f}",
        f"governance_alpha_points={gov_alpha:.6f}",
        f"efficiency={governance_efficiency:.6f}",
        flush=True,
    )

    print(
        "GOVERNANCE_EDGE_VALIDATION_SUMMARY",
        f"git_clean={git_clean()}",
        f"source={SOURCE}",
        f"window_hours={args.window_hours}",
        f"baseline_rows={summary.get('baseline_rows')}",
        f"governance_rows={summary.get('governance_rows')}",
        f"blocked_rows={summary.get('blocked_rows')}",
        f"baseline_expectancy={fmt(baseline_exp)}",
        f"governance_expectancy={fmt(governance_exp)}",
        f"delta_expectancy={fmt(delta_exp)}",
        f"saved_loss_points={saved:.6f}",
        f"missed_profit_points={missed:.6f}",
        f"governance_alpha_points={gov_alpha:.6f}",
        flush=True,
    )

    for row in symbols:
        saved_s = float(row.get("saved_loss_points") or 0.0)
        missed_s = float(row.get("missed_profit_points") or 0.0)
        base = row.get("baseline_expectancy")
        gov = row.get("governance_expectancy")
        delta = float(gov) - float(base) if base is not None and gov is not None else None

        print(
            "GOVERNANCE_EDGE_SYMBOL",
            f"symbol={row.get('symbol')}",
            f"side={row.get('side')}",
            f"baseline_rows={row.get('baseline_rows')}",
            f"governance_rows={row.get('governance_rows')}",
            f"blocked_rows={row.get('blocked_rows')}",
            f"baseline_expectancy={fmt(base)}",
            f"governance_expectancy={fmt(gov)}",
            f"delta_expectancy={fmt(delta)}",
            f"saved_loss_points={saved_s:.6f}",
            f"missed_profit_points={missed_s:.6f}",
            f"governance_alpha_points={alpha(saved_s, missed_s):.6f}",
            flush=True,
        )

    for row in reasons:
        saved_r = float(row.get("saved_loss_points") or 0.0)
        missed_r = float(row.get("missed_profit_points") or 0.0)
        print(
            "GOVERNANCE_EDGE_REASON",
            f"action={row.get('action')}",
            f"reason={row.get('reason')}",
            f"session_action={row.get('session_action')}",
            f"strict_reason={row.get('strict_reason')}",
            f"total_rows={row.get('total_rows')}",
            f"saved_loss_points={saved_r:.6f}",
            f"missed_profit_points={missed_r:.6f}",
            f"governance_alpha_points={alpha(saved_r, missed_r):.6f}",
            flush=True,
        )

    for row in side_rows:
        saved_side = float(row.get("saved_loss_points") or 0.0)
        missed_side = float(row.get("missed_profit_points") or 0.0)
        base = row.get("baseline_expectancy")
        gov = row.get("governance_expectancy")
        delta = float(gov) - float(base) if base is not None and gov is not None else None

        print(
            "GOVERNANCE_EDGE_SIDE",
            f"side={row.get('side')}",
            f"baseline_rows={row.get('baseline_rows')}",
            f"governance_rows={row.get('governance_rows')}",
            f"blocked_rows={row.get('blocked_rows')}",
            f"sample_quality={sample_quality(int(row.get('baseline_rows') or 0))}",
            f"baseline_expectancy={fmt(base)}",
            f"governance_expectancy={fmt(gov)}",
            f"delta_expectancy={fmt(delta)}",
            f"saved_loss_points={saved_side:.6f}",
            f"missed_profit_points={missed_side:.6f}",
            f"governance_alpha_points={alpha(saved_side, missed_side):.6f}",
            flush=True,
        )

    for idx, row in enumerate(alpha_rank_rows, start=1):
        saved_rank = float(row.get("saved_loss_points") or 0.0)
        missed_rank = float(row.get("missed_profit_points") or 0.0)

        print(
            "GOVERNANCE_EDGE_ALPHA_RANK",
            f"rank={idx}",
            f"symbol={row.get('symbol')}",
            f"side={row.get('side')}",
            f"baseline_rows={row.get('baseline_rows')}",
            f"governance_rows={row.get('governance_rows')}",
            f"blocked_rows={row.get('blocked_rows')}",
            f"sample_quality={sample_quality(int(row.get('baseline_rows') or 0))}",
            f"saved_loss_points={saved_rank:.6f}",
            f"missed_profit_points={missed_rank:.6f}",
            f"governance_alpha_points={alpha(saved_rank, missed_rank):.6f}",
            flush=True,
        )

    print("GOVERNANCE_EDGE_VALIDATION_V1_1_OK", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
