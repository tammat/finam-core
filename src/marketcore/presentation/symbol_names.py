from __future__ import annotations

DISPLAY_NAMES = {
    "SBER@MISX": "Сбербанк",
    "GAZP@MISX": "Газпром",
    "LKOH@MISX": "Лукойл",
    "PLZL@MISX": "Полюс",
    "VTBR@MISX": "ВТБ",
    "NVTK@MISX": "Новатэк",
    "OZON@MISX": "Ozon",
    "CNYRUB_TOM@MISX": "Юань / рубль TOM",
    "USDRUBF@RTSX": "Фьючерс доллар / рубль",
    "CNYRUBF@RTSX": "Фьючерс юань / рубль",
    "BRQ6@RTSX": "Brent, август 2026",
    "BRU6@RTSX": "Brent, сентябрь 2026",
    "BRV6@RTSX": "Brent, октябрь 2026",
    "NGN6@RTSX": "Газ, июль 2026",
    "NGQ6@RTSX": "Газ, август 2026",
    "NGU6@RTSX": "Газ, сентябрь 2026",
    "GDU6@RTSX": "Золото, сентябрь 2026",
    "GLU6@RTSX": "Золото, сентябрь 2026",
    "SVU6@RTSX": "Серебро, сентябрь 2026",
    "BTCUSD": "Bitcoin / USD",
    "ETHUSD": "Ethereum / USD",
    "IMOEX": "Индекс МосБиржи",
}

def display_name(symbol: str) -> str:
    return DISPLAY_NAMES.get(symbol or "", "")
