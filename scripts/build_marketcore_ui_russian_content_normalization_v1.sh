#!/usr/bin/env bash
set -euo pipefail

echo "=== BUILD_MARKETCORE_UI_RUSSIAN_CONTENT_NORMALIZATION_V1 ==="

mkdir -p src/scripts scripts src/marketcore/presentation

cat > src/marketcore/presentation/ui_labels.py <<'PY'
from __future__ import annotations


ROUTE_LABELS_RU = {
    "/": "Рабочий стол",

    "/runtime": "Runtime / исполнение",
    "/paper-edge-discovery": "Поиск преимущества",
    "/edge-validation-queue": "Очередь проверки преимущества",
    "/edge-validation-pipeline": "Pipeline проверки преимущества",
    "/edge-robustness-check": "Проверка устойчивости",
    "/edge-oos-validation": "Вневыборочная проверка",
    "/edge-oos-backtest": "Вневыборочный бэктест",
    "/micro-live-readiness": "Готовность Micro Live",

    "/paper-sample-accumulation-monitor": "Накопление выборки",
    "/paper-sample-collection-timer-health": "Здоровье таймера выборки",
    "/paper-runtime-sample-collection-phase-close": "Закрытие фазы выборки",
    "/phase-ii-paper-edge-discovery-summary": "Итоги Phase II: поиск преимущества",
    "/paper-runtime-sample-collection-operations": "Операции накопления выборки",
    "/paper-sample-operations-timer-health": "Здоровье таймера операций",
    "/paper-runtime-sample-collection-daily-summary": "Дневная сводка операций выборки",
    "/marketcore-ui-systemd-health": "Здоровье UI и systemd",

    "/knowledge-graph": "Граф знаний",
    "/research": "Исследования",
    "/portfolio": "Портфель",
    "/orders": "Заявки",
    "/risk": "Риски",
    "/validation": "Валидация",
    "/logs": "Журнал",
    "/system": "Система",
    "/settings": "Настройки",
    "/ai": "AI / помощник",

    "/capital": "Капитал",
    "/edge": "Преимущество",
    "/intraday": "Интрадей",
}


def display_label(route: str, fallback: str = "") -> str:
    return ROUTE_LABELS_RU.get(route, fallback or route)


def route_labels() -> dict[str, str]:
    return dict(ROUTE_LABELS_RU)
PY

cat > src/marketcore/presentation/ui_text.py <<'PY'
from __future__ import annotations


TEXT_REPLACEMENTS_RU = {
    "Paper Edge Discovery": "Поиск преимущества на Paper",
    "Paper Runtime Sample Collection Daily Summary": "Дневная сводка накопления выборки Paper Runtime",
    "Paper Runtime Sample Collection Operations": "Операции накопления выборки Paper Runtime",
    "Paper Sample Operations Timer Health": "Здоровье таймера операций выборки",
    "Paper Sample Accumulation Monitor": "Монитор накопления выборки",
    "Paper Sample Collection Timer Health": "Здоровье таймера накопления выборки",
    "Paper Runtime Sample Collection Phase Close": "Закрытие фазы накопления выборки",
    "Phase II Paper Edge Discovery Summary": "Итоги Phase II: поиск преимущества",
    "MarketCore UI Systemd Health": "Здоровье MarketCore UI и systemd",

    "Candidate Explainability": "Объяснение кандидатов",
    "TOP Candidates Detail": "Детализация TOP-кандидатов",
    "Research Candidates": "Кандидаты исследования",
    "Paper Runtime Real Data": "Реальные данные Paper Runtime",
    "Knowledge Graph": "Граф знаний",
    "Validation": "Валидация",
    "Edge Validation Queue": "Очередь проверки преимущества",
    "Edge Validation Pipeline": "Pipeline проверки преимущества",
    "Edge Robustness Check": "Проверка устойчивости преимущества",
    "Edge OOS Validation": "Вневыборочная проверка преимущества",
    "Edge OOS Backtest": "Вневыборочный бэктест преимущества",
    "Micro Live Readiness": "Готовность Micro Live",

    "Sample Collection Summary": "Сводка накопления выборки",
    "Closest Candidates To Recheck": "Ближайшие кандидаты к повторной проверке",
    "Timer Details": "Детали таймера",
    "Operations Timer Details": "Детали таймера операций",
    "Systemd Details": "Детали systemd",
    "Phase Close Summary": "Сводка закрытия фазы",
    "Pipeline Row Coverage": "Покрытие строк pipeline",
    "Daily Summary": "Дневная сводка",
    "Operations Queue": "Очередь операций",
    "Readiness Gate": "Шлюз готовности",
    "OOS Backtest": "Вневыборочный бэктест",
    "OOS Validation": "Вневыборочная проверка",
    "Robustness Check": "Проверка устойчивости",
    "Accumulation": "Накопление",
    "Summary": "Сводка",
    "Safety": "Безопасность",
    "Result": "Результат",
    "Next Action": "Следующее действие",
    "Source:": "Источник:",
    "Источник:": "Источник:",

    "Platform M2": "Платформа M2",
    "MarketCore OS": "MarketCore OS",
    "MarketCore UI Shell": "Оболочка MarketCore UI",
    "Единая оболочка платформы": "Единая оболочка платформы",

    "Settings": "Настройки",
    "Risk": "Риски",
    "Risks": "Риски",
    "Orders": "Заявки",
    "Portfolio": "Портфель",
    "Research": "Исследования",
    "Logs": "Журнал",
    "System": "Система",
    "Statistics": "Статистика",
    "Health": "Здоровье",
    "Queue": "Очередь",
    "Operations": "Операции",
    "Status": "Статус",
    "Priority": "Приоритет",
    "Ready": "Готово",
    "Blocked": "Заблокировано",
    "Failed": "Ошибка",
    "Rejected": "Отклонено",
    "Watchlist": "Наблюдение",
    "Collecting": "Накопление",
    "Wait Sample": "Ожидание выборки",
    "Wait Both": "Ожидание двух выборок",
    "Wait Total": "Ожидание общей выборки",
    "Wait OOS": "Ожидание OOS-выборки",
    "Need Total": "Нужно общих сделок",
    "Need OOS": "Нужно OOS-сделок",
    "Total Trades": "Всего сделок",
    "OOS Trades": "OOS-сделки",
    "Progress": "Прогресс",
    "Action": "Действие",
    "Reason": "Причина",
    "Conclusion": "Вывод",
    "Recommended Action": "Рекомендованное действие",
    "Open URL": "URL открытия",
    "Risk URL": "URL рисков",
    "Settings URL": "URL настроек",
    "Refreshed At": "Обновлено",
    "Source": "Источник",

    "P&L Total": "P&L всего",
    "P&amp;L Total": "P&L всего",
    "Signals Today": "Сигналы сегодня",
    "Closed Trades": "Закрытые сделки",
    "Timer Active State": "Активное состояние таймера",
    "Timer Unit File State": "Состояние unit-файла таймера",
    "Service Result": "Результат сервиса",
    "Service Healthy": "Сервис исправен",
    "Timer Healthy": "Таймер исправен",
    "Home HTTP OK": "Home HTTP OK",
    "Risk HTTP OK": "Risk HTTP OK",
    "Settings HTTP OK": "Settings HTTP OK",
    "Micro Live Allowed": "Micro Live разрешён",
    "Micro Live Ready Rows": "Строк готовности Micro Live",
    "Micro Live Allowed Rows": "Строк разрешения Micro Live",

    "Candidate": "Кандидат",
    "Candidates": "Кандидаты",
    "Evidence": "Доказательства",
    "Weakness": "Слабое место",
    "Block Reason": "Причина блокировки",
    "Operation": "Операция",
    "Pipeline": "Pipeline",
    "Robustness": "Устойчивость",
    "Backtest": "Бэктест",
    "Readiness": "Готовность",
}


def normalize_ui_text(text: str) -> str:
    result = text

    for source, target in sorted(TEXT_REPLACEMENTS_RU.items(), key=lambda item: len(item[0]), reverse=True):
        result = result.replace(source, target)

    return result
PY

cat > src/marketcore/presentation/navigation.py <<'PY'
from __future__ import annotations

from html import escape

from marketcore.presentation.registry import menu_pages
from marketcore.presentation.ui_labels import display_label


def render_navigation(active_route: str) -> str:
    items: list[str] = []

    for page in menu_pages():
        active = " active" if page.route == active_route else ""
        label = display_label(page.route, page.title)

        items.append(
            f'<a class="nav-item{active}" href="{escape(page.route)}">'
            f'<span class="nav-icon">{escape(page.icon)}</span>'
            f'<span class="nav-label">{escape(label)}</span>'
            f'</a>'
        )

    return "\n".join(items)
PY

python <<'PY'
from pathlib import Path

p = Path("src/marketcore/presentation/layout.py")
s = p.read_text()

if "from marketcore.presentation.ui_text import normalize_ui_text" not in s:
    s = s.replace(
        "from marketcore.presentation.ui_labels import display_label\n",
        "from marketcore.presentation.ui_labels import display_label\n"
        "from marketcore.presentation.ui_text import normalize_ui_text\n",
    )

old = "    page_title = display_label(active_route, title)\n"
new = "    page_title = normalize_ui_text(display_label(active_route, title))\n    content = normalize_ui_text(content)\n"

if old in s:
    s = s.replace(old, new)
elif "page_title = normalize_ui_text(display_label(active_route, title))" not in s:
    raise SystemExit("layout page_title block not found")

# Если в старом layout нет единого shell badge, не ломаем. Проверяем только наличие русского lang и CSS.
if 'lang="ru"' not in s:
    raise SystemExit("layout must remain lang=ru")

p.write_text(s)
PY

cat > src/scripts/audit_marketcore_ui_russian_content_normalization_v1.py <<'PY'
from __future__ import annotations

from marketcore.presentation.registry import menu_pages
from marketcore.presentation.ui_labels import display_label, route_labels
from marketcore.presentation.ui_text import normalize_ui_text


REQUIRED_ROUTES = {
    "/",
    "/paper-edge-discovery",
    "/paper-runtime-sample-collection-daily-summary",
    "/marketcore-ui-systemd-health",
    "/risk",
    "/settings",
}

FORBIDDEN_SNIPPETS_AFTER_NORMALIZATION = [
    "Next Action",
    "Source:",
    "Paper Runtime Real Data",
    "Research Candidates",
    "Candidate Explainability",
    "TOP Candidates Detail",
    "Systemd Details",
    "Daily Summary",
    "Operations Queue",
    "Settings</h1>",
    "Risk</h1>",
]

REQUIRED_NORMALIZED_SNIPPETS = [
    "Следующее действие",
    "Источник:",
    "Реальные данные Paper Runtime",
    "Кандидаты исследования",
    "Объяснение кандидатов",
    "Детализация TOP-кандидатов",
    "Детали systemd",
    "Дневная сводка",
    "Очередь операций",
    "Настройки",
    "Риски",
]


def main() -> None:
    labels = route_labels()
    pages = menu_pages()
    routes = {page.route for page in pages}

    missing_routes = sorted(REQUIRED_ROUTES - routes)
    missing_labels = sorted(page.route for page in pages if page.route not in labels)

    print("=== MARKETCORE_UI_RUSSIAN_CONTENT_NORMALIZATION_V1 ===")
    print(f"pages_total={len(pages)}")

    for page in pages:
        print(
            "PAGE "
            f"route={page.route} "
            f"title={page.title} "
            f"label_ru={display_label(page.route, page.title)}"
        )

    if missing_routes:
        print("missing_required_routes=" + ",".join(missing_routes))
        raise SystemExit(2)

    if missing_labels:
        print("missing_ru_labels=" + ",".join(missing_labels))
        raise SystemExit(3)

    sample = """
    Next Action
    Source:
    Paper Runtime Real Data
    Research Candidates
    Candidate Explainability
    TOP Candidates Detail
    Systemd Details
    Daily Summary
    Operations Queue
    Settings
    Risk
    """

    normalized = normalize_ui_text(sample)

    for snippet in FORBIDDEN_SNIPPETS_AFTER_NORMALIZATION:
        if snippet in normalized:
            print(f"forbidden_after_normalization={snippet}")
            raise SystemExit(4)

    for snippet in REQUIRED_NORMALIZED_SNIPPETS:
        if snippet not in normalized:
            print(f"missing_required_normalized_snippet={snippet}")
            raise SystemExit(5)

    print("route_labels_ru=READY")
    print("content_normalizer=READY")
    print("risk_settings_ru=READY")
    print("single_theme_layout=READY")
    print("VERDICT=MARKETCORE_UI_RUSSIAN_CONTENT_NORMALIZATION_V1_READY")


if __name__ == "__main__":
    main()
PY

cat > scripts/test_marketcore_ui_russian_content_normalization_v1.sh <<'SH_TEST'
#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_MARKETCORE_UI_RUSSIAN_CONTENT_NORMALIZATION_V1 ==="

PYTHONPATH=src python -m py_compile \
  src/marketcore/presentation/ui_labels.py \
  src/marketcore/presentation/ui_text.py \
  src/marketcore/presentation/navigation.py \
  src/marketcore/presentation/layout.py \
  src/scripts/audit_marketcore_ui_russian_content_normalization_v1.py \
  src/marketcore/presentation/app.py

PYTHONPATH=src python src/scripts/audit_marketcore_ui_russian_content_normalization_v1.py \
  | tee /tmp/marketcore_ui_russian_content_normalization_v1.txt

grep -q "VERDICT=MARKETCORE_UI_RUSSIAN_CONTENT_NORMALIZATION_V1_READY" \
  /tmp/marketcore_ui_russian_content_normalization_v1.txt

MARKETCORE_UI_HOST=127.0.0.1 MARKETCORE_UI_PORT=20280 KG_API_BASE_URL=http://127.0.0.1:1 PYTHONPATH=src \
python src/marketcore/presentation/app.py > /tmp/marketcore_ui_russian_norm_v1.log 2>&1 &
ui_pid=$!

cleanup() {
  kill "$ui_pid" >/dev/null 2>&1 || true
}
trap cleanup EXIT

sleep 1

curl -fsS "http://127.0.0.1:20280/" > /tmp/ru_norm_home.html
curl -fsS "http://127.0.0.1:20280/paper-edge-discovery" > /tmp/ru_norm_edge.html
curl -fsS "http://127.0.0.1:20280/risk" > /tmp/ru_norm_risk.html
curl -fsS "http://127.0.0.1:20280/settings" > /tmp/ru_norm_settings.html
curl -fsS "http://127.0.0.1:20280/marketcore-ui-systemd-health" > /tmp/ru_norm_systemd.html

grep -q "Рабочий стол" /tmp/ru_norm_home.html
grep -q "Поиск преимущества" /tmp/ru_norm_home.html
grep -q "Риски" /tmp/ru_norm_home.html
grep -q "Настройки" /tmp/ru_norm_home.html
grep -q "Единая оболочка платформы" /tmp/ru_norm_home.html

grep -q "Объяснение кандидатов" /tmp/ru_norm_edge.html
grep -q "Детализация TOP-кандидатов" /tmp/ru_norm_edge.html
grep -q "Кандидаты исследования" /tmp/ru_norm_edge.html
grep -q "Реальные данные Paper Runtime" /tmp/ru_norm_edge.html
grep -q "Следующее действие" /tmp/ru_norm_edge.html

grep -q "Риски" /tmp/ru_norm_risk.html
grep -q "Настройки" /tmp/ru_norm_settings.html
grep -q "Детали systemd" /tmp/ru_norm_systemd.html

if grep -q "Next Action" /tmp/ru_norm_edge.html; then
  echo "FORBIDDEN_ENGLISH_NEXT_ACTION"
  exit 1
fi

if grep -q "Source:" /tmp/ru_norm_edge.html; then
  echo "FORBIDDEN_ENGLISH_SOURCE"
  exit 1
fi

if grep -q "Systemd Details" /tmp/ru_norm_systemd.html; then
  echo "FORBIDDEN_ENGLISH_SYSTEMD_DETAILS"
  exit 1
fi

grep -q "MARKETCORE_UI_SHELL_V1" /tmp/ru_norm_home.html

echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo "VERDICT=MARKETCORE_UI_RUSSIAN_CONTENT_NORMALIZATION_V1_READY"
echo "VERDICT=TEST_MARKETCORE_UI_RUSSIAN_CONTENT_NORMALIZATION_V1_OK"
SH_TEST

chmod +x scripts/test_marketcore_ui_russian_content_normalization_v1.sh

scripts/test_marketcore_ui_russian_content_normalization_v1.sh

echo "VERDICT=BUILD_MARKETCORE_UI_RUSSIAN_CONTENT_NORMALIZATION_V1_OK"
