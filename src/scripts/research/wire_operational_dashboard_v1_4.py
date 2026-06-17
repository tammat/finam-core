#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
APP_FILE = ROOT / "src/ui/readonly_runtime_dashboard_v1.py"
TEMPLATE_FILE = ROOT / "src/ui/templates/v3_dashboard.html"

HELPER_MARKER = "OPERATIONAL_DASHBOARD_CONTEXT_V1_4"
TEMPLATE_MARKER = "OPERATIONAL_DASHBOARD_WIRING_V1"
KWARG_LINE = "        **_clean_operational_positions_context_v1(),"


HELPER_CODE = r'''
# === OPERATIONAL_DASHBOARD_CONTEXT_V1_4 BEGIN ===
def _load_clean_operational_positions_v1():
    """Русский комментарий:
    Read-only загрузка clean_operational_position_view_v1 для dashboard.
    Историю сделок не меняет, runtime/execution не открывает.
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


def _clean_operational_positions_context_v1():
    """Русский комментарий:
    Возвращает kwargs для v3_dashboard.html.
    Только UI-контекст, без влияния на торговый pipeline.
    """
    rows, error = _load_clean_operational_positions_v1()
    return {
        "operational_positions_v1": rows,
        "operational_positions_error_v1": error,
    }
# === OPERATIONAL_DASHBOARD_CONTEXT_V1_4 END ===
'''


def insert_helper(text: str) -> tuple[str, bool]:
    if HELPER_MARKER in text:
        return text, False

    marker = 'if __name__ == "__main__":'
    if marker in text:
        return text.replace(marker, HELPER_CODE + "\n\n" + marker, 1), True

    return text.rstrip() + "\n\n" + HELPER_CODE + "\n", True


def find_statement_bounds(lines: list[str], idx: int) -> tuple[int, int]:
    """Русский комментарий:
    Находит многострочный вызов/return, содержащий v3_dashboard.html.
    Используем баланс скобок, чтобы не зависеть от render_template.
    """
    start = idx
    while start > 0:
        prev = lines[start - 1]
        if prev.startswith("def ") or prev.startswith("@") or prev.strip().startswith("return "):
            break
        if prev.strip() == "":
            break
        start -= 1

    depth = 0
    started = False
    end = idx

    for j in range(start, len(lines)):
        line = lines[j]
        for ch in line:
            if ch in "([{":
                depth += 1
                started = True
            elif ch in ")]}":
                depth -= 1

        end = j
        if started and depth <= 0 and j >= idx:
            break

    return start, end


def patch_v3_dashboard_call(text: str) -> tuple[str, int]:
    lines = text.splitlines()
    patched = 0

    target_indexes = [
        i for i, line in enumerate(lines)
        if "v3_dashboard.html" in line
    ]

    for idx in reversed(target_indexes):
        start, end = find_statement_bounds(lines, idx)
        block = "\n".join(lines[start:end + 1])

        if "_clean_operational_positions_context_v1()" in block:
            continue

        # Вариант 1: обычный kwargs-вызов:
        #   something("v3_dashboard.html", a=..., b=...)
        # Добавляем **kwargs перед закрывающей скобкой.
        close_line_idx = end
        indent = lines[close_line_idx][: len(lines[close_line_idx]) - len(lines[close_line_idx].lstrip())]

        insert_line = indent + "    **_clean_operational_positions_context_v1(),"

        lines.insert(close_line_idx, insert_line)
        patched += 1

    return "\n".join(lines) + "\n", patched


def main() -> int:
    print("=== OPERATIONAL DASHBOARD WIRING V1_4 ===")
    print("mode=patch_v3_dashboard_renderer")
    print("runtime_allow=0")
    print("execution_enabled=0")

    if not APP_FILE.exists():
        raise SystemExit(f"FAIL: app file not found: {APP_FILE}")
    if not TEMPLATE_FILE.exists():
        raise SystemExit(f"FAIL: template file not found: {TEMPLATE_FILE}")

    template_text = TEMPLATE_FILE.read_text()
    if TEMPLATE_MARKER not in template_text:
        raise SystemExit("FAIL: template operational block marker missing")

    text = APP_FILE.read_text()
    if "v3_dashboard.html" not in text:
        raise SystemExit("FAIL: app file does not reference v3_dashboard.html")

    text, helper_inserted = insert_helper(text)
    text, patched_calls = patch_v3_dashboard_call(text)

    APP_FILE.write_text(text)

    print(f"FOUND_REAL_APP_FILE={APP_FILE}")
    print(f"FOUND_TEMPLATE={TEMPLATE_FILE}")
    print(f"HELPER_INSERTED={int(helper_inserted)}")
    print(f"V3_RENDER_CALLS_PATCHED={patched_calls}")

    if patched_calls < 1 and "_clean_operational_positions_context_v1()" not in text:
        raise SystemExit("FAIL: no v3 dashboard render call patched")

    print("OPERATIONAL_DASHBOARD_WIRING_V1_4_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
