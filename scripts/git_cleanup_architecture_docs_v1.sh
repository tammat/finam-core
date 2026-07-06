#!/usr/bin/env bash
set -euo pipefail

echo "=== GIT_CLEANUP_ARCHITECTURE_DOCS_V1 ==="

# 1. Разрешаем версионировать архитектурные TXT в docs
if ! grep -q '^!docs/\*.txt' .gitignore; then
cat >> .gitignore <<'EOF'

# Project documentation exceptions
!docs/*.txt
!docs/*.md
!PROJECT_STATUS.md
!ROADMAP.md
!ARCHITECTURE.md
EOF
fi

# 2. Удаляем случайный файл с точкой в конце, если он есть
if [ -f "DECISIONS.md." ]; then
  rm -f "DECISIONS.md."
fi

# 3. Проверяем, что документ доступен Git
git add .gitignore docs/ARCHITECTURE_DECISIONS_V1.txt

git status --short

echo "VERDICT=GIT_CLEANUP_ARCHITECTURE_DOCS_V1_READY"
