# -*- coding: utf-8 -*-
"""
Единая настройка логирования для всего проекта.

Правила:
- по умолчанию уровень WARNING (тихо)
- --debug или --log-level DEBUG включает подробности
- без дублирования хендлеров при повторных импортах
"""

from __future__ import annotations

import logging
import os
import sys
from typing import Optional


def setup_logging(
    level: Optional[str] = None,
    *,
    debug: bool = False,
) -> None:
    """
    Русский коммент:
    Настраиваем root logger один раз.
    Повторный вызов безопасен: не добавляем хендлеры повторно.
    """
    root = logging.getLogger()

    # Если уже настроено (есть хендлеры) — не дублируем.
    if root.handlers:
        # но уровень можно обновить
        root.setLevel(_resolve_level(level, debug))
        return

    lvl = _resolve_level(level, debug)
    root.setLevel(lvl)

    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(lvl)

    fmt = os.getenv(
        "LOG_FORMAT",
        "%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )
    datefmt = os.getenv("LOG_DATEFMT", "%H:%M:%S")

    handler.setFormatter(logging.Formatter(fmt=fmt, datefmt=datefmt))
    root.addHandler(handler)


def _resolve_level(level: Optional[str], debug: bool) -> int:
    if debug:
        return logging.DEBUG
    if not level:
        # по умолчанию — тихо
        return logging.WARNING
    lvl = str(level).upper().strip()
    return getattr(logging, lvl, logging.WARNING)
