#!/usr/bin/env python3
from pathlib import Path

p = Path("src/scripts/research/serve_multi_asset_breakout_dashboard_v1.py")
s = p.read_text()

helper = r'''
def fetch_gold_filtered_edge_scorecard_v1():
    try:
        import os
        import psycopg
        from psycopg.rows import dict_row

        dsn = os.environ.get("DATABASE_URL")
        if not dsn:
            return {"status": "DATABASE_URL_NOT_SET", "rows": []}

        sql = """
        with base as (
            select
                symbol,
                family,
                status,
                return_pct,
                source_ts,
                extract(hour from source_ts at time zone 'Europe/Moscow')::int as hour_msk
            from analytics_futures_rs_bottom_paper_observation_v1
            where symbol in ('GDU6@RTSX','GLU6@RTSX')
              and status in ('SUCCESS','FAILURE')
              and return_pct is not null
        ),
        agg as (
            select
                symbol,
                coalesce(max(family), 'GOLD') as family,
                count(*)::int as completed,
                count(*) filter (where return_pct > 0)::int as wins,
                count(*) filter (where return_pct <= 0)::int as losses,
                avg(return_pct) as expectancy,
                sum(return_pct) as net_return,
                case
                    when abs(sum(least(return_pct,0))) > 0
                    then sum(greatest(return_pct,0)) / abs(sum(least(return_pct,0)))
                    else null
                end as profit_factor,
                min(source_ts) as first_ts,
                max(source_ts) as last_ts
            from base
            where hour_msk < 19
            group by symbol
        )
        select *
        from agg
        order by profit_factor desc nulls last, completed desc
        """

        with psycopg.connect(dsn, row_factory=dict_row) as conn:
            with conn.cursor() as cur:
                cur.execute(sql)
                rows = [dict(r) for r in cur.fetchall()]

        for r in rows:
            completed = int(r.get("completed") or 0)
            pf = float(r.get("profit_factor") or 0)
            exp = float(r.get("expectancy") or 0)
            r["edge_mode"] = "FILTERED_BEFORE_19_MSK"
            r["verdict"] = "PRIMARY" if completed >= 15 and pf >= 1.5 and exp > 0 else "WATCH"

        return {"status": "OK", "rows": rows}
    except Exception as exc:
        return {"status": f"ERROR:{type(exc).__name__}:{exc}", "rows": []}


def render_gold_filtered_edge_scorecard_card_v1():
    data = fetch_gold_filtered_edge_scorecard_v1()
    rows = data.get("rows") or []

    if rows:
        body = "".join(
            "<tr>"
            f"<td>{_gold_esc_v1(r.get('symbol'))}</td>"
            f"<td>{_gold_esc_v1(r.get('family'))}</td>"
            f"<td>{_gold_esc_v1(r.get('completed'))}</td>"
            f"<td>{_gold_esc_v1(r.get('wins'))}</td>"
            f"<td>{_gold_esc_v1(r.get('losses'))}</td>"
            f"<td>{_gold_esc_v1(round(float(r.get('profit_factor') or 0), 4))}</td>"
            f"<td>{_gold_esc_v1(round(float(r.get('expectancy') or 0), 4))}</td>"
            f"<td>{_gold_esc_v1(round(float(r.get('net_return') or 0), 4))}</td>"
            f"<td>{_gold_esc_v1(r.get('verdict'))}</td>"
            f"<td>{_gold_esc_v1(r.get('last_ts'))}</td>"
            "</tr>"
            for r in rows
        )
    else:
        body = "<tr><td colspan='10'>Нет данных</td></tr>"

    return f"""
<div class="card">
  <h2>🟢 Filtered Gold Edge</h2>
  <div><b>Режим:</b> research-only scorecard</div>
  <div><b>Фильтр:</b> GDU6/GLU6, только сигналы до 19:00 МСК</div>
  <div><b>Статус источника:</b> {_gold_esc_v1(data.get('status'))}</div>
  <table>
    <tr>
      <th>Инструмент</th><th>Семейство</th><th>Завершено</th><th>Успех</th><th>Ошибка</th>
      <th>PF</th><th>Expectancy</th><th>Net Return</th><th>Вердикт</th><th>Последний сигнал</th>
    </tr>
    {body}
  </table>
</div>
"""
'''

if "def fetch_gold_filtered_edge_scorecard_v1()" not in s:
    anchor = "def render_rs_bottom_runtime_dry_run_dashboard_v1():"
    if anchor not in s:
        raise SystemExit("RS_BOTTOM_RUNTIME_RENDER_ANCHOR_NOT_FOUND")
    s = s.replace(anchor, helper + "\n\n" + anchor, 1)

start = s.find("def render_rs_bottom_runtime_dry_run_dashboard_v1():")
end = s.find("def render_finam_core_mobile_home_v1")
if end < 0:
    end = s.find("class Handler")
if start < 0 or end < 0:
    raise SystemExit("RS_BOTTOM_RUNTIME_BLOCK_NOT_FOUND")

block = s[start:end]

if "render_gold_filtered_edge_scorecard_card_v1()" not in block:
    anchor = "render_gold_session_guard_status_card_v1()"
    if anchor in block:
        block = block.replace(
            "{render_gold_session_guard_status_card_v1()}",
            "{render_gold_filtered_edge_scorecard_card_v1()}\n\n{render_gold_session_guard_status_card_v1()}",
            1,
        )
    else:
        block = block.replace("{error_html}", "{render_gold_filtered_edge_scorecard_card_v1()}\n\n{error_html}", 1)

    s = s[:start] + block + s[end:]
    p.write_text(s)
    print("PATCH_GOLD_FILTERED_EDGE_SCORECARD_8088_V1_OK")
else:
    print("GOLD_FILTERED_EDGE_SCORECARD_8088_ALREADY_PRESENT")
