#!/usr/bin/env bash
set -euo pipefail

ENV_FILE="${1:-.env}"

test -f "$ENV_FILE"

DUP_KEYS=$(grep -v '^#' "$ENV_FILE" | grep '=' | cut -d= -f1 | sort | uniq -d || true)

if [ -n "$DUP_KEYS" ]; then
  echo "ENV_DUPLICATE_KEYS_FOUND"
  echo "$DUP_KEYS"
  exit 1
fi

grep -q '^TG_AI_TOKEN=' "$ENV_FILE" || { echo "ENV_MISSING_TG_AI_TOKEN"; exit 1; }
grep -q '^TG_PROXY=' "$ENV_FILE" || { echo "ENV_MISSING_TG_PROXY"; exit 1; }
grep -q '^TG_STRATEGY_STATUS_CHAT_ID=-100' "$ENV_FILE" || { echo "ENV_BAD_TG_STRATEGY_STATUS_CHAT_ID"; exit 1; }

if grep -q 'TG_STRATEGY_STATUS_CHAT_ID=' <(grep '^TG_PROXY=' "$ENV_FILE"); then
  echo "ENV_BROKEN_TG_PROXY_LINE"
  exit 1
fi

if grep -q '^TELEGRAM_CHAT_ID=' "$ENV_FILE"; then
  echo "ENV_WARNING_TELEGRAM_CHAT_ID_PRESENT_USE_TG_STRATEGY_STATUS_CHAT_ID"
fi

grep -q '^DATABASE_URL=' "$ENV_FILE" || { echo "ENV_MISSING_DATABASE_URL"; exit 1; }

echo "ENV_CONSISTENCY_OK file=$ENV_FILE"
