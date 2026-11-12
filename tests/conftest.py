from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import Engine
from sqlalchemy.orm import Session

from alquilometro_api.app import app
from alquilometro_api.core.config import get_config
from alquilometro_api.core.database import (
    Base,
    crear_engine,
    get_engine,
)


def cerrar_engine_cacheado() -> None:
    """Libera la conexión que get_engine guarda en caché."""
    if get_engine.cache_info().currsize:
        get_engine().dispose()

    get_engine.cache_clear()


@pytest.fixture(autouse=True)
def limpiar_caches() -> Iterator[None]:
    cerrar_engine_cacheado()
    get_config.cache_clear()

    yield

    cerrar_engine_cacheado()
    get_config.cache_clear()


@pytest.fixture
def engine() -> Iterator[Engine]:
    """Base SQLite en memoria, limpia para cada test."""
    engine = crear_engine('sqlite://')
    Base.metadata.create_all(engine)

    yield engine

    Base.metadata.drop_all(engine)
    engine.dispose()


@pytest.fixture
def sesion(engine: Engine) -> Iterator[Session]:
    """Sesión SQLAlchemy asociada a la base del test."""
    with Session(engine) as sesion:
        yield sesion


@pytest.fixture
def cliente(monkeypatch: pytest.MonkeyPatch) -> Iterator[TestClient]:
    """Cliente HTTP que usa una SQLite temporal en memoria."""
    monkeypatch.setenv('DATABASE_URL', 'sqlite://')

    with TestClient(app) as cliente:
        yield cliente
