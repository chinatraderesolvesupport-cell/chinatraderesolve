from app import config


def test_maintenance_interval_defaults_to_one_hour(monkeypatch):
    monkeypatch.delenv("MAINTENANCE_INTERVAL_SECONDS", raising=False)

    assert config._maintenance_interval_seconds() == 3600


def test_maintenance_interval_clamps_legacy_minute_polling(monkeypatch):
    monkeypatch.setenv("MAINTENANCE_INTERVAL_SECONDS", "60")

    assert config._maintenance_interval_seconds() == 3600


def test_maintenance_interval_allows_slower_polling(monkeypatch):
    monkeypatch.setenv("MAINTENANCE_INTERVAL_SECONDS", "7200")

    assert config._maintenance_interval_seconds() == 7200


def test_maintenance_interval_has_bounded_maximum(monkeypatch):
    monkeypatch.setenv("MAINTENANCE_INTERVAL_SECONDS", "999999")

    assert config._maintenance_interval_seconds() == 86400
