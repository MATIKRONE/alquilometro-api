from collections.abc import Iterator
from functools import lru_cache
from typing import Any

from sqlalchemy import Engine, create_engine, event
from sqlalchemy.engine import make_url
from sqlalchemy.orm import DeclarativeBase, Session
from sqlalchemy.pool import StaticPool

from alquilometro_api.core.config import get_config


class Base(DeclarativeBase):
    """
    Base declarativa de todos los modelos SQLalchemy
    """


def _activar_fk(conexion: Any, _registro: Any) -> None:
    # SQLite ignora las claves foráneas salvo que se active el pragma;
    # PostgreSQL siempre las aplica: así ambos se comportan igual
    cursor = conexion.cursor()
    cursor.execute('PRAGMA foreign_keys=ON')
    cursor.close()


def crear_engine(url: str, *, echo: bool = False) -> Engine:
    parsed = make_url(url)
    if parsed.get_backend_name() != 'sqlite':
        return create_engine(url, echo=echo)

    opciones: dict[str, Any] = {'connect_args': {'check_same_thread': False}}
    if parsed.database in {None, '', ':memory:'}:
        # En memoria, cada conexión sería una base distinta y vacía.
        opciones['poolclass'] = StaticPool
    engine = create_engine(url, echo=echo, **opciones)
    event.listen(engine, 'connect', _activar_fk)
    return engine


@lru_cache
def get_engine() -> Engine:
    config = get_config()
    return crear_engine(config.DATABASE_URL, echo=config.sql_echo)


def get_session() -> Iterator[Session]:
    """Dependencia de FastAPI: una sesión por request, siempre cerrada."""
    with Session(get_engine()) as sesion:
        yield sesion


def crear_tablas(engine: Engine | None = None) -> None:
    """Crea las tablas que falten (decisión F3: sin Alembic por ahora).

    Los modelos deben estar importados (`alquilometro_api.models`) para
    estar registrados en `Base.metadata`.
    """
    Base.metadata.create_all(engine or get_engine())
    # SQLite ignora
