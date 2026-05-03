# src/data/expiry_calendar.py

# Русский коммент:
# Простейший календарь экспираций + выбор фронта (как у фонда, но упрощённо)

from datetime import datetime

# Формат: YYYY-MM-DD
EXPIRY = {
    "NGH6": "2026-03-20",
    "NGM6": "2026-04-20",
    "NGU6": "2026-05-20",

    "BRM6": "2026-05-01",
    "BRN6": "2026-06-01",
    "BRU6": "2026-07-01",

    "GCM6": "2026-05-25",
    "GCQ6": "2026-06-25",
    "GCZ6": "2026-07-25",

    "SIH6": "2026-03-15",
    "SIM6": "2026-06-15",
    "SIU6": "2026-09-15",

    "SRH6": "2026-03-20",
    "SRM6": "2026-06-20",
    "SRU6": "2026-09-20",
}

CALENDAR = {
    "NG": ["NGH6", "NGM6", "NGU6"],
    "BR": ["BRM6", "BRN6", "BRU6"],
    "GC": ["GCM6", "GCQ6", "GCZ6"],
    "SI": ["SIH6", "SIM6", "SIU6"],  # серебро (MOEX)
    "SR": ["SRH6", "SRM6", "SRU6"],  # USD/RUB
}


def get_active_contract(base: str) -> str | None:
    """
    Выбираем ближайший НЕ истёкший контракт
    """

    contracts = CALENDAR.get(base)
    if not contracts:
        return None

    now = datetime.utcnow()

    for c in contracts:
        exp = EXPIRY.get(c)
        if not exp:
            continue

        exp_dt = datetime.fromisoformat(exp)

        if exp_dt > now:
            return c

    return None