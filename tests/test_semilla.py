from decimal import Decimal
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from alquilometro_api import semilla
from alquilometro_api.domain.errores import ValidacionError
from alquilometro_api.domain.moneda import Moneda
from alquilometro_api.domain.rol import Rol
from alquilometro_api.models.publicacion import Publicacion
from alquilometro_api.models.usuario import Usuario
from alquilometro_api.services.indices import RepositorioIndicesDB


def todas(sesion: Session) -> list[Publicacion]:
    return list(sesion.scalars(select(Publicacion)))


# --- P4: avisos de ejemplo -------------------------------------------------


def test_sample_listings_are_between_15_and_30(sesion: Session) -> None:
    creados = semilla.cargar_publicaciones_de_ejemplo(sesion)

    assert 15 <= creados <= 30  # noqa: PLR2004
    assert len(todas(sesion)) == creados


def test_sample_listings_are_loaded_only_once(sesion: Session) -> None:
    semilla.cargar_publicaciones_de_ejemplo(sesion)

    assert semilla.cargar_publicaciones_de_ejemplo(sesion) == 0
    assert len(todas(sesion)) == len(semilla.AVISOS_DE_EJEMPLO)


def test_sample_listings_belong_to_a_system_admin(sesion: Session) -> None:
    semilla.cargar_publicaciones_de_ejemplo(sesion)

    duenos = {p.publicador.email for p in todas(sesion)}
    assert duenos == {semilla.EMAIL_SISTEMA}
    sistema = sesion.scalars(select(Usuario)).one()
    assert sistema.rol is Rol.ADMIN


def test_system_user_password_cannot_be_guessed(sesion: Session) -> None:
    from alquilometro_api.core.seguridad import verificar_password  # noqa: PLC0415

    sistema = semilla.crear_usuario_sistema(sesion)

    assert not verificar_password('', sistema.password_hash)
    assert not verificar_password('sistema', sistema.password_hash)


def test_sample_listings_are_varied(sesion: Session) -> None:
    semilla.cargar_publicaciones_de_ejemplo(sesion)
    avisos = todas(sesion)

    assert {p.precio_alquiler.moneda for p in avisos} == set(Moneda)
    assert {p.tipo_ajuste for p in avisos} == {'FIJO', 'INDICE', None}
    assert {p.serie_codigo for p in avisos} >= {'ICL', 'IPC'}
    assert len({p.propiedad.zona for p in avisos}) >= 8  # noqa: PLR2004
    assert {p.propiedad.tipo for p in avisos} == {'departamento', 'casa', 'ph'}
    assert any(p.patrocinada for p in avisos)
    assert any(p.propiedad.metros_cuadrados is None for p in avisos)
    assert any(p.expensas_mensuales is None for p in avisos)
    assert any(p.propiedad.permite_mascotas is False for p in avisos)
    assert all(p.fuente == semilla.FUENTE_SEMILLA for p in avisos)


def test_every_sample_listing_has_computable_costs(sesion: Session) -> None:
    semilla.cargar_publicaciones_de_ejemplo(sesion)

    for aviso in todas(sesion):
        assert aviso.calcular_costo_real().total.monto > 0
        assert aviso.calcular_costo_entrada().total.monto > 0


def test_sample_listings_are_searchable_through_the_api(
    cliente: TestClient,
) -> None:
    from alquilometro_api.core.database import get_engine  # noqa: PLC0415

    with Session(get_engine()) as sesion:
        semilla.cargar_publicaciones_de_ejemplo(sesion)

    todos = cliente.get('/publicaciones').json()
    palermo = cliente.get('/publicaciones', params={'zona': 'Palermo'}).json()

    assert len(todos) == len(semilla.AVISOS_DE_EJEMPLO)
    assert palermo
    assert all(p['propiedad']['zona'] == 'Palermo' for p in palermo)


# --- I2: series ICL e IPC ----------------------------------------------------


def test_icl_sample_has_24_monthly_values(sesion: Session) -> None:
    assert semilla.cargar_icl_de_ejemplo(sesion) == semilla.MESES_DE_SERIE

    assert len(RepositorioIndicesDB(sesion).listar('ICL')) == 24  # noqa: PLR2004


def test_ipc_is_a_level_series_built_from_monthly_variations(
    sesion: Session,
) -> None:
    cantidad = semilla.cargar_ipc_de_ejemplo(sesion)

    valores = RepositorioIndicesDB(sesion).listar('IPC')
    niveles = [v.valor for v in valores]
    assert cantidad == len(semilla.IPC_VARIACIONES) == len(valores)
    assert niveles[0] == Decimal('120.60')  # 100 x 1,206 (enero 2024)
    assert niveles == sorted(niveles)
    assert valores[0].fecha.isoformat() == '2024-01-01'


def test_both_series_can_be_loaded_together(sesion: Session) -> None:
    semilla.cargar_icl_de_ejemplo(sesion)
    semilla.cargar_ipc_de_ejemplo(sesion)

    repo = RepositorioIndicesDB(sesion)
    assert repo.listar('ICL')
    assert repo.listar('IPC')


def test_csv_loader_accepts_header_blank_lines_and_updates(
    sesion: Session,
) -> None:
    contenido = 'fecha,valor\n2025-01-01,100.5\n\n2025-02-01,101.25\n'

    cargados = semilla.cargar_serie_desde_csv(sesion, 'ICL', contenido)
    semilla.cargar_serie_desde_csv(sesion, 'ICL', '2025-01-01,110\n')

    valores = RepositorioIndicesDB(sesion).listar('ICL')
    assert cargados == 2  # noqa: PLR2004
    assert [v.valor for v in valores] == [Decimal('110'), Decimal('101.25')]


@pytest.mark.parametrize('contenido', ['2025-01-01,abc\n', '2025-01-01\n'])
def test_csv_loader_rejects_bad_rows_after_the_first(
    sesion: Session, contenido: str
) -> None:
    with pytest.raises(ValidacionError):
        semilla.cargar_serie_desde_csv(
            sesion, 'ICL', '2025-01-01,1\n' + contenido
        )


def test_main_loads_everything_and_csv_option(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setenv('DATABASE_URL', f'sqlite:///{tmp_path / "demo.db"}')
    monkeypatch.setenv('ADMIN_EMAIL', 'admin@example.com')
    monkeypatch.setenv('ADMIN_PASSWORD', 'clave-segura-123')

    semilla.main([])
    salida = capsys.readouterr().out
    archivo = tmp_path / 'icl.csv'
    archivo.write_text('fecha,valor\n2026-01-01,300\n', encoding='utf-8')
    semilla.main(['--csv', 'ICL', str(archivo)])

    assert 'IPC (INDEC): 22' in salida
    assert 'Avisos de ejemplo: 20' in salida
    assert 'Administrador listo: admin@example.com' in salida
    assert 'ICL: 1 valores cargados.' in capsys.readouterr().out
