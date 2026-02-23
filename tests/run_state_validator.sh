#!/usr/bin/env bash
set -euo pipefail

python -m tests.test_state_validator
python -m tests.test_accounting_validator
