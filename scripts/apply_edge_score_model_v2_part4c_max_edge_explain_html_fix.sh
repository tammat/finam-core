#!/usr/bin/env bash
set -euo pipefail

echo "=== APPLY_EDGE_SCORE_MODEL_V2_PART4C_MAX_EDGE_EXPLAIN_HTML_FIX ==="

target="src/marketcore/presentation/components/max_edge_card.py"
test -f "$target"

python - <<'PY'
from pathlib import Path

p = Path("src/marketcore/presentation/components/max_edge_card.py")
s = p.read_text(encoding="utf-8")

if "def render_edge_score_explain_card" not in s:
    helper = '''
def render_edge_score_explain_card(current: dict) -> str:
    groups = current.get("edge_score_explain_groups") or []
    if not groups:
        return ""

    rows = []
    for group in groups:
        rows.append(
            "<tr>"
            f"<td>{_v(group.get('group_code'))}</td>"
            f"<td>{_v(group.get('group_score'))}</td>"
            f"<td>{_v(group.get('group_weight'))}</td>"
            f"<td>{_v(group.get('group_contribution'))}</td>"
            "</tr>"
        )

    return f"""
        <div class="edge-score-explain-card" data-i18n-scope="edge.score.explain">
            <div class="edge-score-explain-title" data-i18n-key="edge.score.explain.title">edge.score.explain.title</div>
            <table class="edge-score-explain-table">
                <thead>
                    <tr>
                        <th data-i18n-key="edge.score.explain.group">edge.score.explain.group</th>
                        <th data-i18n-key="edge.score.explain.score">edge.score.explain.score</th>
                        <th data-i18n-key="edge.score.explain.weight">edge.score.explain.weight</th>
                        <th data-i18n-key="edge.score.explain.contribution">edge.score.explain.contribution</th>
                    </tr>
                </thead>
                <tbody>
                    {''.join(rows)}
                </tbody>
            </table>
        </div>
    """
'''

    marker = "\n\ndef render_max_edge_card(current: dict) -> str:"
    if marker not in s:
        raise SystemExit("RENDER_MAX_EDGE_CARD_MARKER_NOT_FOUND")
    s = s.replace(marker, "\n\n" + helper + marker, 1)

if "render_edge_score_explain_card(current)" not in s:
    old = """        </div>
    \""""
    new = """        </div>
        {render_edge_score_explain_card(current)}
    \""""
    if old not in s:
        raise SystemExit("MAX_EDGE_CARD_CLOSE_MARKER_NOT_FOUND")
    s = s.replace(old, new, 1)

p.write_text(s, encoding="utf-8")
print("patch_status=applied")
PY

PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python -m py_compile "$target"

echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo "VERDICT=EDGE_SCORE_MODEL_V2_PART4C_MAX_EDGE_EXPLAIN_HTML_FIX_READY"
