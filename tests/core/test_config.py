import pytest

from alquilometro_api.core.config import Configuracion, get_config


def test_defaults_to_local_sqlite(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv('DATABASE_URL', raising=False)
    monkeypatch.delenv('SQL_ECHO', raising=False)

    config = Configuracion(_env_file=None)

    assert config.DATABASE_URL == 'sqlite:///./alquilometro.db'
    assert config.sql_echo is False


def test_environment_variables_override_defaults(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv('DATABASE_URL', 'postgresql+psycopg://u:p@db/x')
    monkeypatch.setenv('SQL_ECHO', 'true')

    config = Configuracion(_env_file=None)

    assert config.DATABASE_URL == 'postgresql+psycopg://u:p@db/x'
    assert config.sql_echo is True


def test_values_are_read_from_env_file(
    monkeypatch: pytest.MonkeyPatch, tmp_path: pytest.TempPathFactory
) -> None:
    monkeypatch.delenv('DATABASE_URL', raising=False)
    archivo = tmp_path / '.env'  # type: ignore[operator]
    archivo.write_text('DATABASE_URL=sqlite:///./otra.db\n')

    config = Configuracion(_env_file=archivo)

    assert config.DATABASE_URL == 'sqlite:///./otra.db'


def test_obtener_configuracion_is_cached() -> None:
    assert get_config() is get_config()
