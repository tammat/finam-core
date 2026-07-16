from pathlib import Path


def test_observation_lineage_gap_has_ru_catalog_entry() -> None:
    migration = Path("sql/presentation/066_control_center_observation_lineage_i18n_v1.sql").read_text()
    assert "status.observation_id_link_gap" in migration
    assert "Не найдена сквозная связь по идентификатору наблюдения" in migration
    assert "ON CONFLICT (resource_key, locale_code) DO UPDATE" in migration
