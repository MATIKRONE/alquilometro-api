from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import Engine, inspect, text
from sqlalchemy.orm import Mapped, Session, mapped_column

from alquilometro_api.app import app
from alquilometro_api.core import database
from alquilometro_api.core.database import (
    Base,
    crear_engine,
    crear_tablas,
    get_session,
)


class TablaDePrueba(Base):
    __tablename__ = 'tabla_de_prueba'

    id: Mapped[int] = mapped_column(primary_key=True)


@pytest.fixture(autouse=True, scope='module')
def _aislar_tabla_de_prueba() -> Iterator[None]:
    # Solo en este módulo: la tabla no debe existir ara otros tests.
    yield
    Base.metadata.remove(TablaDePrueba.__table__)


def test_in_memory_engine_shares_one_database_across_connections() -> None:
    engine = crear_engine('sqlite://')
    with engine.begin() as conexion:
        conexion.execute(text('CREATE TABLE t (id INTEGER)'))
        conexion.execute(text('INSERT INTO t VALUES (7)'))

    with engine.connect() as otra:
        assert otra.execute(text('SELECT id FROM t')).scalar_one() == 7  # noqa: PLR2004


def test_foreign_keys_are_enforced(engine: Engine) -> None:
    with engine.connect() as conexion:
        assert conexion.execute(text('PRAGMA foreign_keys')).scalar_one() == 1


def test_file_database_persists_between_engines(tmp_path: Path) -> None:
    url = f'sqlite:///{tmp_path / "datos.db"}'
    primero = crear_engine(url)
    with primero.begin() as conexion:
        conexion.execute(text('CREATE TABLE t (id INTEGER)'))
    primero.dispose()

    segundo = crear_engine(url)

    assert 't' in inspect(segundo).get_table_names()


def test_crear_tablas_creates_missing_tables_and_is_idempotent() -> None:
    engine = crear_engine('sqlite://')

    crear_tablas(engine)
    crear_tablas(engine)

    assert 'tabla_de_prueba' in inspect(engine).get_table_names()


def test_sesion_fixture_can_persist_and_read(sesion: Session) -> None:
    sesion.add(TablaDePrueba(id=1))
    sesion.commit()

    assert sesion.get(TablaDePrueba, 1) is not None


def test_obtener_sesion_yields_a_session_and_closes_it(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv('DATABASE_URL', 'sqlite://')
    generador = get_session()

    sesion = next(generador)
    assert sesion.execute(text('SELECT 1')).scalar_one() == 1
    assert sesion.in_transaction()

    generador.close()
    assert not sesion.in_transaction()


def test_app_startup_creates_tables(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    ruta = tmp_path / 'arranque.db'
    monkeypatch.setenv('DATABASE_URL', f'sqlite:///{ruta}')

    with TestClient(app):
        pass

    assert (
        'tabla_de_prueba'
        in inspect(crear_engine(f'sqlite:///{ruta}')).get_table_names()
    )


def test_non_sqlite_urls_get_no_sqlite_specific_options(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    llamadas: list[tuple[tuple, dict]] = []
    monkeypatch.setattr(
        database,
        'create_engine',
        lambda *args, **kwargs: llamadas.append((args, kwargs)),
    )

    database.crear_engine('postgresql+psycopg://u:p@db/x', echo=True)

    assert llamadas == [(('postgresql+psycopg://u:p@db/x',), {'echo': True})]
