#data/contract_mapper.py

# Русский коммент: маппинг "фронт-контрактов"

from data.expiry_calendar import get_active_contract

SUFFIX = "@RTSX"

FRONT_MAP = {
    "NG_FRONT": "NG",
    "BR_FRONT": "BR",
    "GC_FRONT": "GC",
    "SI_FRONT": "SI",
    "SR_FRONT": "SR",
}
CALENDAR = {
    "NG": ["NGH6", "NGM6", "NGU6"],
    "BR": ["BRM6", "BRN6", "BRU6"],  # ← ДОБАВИТЬ
    "GC": ["GCM6", "GCQ6", "GCZ6"],
}
def resolve(symbol: str) -> str:
    """
    NG_FRONT → NGH6@RTSX
    BR_FRONT → BRM6@RTSX
    GC_FRONT → GCM6@RTSX
    """
    # если не фронт — возвращаем как есть
    base = FRONT_MAP.get(symbol)
    if not base:
        return symbol

    contract = get_active_contract(base)
    if not contract:
        return symbol

    return f"{contract}{SUFFIX}"