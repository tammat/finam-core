#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core || exit 1

echo "=== RESEARCH_UNTRACKED_AUDIT_V1 ==="

git ls-files --others --exclude-standard \
  | grep -E '^(src/scripts/research/|scripts/test_).*(_v1|_v1_1)\.(py|sh)$' \
  | sort \
  | tee /tmp/research_untracked_audit_v1_files.txt || true

echo
echo "=== PY_COMPILE ==="
while read -r f; do
  [ -z "$f" ] && continue
  case "$f" in
    *.py)
      python3 -m py_compile "$f"
      echo "COMPILE_OK $f"
      ;;
    *.sh)
      bash -n "$f"
      echo "BASH_N_OK $f"
      ;;
  esac
done < /tmp/research_untracked_audit_v1_files.txt

echo
echo "=== SUMMARY ==="
files_total=$(wc -l < /tmp/research_untracked_audit_v1_files.txt | tr -d ' ')
echo "files_total=${files_total}"
echo "VERDICT=RESEARCH_UNTRACKED_AUDIT_READY"
echo "TEST_RESEARCH_UNTRACKED_AUDIT_V1_OK"
