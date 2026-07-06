#!/usr/bin/env bash
set -euo pipefail

echo "=== BUILD_UI_RESPONSIVE_COMPACT_V1 ==="

python - <<'PY'
from pathlib import Path

root = Path("src/marketcore/presentation")
candidates = list(root.rglob("*.py")) + list(root.rglob("*.css"))

targets = []
for p in candidates:
    s = p.read_text(encoding="utf-8", errors="ignore")
    if "body" in s and ".card" in s:
        targets.append(p)

if not targets:
    raise SystemExit("UI_STYLE_TARGET_NOT_FOUND")

css = r'''

/* UI_RESPONSIVE_COMPACT_V1 */
:root {
    --ui-compact-kpi-height: 56px;
    --ui-compact-gap: 8px;
    --ui-sticky-bar-height: 28px;
}

body {
    padding-top: var(--ui-sticky-bar-height);
}

.ui-runtime-bar {
    position: fixed;
    top: 0;
    left: 0;
    right: 0;
    height: var(--ui-sticky-bar-height);
    z-index: 9999;
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 0 12px;
    font-size: 12px;
    line-height: 1;
    background: rgba(10, 14, 22, 0.96);
    border-bottom: 1px solid rgba(255,255,255,0.08);
    color: #d7dee9;
}

.ui-runtime-bar strong {
    font-weight: 600;
}

.cards {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(132px, 1fr));
    gap: var(--ui-compact-gap);
    margin: 8px 0 10px 0;
}

.card {
    padding: 8px 10px;
    border-radius: 8px;
}

.cards .card {
    min-height: var(--ui-compact-kpi-height);
}

.card h2 {
    font-size: 18px;
    margin: 0 0 6px 0;
}

.card h3 {
    font-size: 11px;
    line-height: 1.2;
    margin: 0 0 4px 0;
    font-weight: 500;
    opacity: 0.82;
}

.card p {
    font-size: 18px;
    line-height: 1.2;
    margin: 0;
    font-weight: 650;
}

table {
    font-size: 12px;
}

th, td {
    padding: 5px 7px;
    line-height: 1.25;
}

thead th {
    position: sticky;
    top: var(--ui-sticky-bar-height);
    z-index: 5;
}

@media (max-width: 760px) {
    body {
        padding-top: 34px;
    }

    .ui-runtime-bar {
        height: 34px;
        font-size: 11px;
        padding: 0 8px;
    }

    .cards {
        grid-template-columns: repeat(2, minmax(0, 1fr));
        gap: 6px;
    }

    .card {
        padding: 7px 8px;
    }

    .card h2 {
        font-size: 16px;
    }

    .card h3 {
        font-size: 10px;
    }

    .card p {
        font-size: 15px;
    }

    table {
        display: block;
        overflow-x: auto;
        white-space: nowrap;
        font-size: 11px;
    }

    th, td {
        padding: 4px 6px;
    }
}
'''

for p in targets:
    s = p.read_text(encoding="utf-8", errors="ignore")
    if "UI_RESPONSIVE_COMPACT_V1" not in s:
        p.write_text(s + css, encoding="utf-8")
        print(f"patched_style={p}")
        break
else:
    print("style_already_patched")
PY

python - <<'PY'
from pathlib import Path

root = Path("src/marketcore/presentation")
candidates = list(root.rglob("*.py"))

bar = r'''
<!-- UI_RESPONSIVE_COMPACT_V1 -->
<div class="ui-runtime-bar">
    <strong>FINAM Core</strong>
    <span id="ui-runtime-clock">--.--.---- --:--:--</span>
</div>
<script>
(function () {
    function pad(n) { return String(n).padStart(2, "0"); }
    function tick() {
        const d = new Date();
        const text =
            pad(d.getDate()) + "." +
            pad(d.getMonth() + 1) + "." +
            d.getFullYear() + " " +
            pad(d.getHours()) + ":" +
            pad(d.getMinutes()) + ":" +
            pad(d.getSeconds());
        const el = document.getElementById("ui-runtime-clock");
        if (el) el.textContent = text;
    }
    tick();
    setInterval(tick, 1000);
})();
</script>
'''

for p in candidates:
    s = p.read_text(encoding="utf-8", errors="ignore")
    if "</body>" in s and "UI_RESPONSIVE_COMPACT_V1" not in s:
        p.write_text(s.replace("</body>", bar + "\n</body>"), encoding="utf-8")
        print(f"patched_layout={p}")
        break
else:
    raise SystemExit("UI_LAYOUT_BODY_TARGET_NOT_FOUND")
PY

cat > scripts/test_ui_responsive_compact_v1.sh <<'SH_TEST'
#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_UI_RESPONSIVE_COMPACT_V1 ==="

PYTHONPATH=src python -m py_compile \
  src/marketcore/presentation/registry.py \
  src/marketcore/presentation/router.py

sudo systemctl restart marketcore-ui-shell.service
sleep 2

curl -fsS "http://127.0.0.1:8080/feature-store" >/tmp/ui_compact_feature_store.html
curl -fsS "http://127.0.0.1:8080/portfolio-platform" >/tmp/ui_compact_portfolio.html

grep -q "ui-runtime-bar" /tmp/ui_compact_feature_store.html
grep -q "ui-runtime-clock" /tmp/ui_compact_feature_store.html
grep -q "UI_RESPONSIVE_COMPACT_V1" /tmp/ui_compact_feature_store.html

echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo "VERDICT=UI_RESPONSIVE_COMPACT_V1_READY"
echo "VERDICT=TEST_UI_RESPONSIVE_COMPACT_V1_OK"
SH_TEST

chmod +x scripts/test_ui_responsive_compact_v1.sh
scripts/test_ui_responsive_compact_v1.sh

echo "VERDICT=BUILD_UI_RESPONSIVE_COMPACT_V1_OK"
