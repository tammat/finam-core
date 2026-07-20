from pathlib import Path


def test_live_control_center_message_keys_are_localized() -> None:
    migration = Path(
        "sql/presentation/163_control_center_live_i18n_completeness_v2.sql"
    ).read_text(encoding="utf-8")
    for key in (
        "column.analysis.status",
        "column.fills.1h",
        "column.last.quote.at",
        "column.priority.rank",
        "column.waiting.candidates",
        "status.donchian_volatility_breakout_v1",
        "status.microstructure_verified",
        "status.reserve",
    ):
        assert key in migration
