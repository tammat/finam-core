#!/usr/bin/env bash
set -euo pipefail

echo "=== MULTI_ASSET_DASHBOARD_RU_MENU_AND_COMPRESSION_SUMMARY_V1 ==="

html="$(curl -fsS http://127.0.0.1:8088/summary)"

echo "$html" | grep -q "Рейтинг Edge"
echo "$html" | grep -q "Сжатие"
echo "$html" | grep -q "История сжатия"

echo "$html" | grep -q "Сжатие / расширение"
echo "$html" | grep -q "снимков истории"
echo "$html" | grep -q "строк истории"
echo "$html" | grep -q "событий сжатия"
echo "$html" | grep -q "кандидатов расширения"

echo "VERDICT=MULTI_ASSET_DASHBOARD_RU_MENU_AND_COMPRESSION_SUMMARY_OK"
echo "TEST_MULTI_ASSET_DASHBOARD_RU_MENU_AND_COMPRESSION_SUMMARY_V1_OK"
