#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]

BLOCK_MARKER = "OPERATIONAL_DASHBOARD_WIRING_V1"

APP_INJECT = r'''
# === OPERATIONAL_DASHBOARD_WIRING_V1 BEGIN ===
def _load_clean_operational_positions_v1():
    """Русский комментарий:
    Читает готовое PostgreSQL view clean_operational_position_view_v1
    только для отображения в dashboard. Историю trades не меняет.
    """
    import os
    import psycopg2
    import psycopg2.extras

    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        return [], "DATABASE_URL не задан"

    sql = """
        select
            symbol,
            strategy,
            timeframe,
            trade_source,
            fills,
            buy_fills,
            sell_fills,
            round(net_qty::numeric, 6) as net_qty,
            full_chains,
            round(v3_pnl::numeric, 6) as pnl,
            operational_status,
            is_current_operational_position,
            include_in_clean_operational_view,
            last_buy_ts,
            last_sell_ts,
            last_chain_exit_ts
        from clean_operational_position_view_v1
        order by
            case operational_status
                when 'OPEN_PAPER_LONG_TAIL' then 0
                when 'CLEAN_V3_OPEN_REVIEW' then 1
                when 'CLEAN_V3_FLAT' then 2
                when 'QUARANTINE_CONTAMINATED_TAIL' then 3
                when 'EXCLUDE_HISTORICAL_TAIL' then 4
                else 5
            end,
            symbol,
            strategy,
            timeframe;
    """

    status_ru = {
        "OPEN_PAPER_LONG_TAIL": "Текущая paper-позиция",
        "CLEAN_V3_FLAT": "Clean V3, позиции нет",
        "CLEAN_V3_OPEN_REVIEW": "Clean V3, открыт остаток",
        "EXCLUDE_HISTORICAL_TAIL": "Исключено: исторический хвост",
        "QUARANTINE_CONTAMINATED_TAIL": "Карантин: загрязнённый хвост",
    }

    rows = []
    try:
        with psycopg2.connect(database_url) as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute(sql)
                for row in cur.fetchall():
                    item = dict(row)
                    item["operational_status_ru"] = status_ru.get(
                        item.get("operational_status"),
                        item.get("operational_status"),
                    )
                    rows.append(item)
        return rows, None
    except Exception as exc:
        return [], str(exc)


@app.context_processor
def _inject_clean_operational_positions_v1():
    """Русский комментарий:
    Добавляет operational view в Jinja-контекст.
    Работает только как read-only dashboard context.
    """
    rows, error = _load_clean_operational_positions_v1()
    return {
        "operational_positions_v1": rows,
        "operational_positions_error_v1": error,
    }
# === OPERATIONAL_DASHBOARD_WIRING_V1 END ===
'''


TEMPLATE_BLOCK = r'''
<!-- OPERATIONAL_DASHBOARD_WIRING_V1 BEGIN -->
<section id="clean-operational-position-view-v1" style="margin-top: 24px;">
  <h2>Операционное состояние paper-позиций</h2>
  <p style="margin-bottom: 12px;">
    Источник: <code>clean_operational_position_view_v1</code>.
    Runtime и real execution не открываются.
  </p>

  {% if operational_positions_error_v1 %}
    <div style="padding: 10px; border: 1px solid #b91c1c; border-radius: 6px;">
      Ошибка чтения operational view: {{ operational_positions_error_v1 }}
    </div>
  {% elif operational_positions_v1 %}
    <table style="width: 100%; border-collapse: collapse; font-size: 13px;">
      <thead>
        <tr>
          <th style="text-align:left; border-bottom: 1px solid #ccc; padding: 6px;">Инструмент</th>
          <th style="text-align:left; border-bottom: 1px solid #ccc; padding: 6px;">Стратегия</th>
          <th style="text-align:left; border-bottom: 1px solid #ccc; padding: 6px;">TF</th>
          <th style="text-align:right; border-bottom: 1px solid #ccc; padding: 6px;">Net qty</th>
          <th style="text-align:right; border-bottom: 1px solid #ccc; padding: 6px;">Цепочки</th>
          <th style="text-align:right; border-bottom: 1px solid #ccc; padding: 6px;">PnL</th>
          <th style="text-align:left; border-bottom: 1px solid #ccc; padding: 6px;">Статус</th>
          <th style="text-align:center; border-bottom: 1px solid #ccc; padding: 6px;">Текущая позиция</th>
          <th style="text-align:center; border-bottom: 1px solid #ccc; padding: 6px;">В clean view</th>
        </tr>
      </thead>
      <tbody>
        {% for row in operational_positions_v1 %}
          <tr>
            <td style="padding: 6px; border-bottom: 1px solid #eee;">{{ row.symbol }}</td>
            <td style="padding: 6px; border-bottom: 1px solid #eee;">{{ row.strategy }}</td>
            <td style="padding: 6px; border-bottom: 1px solid #eee;">{{ row.timeframe }}</td>
            <td style="padding: 6px; border-bottom: 1px solid #eee; text-align:right;">{{ row.net_qty }}</td>
            <td style="padding: 6px; border-bottom: 1px solid #eee; text-align:right;">{{ row.full_chains }}</td>
            <td style="padding: 6px; border-bottom: 1px solid #eee; text-align:right;">{{ row.pnl }}</td>
            <td style="padding: 6px; border-bottom: 1px solid #eee;">{{ row.operational_status_ru }}</td>
            <td style="padding: 6px; border-bottom: 1px solid #eee; text-align:center;">
              {% if row.is_current_operational_position %}да{% else %}нет{% endif %}
            </td>
            <td style="padding: 6px; border-bottom: 1px solid #eee; text-align:center;">
              {% if row.include_in_clean_operational_view %}да{% else %}нет{% endif %}
            </td>
          </tr>
        {% endfor %}
      </tbody>
    </table>
  {% else %}
    <p>Нет данных operational view.</p>
  {% endif %}
</section>
<!-- OPERATIONAL_DASHBOARD_WIRING_V1 END -->
'''


def find_template() -> Path:
    candidates = list(ROOT.rglob("v3_dashboard.html"))
    if not candidates:
        raise SystemExit("FAIL: v3_dashboard.html not found")
    return candidates[0]


def find_app_file() -> Path:
    candidates = []
    for path in ROOT.rglob("*.py"):
        if ".venv" in path.parts or "venv" in path.parts or ".git" in path.parts:
            continue
        text = path.read_text(errors="ignore")
        if "v3_dashboard.html" in text and "render_template" in text and "Flask" in text:
            candidates.append(path)

    if not candidates:
        for path in ROOT.rglob("*.py"):
            if ".venv" in path.parts or "venv" in path.parts or ".git" in path.parts:
                continue
            text = path.read_text(errors="ignore")
            if "v3_dashboard.html" in text and "render_template" in text:
                candidates.append(path)

    if not candidates:
        raise SystemExit("FAIL: dashboard app file rendering v3_dashboard.html not found")

    return candidates[0]


def patch_app(path: Path) -> None:
    text = path.read_text()

    if BLOCK_MARKER in text:
        print(f"APP_ALREADY_PATCHED path={path}")
        return

    if "app = Flask" not in text and "app=Flask" not in text:
        raise SystemExit(f"FAIL: Flask app variable not found in {path}")

    path.write_text(text.rstrip() + "\n\n" + APP_INJECT + "\n")
    print(f"APP_PATCHED path={path}")


def patch_template(path: Path) -> None:
    text = path.read_text()

    if BLOCK_MARKER in text:
        print(f"TEMPLATE_ALREADY_PATCHED path={path}")
        return

    if "</body>" in text:
        text = text.replace("</body>", TEMPLATE_BLOCK + "\n</body>", 1)
    else:
        text = text.rstrip() + "\n\n" + TEMPLATE_BLOCK + "\n"

    path.write_text(text)
    print(f"TEMPLATE_PATCHED path={path}")


def main() -> int:
    print("=== OPERATIONAL DASHBOARD WIRING V1 ===")
    print("mode=patch_dashboard")
    print("runtime_allow=0")
    print("execution_enabled=0")

    template = find_template()
    app_file = find_app_file()

    print(f"FOUND_TEMPLATE={template}")
    print(f"FOUND_APP_FILE={app_file}")

    patch_app(app_file)
    patch_template(template)

    print("OPERATIONAL_DASHBOARD_WIRING_V1_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
