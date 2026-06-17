#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
TEMPLATE = ROOT / "src/ui/templates/v3_dashboard.html"

START = "<!-- OPERATIONAL_DASHBOARD_WIRING_V1 BEGIN -->"
END = "<!-- OPERATIONAL_DASHBOARD_WIRING_V1 END -->"

NEW_BLOCK = r'''<!-- OPERATIONAL_DASHBOARD_WIRING_V1 BEGIN -->
<section id="clean-operational-position-view-v1" style="margin-top: 24px;">
  <h2>Операционное состояние paper-позиций</h2>
  <p style="margin-bottom: 12px;">
    Источник: <code>clean_operational_position_view_v1</code>.
    Это read-only слой: история сделок не меняется, runtime и real execution не открываются.
  </p>

  {% if operational_positions_error_v1 %}
    <div style="padding: 10px; border: 1px solid #b91c1c; border-radius: 6px;">
      Ошибка чтения operational view: {{ operational_positions_error_v1 }}
    </div>
  {% elif operational_positions_v1 %}

    <h3>Текущая paper-позиция</h3>
    <table style="width: 100%; border-collapse: collapse; font-size: 13px; margin-bottom: 18px;">
      <thead>
        <tr>
          <th style="text-align:left; border-bottom: 1px solid #ccc; padding: 6px;">Инструмент</th>
          <th style="text-align:left; border-bottom: 1px solid #ccc; padding: 6px;">Стратегия</th>
          <th style="text-align:left; border-bottom: 1px solid #ccc; padding: 6px;">TF</th>
          <th style="text-align:right; border-bottom: 1px solid #ccc; padding: 6px;">Net qty</th>
          <th style="text-align:right; border-bottom: 1px solid #ccc; padding: 6px;">Цепочки</th>
          <th style="text-align:right; border-bottom: 1px solid #ccc; padding: 6px;">PnL</th>
          <th style="text-align:left; border-bottom: 1px solid #ccc; padding: 6px;">Пояснение</th>
        </tr>
      </thead>
      <tbody>
        {% for row in operational_positions_v1 %}
          {% if row.operational_status == 'OPEN_PAPER_LONG_TAIL' %}
            <tr>
              <td style="padding: 6px; border-bottom: 1px solid #eee;">{{ row.symbol }}</td>
              <td style="padding: 6px; border-bottom: 1px solid #eee;">{{ row.strategy }}</td>
              <td style="padding: 6px; border-bottom: 1px solid #eee;">{{ row.timeframe }}</td>
              <td style="padding: 6px; border-bottom: 1px solid #eee; text-align:right;">{{ row.net_qty }}</td>
              <td style="padding: 6px; border-bottom: 1px solid #eee; text-align:right;">{{ row.full_chains }}</td>
              <td style="padding: 6px; border-bottom: 1px solid #eee; text-align:right;">{{ row.pnl }}</td>
              <td style="padding: 6px; border-bottom: 1px solid #eee;">Оставлено как текущий paper-long tail</td>
            </tr>
          {% endif %}
        {% endfor %}
      </tbody>
    </table>

    <h3>Clean V3 без открытой позиции</h3>
    <table style="width: 100%; border-collapse: collapse; font-size: 13px; margin-bottom: 18px;">
      <thead>
        <tr>
          <th style="text-align:left; border-bottom: 1px solid #ccc; padding: 6px;">Инструмент</th>
          <th style="text-align:left; border-bottom: 1px solid #ccc; padding: 6px;">Стратегия</th>
          <th style="text-align:left; border-bottom: 1px solid #ccc; padding: 6px;">TF</th>
          <th style="text-align:right; border-bottom: 1px solid #ccc; padding: 6px;">Net qty</th>
          <th style="text-align:right; border-bottom: 1px solid #ccc; padding: 6px;">Цепочки</th>
          <th style="text-align:right; border-bottom: 1px solid #ccc; padding: 6px;">PnL</th>
          <th style="text-align:left; border-bottom: 1px solid #ccc; padding: 6px;">Статус</th>
        </tr>
      </thead>
      <tbody>
        {% for row in operational_positions_v1 %}
          {% if row.operational_status == 'CLEAN_V3_FLAT' %}
            <tr>
              <td style="padding: 6px; border-bottom: 1px solid #eee;">{{ row.symbol }}</td>
              <td style="padding: 6px; border-bottom: 1px solid #eee;">{{ row.strategy }}</td>
              <td style="padding: 6px; border-bottom: 1px solid #eee;">{{ row.timeframe }}</td>
              <td style="padding: 6px; border-bottom: 1px solid #eee; text-align:right;">{{ row.net_qty }}</td>
              <td style="padding: 6px; border-bottom: 1px solid #eee; text-align:right;">{{ row.full_chains }}</td>
              <td style="padding: 6px; border-bottom: 1px solid #eee; text-align:right;">{{ row.pnl }}</td>
              <td style="padding: 6px; border-bottom: 1px solid #eee;">Позиции нет, включено в clean operational view</td>
            </tr>
          {% endif %}
        {% endfor %}
      </tbody>
    </table>

    <h3>Карантин</h3>
    <table style="width: 100%; border-collapse: collapse; font-size: 13px; margin-bottom: 18px;">
      <thead>
        <tr>
          <th style="text-align:left; border-bottom: 1px solid #ccc; padding: 6px;">Инструмент</th>
          <th style="text-align:left; border-bottom: 1px solid #ccc; padding: 6px;">Стратегия</th>
          <th style="text-align:left; border-bottom: 1px solid #ccc; padding: 6px;">TF</th>
          <th style="text-align:right; border-bottom: 1px solid #ccc; padding: 6px;">Net qty</th>
          <th style="text-align:right; border-bottom: 1px solid #ccc; padding: 6px;">Цепочки</th>
          <th style="text-align:right; border-bottom: 1px solid #ccc; padding: 6px;">PnL</th>
          <th style="text-align:left; border-bottom: 1px solid #ccc; padding: 6px;">Причина</th>
        </tr>
      </thead>
      <tbody>
        {% for row in operational_positions_v1 %}
          {% if row.operational_status == 'QUARANTINE_CONTAMINATED_TAIL' %}
            <tr>
              <td style="padding: 6px; border-bottom: 1px solid #eee;">{{ row.symbol }}</td>
              <td style="padding: 6px; border-bottom: 1px solid #eee;">{{ row.strategy }}</td>
              <td style="padding: 6px; border-bottom: 1px solid #eee;">{{ row.timeframe }}</td>
              <td style="padding: 6px; border-bottom: 1px solid #eee; text-align:right;">{{ row.net_qty }}</td>
              <td style="padding: 6px; border-bottom: 1px solid #eee; text-align:right;">{{ row.full_chains }}</td>
              <td style="padding: 6px; border-bottom: 1px solid #eee; text-align:right;">{{ row.pnl }}</td>
              <td style="padding: 6px; border-bottom: 1px solid #eee;">Загрязнённый хвост: price jump / duration guard</td>
            </tr>
          {% endif %}
        {% endfor %}
      </tbody>
    </table>

    <h3>Исключено из operational state</h3>
    <table style="width: 100%; border-collapse: collapse; font-size: 13px; margin-bottom: 18px;">
      <thead>
        <tr>
          <th style="text-align:left; border-bottom: 1px solid #ccc; padding: 6px;">Инструмент</th>
          <th style="text-align:left; border-bottom: 1px solid #ccc; padding: 6px;">Стратегия</th>
          <th style="text-align:left; border-bottom: 1px solid #ccc; padding: 6px;">TF</th>
          <th style="text-align:right; border-bottom: 1px solid #ccc; padding: 6px;">Net qty</th>
          <th style="text-align:right; border-bottom: 1px solid #ccc; padding: 6px;">Цепочки</th>
          <th style="text-align:right; border-bottom: 1px solid #ccc; padding: 6px;">PnL</th>
          <th style="text-align:left; border-bottom: 1px solid #ccc; padding: 6px;">Причина</th>
        </tr>
      </thead>
      <tbody>
        {% for row in operational_positions_v1 %}
          {% if row.operational_status == 'EXCLUDE_HISTORICAL_TAIL' %}
            <tr>
              <td style="padding: 6px; border-bottom: 1px solid #eee;">{{ row.symbol }}</td>
              <td style="padding: 6px; border-bottom: 1px solid #eee;">{{ row.strategy }}</td>
              <td style="padding: 6px; border-bottom: 1px solid #eee;">{{ row.timeframe }}</td>
              <td style="padding: 6px; border-bottom: 1px solid #eee; text-align:right;">{{ row.net_qty }}</td>
              <td style="padding: 6px; border-bottom: 1px solid #eee; text-align:right;">{{ row.full_chains }}</td>
              <td style="padding: 6px; border-bottom: 1px solid #eee; text-align:right;">{{ row.pnl }}</td>
              <td style="padding: 6px; border-bottom: 1px solid #eee;">Исторический partial tail, не текущая paper-позиция</td>
            </tr>
          {% endif %}
        {% endfor %}
      </tbody>
    </table>

  {% else %}
    <p>Нет данных operational view.</p>
  {% endif %}
</section>
<!-- OPERATIONAL_DASHBOARD_WIRING_V1 END -->'''


def main() -> int:
    print("=== OPERATIONAL DASHBOARD RU STATUS POLISH V1 ===")
    print("mode=patch_template")
    print("runtime_allow=0")
    print("execution_enabled=0")

    if not TEMPLATE.exists():
        raise SystemExit(f"FAIL: template not found: {TEMPLATE}")

    text = TEMPLATE.read_text()

    start = text.find(START)
    end = text.find(END)

    if start == -1 or end == -1:
        raise SystemExit("FAIL: operational dashboard block markers not found")

    end = end + len(END)

    text = text[:start] + NEW_BLOCK + text[end:]
    TEMPLATE.write_text(text)

    print(f"TEMPLATE_PATCHED={TEMPLATE}")
    print("OPERATIONAL_DASHBOARD_RU_STATUS_POLISH_V1_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
