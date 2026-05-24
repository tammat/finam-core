#!/usr/bin/env bash
set -euo pipefail

mkdir -p reports

{
  echo "# Finam_Core Project Gap Analysis"
  echo
  echo "## Git"
  git branch --show-current
  git log -1 --oneline
  git status --short
  echo

  echo "## Top-level structure"
  find src/finam_core -maxdepth 2 -type d | sort
  echo

  echo "## Runtime / Risk / Execution modules"
  find src/finam_core/runtime src/finam_core/risk src/finam_core/execution src/finam_core/pipelines -type f | sort
  echo

  echo "## PostgreSQL tables declared in code"
  grep -R --exclude-dir='__pycache__' "CREATE TABLE IF NOT EXISTS" -n src scripts | sort
  echo

  echo "## Repositories"
  grep -R --exclude-dir='__pycache__' "class .*Repository\|Repository(" -n src/finam_core src/scripts | sort
  echo

  echo "## RuntimeConfig usage"
  grep -R --exclude-dir='__pycache__' "RuntimeConfig\|runtime_config.get" -n src scripts | sort
  echo

  echo "## Direct os.getenv still present"
  grep -R --exclude-dir='__pycache__' "os.getenv" -n src scripts | sort
  echo

  echo "## Runtime governance tables usage"
  grep -R --exclude-dir='__pycache__' "runtime_regime_overrides\|runtime_strategy_scores\|runtime_active_universe\|strategy_regime_matrix" -n src scripts | sort
  echo

  echo "## Tests"
  find scripts -maxdepth 2 -type f -name "test_*.sh" | sort
  echo

} > reports/project_gap_analysis.md

echo "PROJECT_GAP_ANALYSIS_OK reports/project_gap_analysis.md"
