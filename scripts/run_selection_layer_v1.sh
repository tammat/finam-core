#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python -m finam_core.research.selection_runner
