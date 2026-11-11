from collections.abc import Iterator

import pytest
from sqlalchemy import Engine
from sqlalchemy.orm import Session

from alquilometro_api.core.database import Base, crear_engine


@pytest.fixture
def engine() -> Iterator[Engine]:
    """Base SQLite en memoria, limpia en cada test"""
    engine = crear_engine('sqlite://')
    Base.metadata.create_all(engine)
    yield engine
    Base.metadata.drop_all(engine)
    engine.dispose()


@pytest.fixture
def sesion(engine: Engine) -> Iterator[Session]:
    with Session(engine) as sesion:
        yield sesion
