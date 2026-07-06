#!/usr/bin/env bash
set -euo pipefail

echo "=== GIT_CLEANUP_DOCS_REMAINING_V1 ==="

# Runtime snapshot не коммитим
if ! grep -q '^data/snapshot\.json$' .gitignore; then
  cat >> .gitignore <<'EOF'

# Runtime snapshots
data/snapshot.json
EOF
fi

git restore data/snapshot.json 2>/dev/null || true
git restore ARCHITECTURE.md 2>/dev/null || true
rm -f "DECISIONS.md."

PYTHONPATH=src python -m py_compile src/scripts/check_no_hardcode_v1.py
PYTHONPATH=src python src/scripts/check_no_hardcode_v1.py

git add \
  .gitignore \
  PROJECT_STATUS.md \
  ROADMAP.md \
  docs/PLATFORM_ROADMAP_V1.md \
  docs/UI_STANDARDS_V1.md \
  scripts/git_cleanup_architecture_docs_v1.sh \
  scripts/git_cleanup_docs_remaining_v1.sh

git status --short

echo "VERDICT=GIT_CLEANUP_DOCS_REMAINING_V1_READY"
