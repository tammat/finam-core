#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_RESEARCH_ARTIFACT_INVENTORY_V1 ==="

echo
echo "===== ACTIVE PRODUCTION ====="

find src/scripts/research scripts \
  -type f \
  \( \
      -name "build_global_edge_forensic_engine_v1.py" \
   -o -name "test_global_edge_forensic_engine_v1.sh" \
   -o -name "test_global_edge_forensic_engine_metadata_fix_v1.sh" \
  \) | sort

echo
echo "===== UNTRACKED RESEARCH ====="

git ls-files --others --exclude-standard \
| grep -E '^(scripts|src/scripts/research)/' \
| sort

echo
echo "===== INVENTORY ====="

prod=0
research=0
obsolete=0

while read -r f
do
    [[ -z "$f" ]] && continue

    case "$f" in
        *global_edge_forensic_engine_v1* )
            cls="ACTIVE_PRODUCTION"
            ((prod+=1))
            ;;
        *gold*|*market_state*|*rs_bottom*|*equity*|*strategy_class*|*fast_winner*|*entry_exit*|*canonical_schema*|*compression* )
            cls="ACTIVE_RESEARCH"
            ((research+=1))
            ;;
        *)
            cls="UNKNOWN"
            ((obsolete+=1))
            ;;
    esac

    printf "%-20s %s\n" "$cls" "$f"

done < <(
git ls-files --others --exclude-standard \
| grep -E '^(scripts|src/scripts/research)/'
)

echo
echo "production=$prod"
echo "research=$research"
echo "unknown=$obsolete"

echo
echo "VERDICT=RESEARCH_ARTIFACT_INVENTORY_V1_READY"

echo
echo "TEST_RESEARCH_ARTIFACT_INVENTORY_V1_OK"

