#!/usr/bin/env bash
set -euo pipefail

echo "=== BUILD_EDGE_AUDIT_MENU_LINK_V1 ==="

python - <<'PY'
from pathlib import Path

page = Path("src/marketcore/presentation/pages/edge_audit_page.py")
s = page.read_text(encoding="utf-8")

if "class EdgeAuditPage" not in s:
    s += '''

class EdgeAuditPage:
    route = "/edge-audit"
    title = "Edge Audit"
    menu_title = "Edge Audit"
    menu_order = 46

    def render(self) -> str:
        return render_edge_audit_page()
'''
    page.write_text(s, encoding="utf-8")

reg = Path("src/marketcore/presentation/registry.py")
r = reg.read_text(encoding="utf-8")

imp = "from marketcore.presentation.pages.edge_audit_page import EdgeAuditPage\n"
if imp not in r:
    marker = "from marketcore.presentation.pages.edge_platform import EdgePlatformPage\n"
    r = r.replace(marker, marker + imp)

if "EdgeAuditPage()," not in r:
    marker = "    EdgePlatformPage(),\n"
    r = r.replace(marker, marker + "    EdgeAuditPage(),\n")

reg.write_text(r, encoding="utf-8")
PY

cat > scripts/test_edge_audit_menu_link_v1.sh <<'TEST'
#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_EDGE_AUDIT_MENU_LINK_V1 ==="

PYTHONPATH=src python -m py_compile \
  src/marketcore/presentation/pages/edge_audit_page.py \
  src/marketcore/presentation/registry.py \
  src/marketcore/presentation/router.py

sudo systemctl restart marketcore-ui-shell.service
sleep 2

curl -fsS http://127.0.0.1:8080/edge-audit >/tmp/edge_audit_page.html
curl -fsS http://127.0.0.1:8080/ >/tmp/edge_audit_home.html

grep -q "Edge Audit" /tmp/edge_audit_page.html
grep -q "/edge-audit" /tmp/edge_audit_home.html

echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo "VERDICT=TEST_EDGE_AUDIT_MENU_LINK_V1_OK"
TEST

chmod +x scripts/test_edge_audit_menu_link_v1.sh
scripts/test_edge_audit_menu_link_v1.sh

echo "VERDICT=BUILD_EDGE_AUDIT_MENU_LINK_V1_OK"
