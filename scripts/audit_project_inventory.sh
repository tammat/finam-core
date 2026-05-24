#!/usr/bin/env bash
set -euo pipefail

mkdir -p reports

grep -R --exclude-dir='__pycache__' "class .*Repository\|Repository(" -n src/finam_core src/scripts | sort \
  > reports/repositories_inventory.txt

grep -R --exclude-dir='__pycache__' "CREATE TABLE IF NOT EXISTS" -n src scripts | sort \
  > reports/postgres_tables_inventory.txt

grep -R --exclude-dir='__pycache__' "os.getenv\|os.environ" -n src scripts \
  | grep -v "^scripts/test_" \
  | sort > reports/runtime_env_inventory.txt

grep -R --exclude-dir='__pycache__' "os.getenv\|os.environ" -n scripts/test_* src/scripts/test_* 2>/dev/null \
  | sort > reports/test_env_inventory.txt || true

grep -R --exclude-dir='__pycache__' "argparse.ArgumentParser\|add_argument" -n src scripts \
  | sort > reports/cli_args_inventory.txt

echo "PROJECT_INVENTORY_OK"
wc -l reports/*inventory.txt
