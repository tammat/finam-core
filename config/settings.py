# config/settings.py

import os  # стандартная библиотека для работы с переменными окружения
from dotenv import load_dotenv  # загрузка переменных из файла .env

load_dotenv()  # инициализация загрузки .env при старте приложения


class Settings:
    """
    Централизованная конфигурация торгового ядра и RiskStack v2.
    Все параметры читаются из .env, но имеют безопасные значения по умолчанию.
    """

    # ==============================
    # Режим работы системы
    # ==============================

    MODE = os.getenv("MODE", "SIM")
    # Режим работы: SIM (симуляция) или REAL (боевой режим)

    INITIAL_CASH = float(os.getenv("INITIAL_CASH", 100_000))
    # Начальный капитал для симуляции / тестирования


    # ==============================
    # Legacy core ограничения (базовое ядро)
    # ==============================

    MAX_POSITION = int(os.getenv("MAX_POSITION", 10))
    # Максимальное количество контрактов в одной позиции (штучный лимит)

    MAX_EXPOSURE = float(os.getenv("MAX_EXPOSURE", 100_000))
    # Максимальная суммарная экспозиция портфеля в абсолютных значениях

    DEFAULT_SLIPPAGE = float(os.getenv("DEFAULT_SLIPPAGE", 0.0))
    # Проскальзывание по умолчанию (используется в симуляции)


    # ==============================
    # RiskStack v2 конфигурация
    # ==============================

    MAX_DAILY_LOSS_PCT = (
        float(os.getenv("MAX_DAILY_LOSS_PCT"))
        if os.getenv("MAX_DAILY_LOSS_PCT") is not None
        else None
    )
    # Максимально допустимая дневная просадка (% от стартового капитала)
    # None = правило отключено

    MAX_DRAWDOWN_PCT = (
        float(os.getenv("MAX_DRAWDOWN_PCT"))
        if os.getenv("MAX_DRAWDOWN_PCT") is not None
        else None
    )
    # Максимальная просадка от исторического пика equity (%)
    # None = правило отключено

    MAX_POSITION_PCT = (
        float(os.getenv("MAX_POSITION_PCT"))
        if os.getenv("MAX_POSITION_PCT") is not None
        else None
    )
    # Максимальный размер одной позиции (% от equity)
    # None = правило отключено

    MAX_GROSS_EXPOSURE_PCT = (
        float(os.getenv("MAX_GROSS_EXPOSURE_PCT"))
        if os.getenv("MAX_GROSS_EXPOSURE_PCT") is not None
        else None
    )
    # Максимальная валовая экспозиция портфеля (% от equity)
    # None = правило отключено

    MAX_PORTFOLIO_HEAT = (
        float(os.getenv("MAX_PORTFOLIO_HEAT"))
        if os.getenv("MAX_PORTFOLIO_HEAT") is not None
        else None
    )
    # Абсолютный лимит риска портфеля (portfolio heat)
    # None = правило отключено

    CORRELATION_THRESHOLD = float(os.getenv("CORRELATION_THRESHOLD", 0.8))
    # Порог корреляции инструментов (по умолчанию 0.8 — текущее поведение сохранено)