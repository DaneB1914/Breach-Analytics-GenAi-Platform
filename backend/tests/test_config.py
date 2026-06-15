from app.core.config import DEFAULT_DATABASE_URL, get_settings


def test_settings_use_default_database_url(monkeypatch) -> None:
    monkeypatch.delenv("DATABASE_URL", raising=False)
    get_settings.cache_clear()

    settings = get_settings()

    assert settings.database_url == DEFAULT_DATABASE_URL

    get_settings.cache_clear()


def test_settings_read_database_url_from_environment(monkeypatch) -> None:
    database_url = "postgresql+psycopg://user:password@db:5432/example"
    monkeypatch.setenv("DATABASE_URL", database_url)
    get_settings.cache_clear()

    settings = get_settings()

    assert settings.database_url == database_url

    get_settings.cache_clear()
