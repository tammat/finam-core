from decimal import Decimal
from pathlib import Path

from scripts.build_rvi_regime_feature_v1 import regime


def test_rvi_regime_boundaries() -> None:
    assert regime(Decimal("0.25")) == "LOW_VOL"
    assert regime(Decimal("0.50")) == "NORMAL_VOL"
    assert regime(Decimal("0.75")) == "HIGH_VOL"


def test_rvi_is_feature_only_and_scheduled() -> None:
    migration = Path("sql/analytics/236_rvi_shadow_feature_onboarding_v1.sql").read_text()
    service = Path("deploy/systemd/finam-v5-bars-fast.service").read_text()
    assert "VIU6@RTSX=M1" in service
    assert "is_tradable=false" in migration
    assert "paper_allowed boolean NOT NULL DEFAULT false" in migration
    assert "live_allowed boolean NOT NULL DEFAULT false" in migration
    assert "RVI_REGIME_FEATURE_V1" in migration
