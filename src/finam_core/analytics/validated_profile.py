from dataclasses import dataclass


@dataclass(frozen=True)
class ValidatedProfile:
    symbol: str
    strategy: str
    timeframe: str
    market_session: str
    hour_utc: int
    min_trades: int
    min_winrate: float
    min_net_pnl: float


BR_M5_VALIDATED_PROFILES = [
    ValidatedProfile(
        symbol="BRM6@RTSX",
        strategy="BR_CONSERVATIVE_BREAKOUT",
        timeframe="M5",
        market_session="morning",
        hour_utc=9,
        min_trades=30,
        min_winrate=0.55,
        min_net_pnl=1.0,
    )
]


def is_validated_profile(
    symbol: str,
    strategy: str,
    timeframe: str,
    hour_utc: int,
) -> bool:
    for profile in BR_M5_VALIDATED_PROFILES:
        if (
            profile.symbol == symbol
            and profile.strategy == strategy
            and profile.timeframe == timeframe
            and profile.hour_utc == hour_utc
        ):
            return True

    return False
