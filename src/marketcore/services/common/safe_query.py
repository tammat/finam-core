from __future__ import annotations

from typing import Callable, TypeVar

T = TypeVar("T")


def safe_query(loader: Callable[[], T], fallback: T) -> T:
    """
    Выполняет запрос к БД.

    При любой ошибке
    (нет доступа,
     таблица отсутствует,
     SQL и т.д.)

    возвращает fallback.
    """

    try:
        return loader()
    except Exception:
        return fallback
