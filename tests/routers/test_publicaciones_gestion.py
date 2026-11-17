from collections.abc import Callable
from http import HTTPStatus

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from alquilometro_api.core.database import get_engine
from alquilometro_api.semilla import cargar_publicaciones_de_ejemplo

Autenticar = Callable[..., dict[str, str]]


def datos(**cambios: object) -> dict[str, object]:
    base: dict[str, object] = {
        'propiedad': {
            'direccion': 'Avenida Rivadavia 5500',
            'zona': 'Caballito',
            'tipo': 'departamento',
            'ambientes': 2,
        },
        'precio_alquiler': {'monto': '650000', 'moneda': 'ARS'},
    }
    return base | cambios


@pytest.fixture
def aviso_id(cliente: TestClient, headers_inmobiliaria: dict[str, str]) -> int:
    respuesta = cliente.post(
        '/publicaciones', json=datos(), headers=headers_inmobiliaria
    )
    return respuesta.json()['id']


# --- lectura --------------------------------------------------------------


def test_get_by_id_returns_the_listing(
    cliente: TestClient, aviso_id: int
) -> None:
    respuesta = cliente.get(f'/publicaciones/{aviso_id}')

    assert respuesta.status_code == HTTPStatus.OK
    assert respuesta.json()['id'] == aviso_id
    assert respuesta.json()['propiedad']['zona'] == 'Caballito'


def test_get_missing_listing_is_404(cliente: TestClient) -> None:
    assert (
        cliente.get('/publicaciones/999').status_code == HTTPStatus.NOT_FOUND
    )


# --- edición --------------------------------------------------------------


def test_owner_updates_the_listing(
    cliente: TestClient, aviso_id: int, headers_inmobiliaria: dict[str, str]
) -> None:
    nuevo = datos(
        propiedad={
            'direccion': 'Avenida Rivadavia 5500',
            'zona': 'Palermo',
            'tipo': 'ph',
            'ambientes': 3,
        },
        precio_alquiler={'monto': '720000', 'moneda': 'ARS'},
        comision={'monto': '720000', 'moneda': 'ARS'},
    )

    respuesta = cliente.put(
        f'/publicaciones/{aviso_id}', json=nuevo, headers=headers_inmobiliaria
    )

    assert respuesta.status_code == HTTPStatus.OK
    cuerpo = cliente.get(f'/publicaciones/{aviso_id}').json()
    assert cuerpo['propiedad']['zona'] == 'Palermo'
    assert cuerpo['precio_alquiler']['monto'] == '720000.00'
    assert cuerpo['comision']['monto'] == '720000.00'


def test_update_with_invalid_data_is_422(
    cliente: TestClient, aviso_id: int, headers_inmobiliaria: dict[str, str]
) -> None:
    invalido = datos(precio_alquiler={'monto': '0', 'moneda': 'ARS'})

    respuesta = cliente.put(
        f'/publicaciones/{aviso_id}',
        json=invalido,
        headers=headers_inmobiliaria,
    )

    assert respuesta.status_code == HTTPStatus.UNPROCESSABLE_ENTITY


def test_update_missing_listing_is_404(
    cliente: TestClient, headers_inmobiliaria: dict[str, str]
) -> None:
    respuesta = cliente.put(
        '/publicaciones/999', json=datos(), headers=headers_inmobiliaria
    )

    assert respuesta.status_code == HTTPStatus.NOT_FOUND


# --- borrado --------------------------------------------------------------


def test_owner_deletes_the_listing(
    cliente: TestClient, aviso_id: int, headers_inmobiliaria: dict[str, str]
) -> None:
    respuesta = cliente.delete(
        f'/publicaciones/{aviso_id}', headers=headers_inmobiliaria
    )

    assert respuesta.status_code == HTTPStatus.NO_CONTENT
    assert cliente.get(f'/publicaciones/{aviso_id}').status_code == 404  # noqa: PLR2004
    assert cliente.get('/publicaciones').json() == []


def test_delete_missing_listing_is_404(
    cliente: TestClient, headers_inmobiliaria: dict[str, str]
) -> None:
    respuesta = cliente.delete(
        '/publicaciones/999', headers=headers_inmobiliaria
    )

    assert respuesta.status_code == HTTPStatus.NOT_FOUND


# --- permisos (P6) --------------------------------------------------------


@pytest.mark.parametrize(
    ('email', 'rol'),
    [
        ('ajena@example.com', 'INMOBILIARIA'),
        ('busca@example.com', 'BUSCADOR'),
    ],
)
def test_only_the_owner_can_change_or_delete(
    cliente: TestClient,
    autenticar_como: Autenticar,
    aviso_id: int,
    email: str,
    rol: str,
) -> None:
    intruso = autenticar_como(email, rol)

    put = cliente.put(
        f'/publicaciones/{aviso_id}',
        json=datos(precio_alquiler={'monto': '1', 'moneda': 'ARS'}),
        headers=intruso,
    )
    borrar = cliente.delete(f'/publicaciones/{aviso_id}', headers=intruso)

    assert put.status_code == HTTPStatus.FORBIDDEN
    assert borrar.status_code == HTTPStatus.FORBIDDEN
    intacto = cliente.get(f'/publicaciones/{aviso_id}').json()
    assert intacto['precio_alquiler']['monto'] == '650000.00'


def test_changes_require_a_token(cliente: TestClient, aviso_id: int) -> None:
    put = cliente.put(f'/publicaciones/{aviso_id}', json=datos())
    borrar = cliente.delete(f'/publicaciones/{aviso_id}')

    assert put.status_code == HTTPStatus.UNAUTHORIZED
    assert borrar.status_code == HTTPStatus.UNAUTHORIZED


def test_admin_can_change_and_delete_any_listing(
    cliente: TestClient, autenticar_como: Autenticar, aviso_id: int
) -> None:
    admin = autenticar_como('admin@example.com', 'ADMIN')

    put = cliente.put(
        f'/publicaciones/{aviso_id}', json=datos(), headers=admin
    )
    borrar = cliente.delete(f'/publicaciones/{aviso_id}', headers=admin)

    assert put.status_code == HTTPStatus.OK
    assert borrar.status_code == HTTPStatus.NO_CONTENT


def test_sample_listings_belong_to_the_system_not_to_inmobiliarias(
    cliente: TestClient,
    autenticar_como: Autenticar,
    headers_inmobiliaria: dict[str, str],
) -> None:
    with Session(get_engine()) as sesion:
        cargar_publicaciones_de_ejemplo(sesion)

    inmobiliaria = cliente.put(
        '/publicaciones/1', json=datos(), headers=headers_inmobiliaria
    )
    admin = cliente.put(
        '/publicaciones/1',
        json=datos(),
        headers=autenticar_como('admin@example.com', 'ADMIN'),
    )

    assert inmobiliaria.status_code == HTTPStatus.FORBIDDEN
    assert admin.status_code == HTTPStatus.OK


# --- costo de entrada (C3) -------------------------------------------------


def test_entry_cost_endpoint_separates_concepts_and_lists_missing(
    cliente: TestClient, headers_inmobiliaria: dict[str, str]
) -> None:
    publicacion = datos(
        deposito={'monto': '650000', 'moneda': 'ARS'},
        otros_gastos_entrada={'monto': '40000', 'moneda': 'ARS'},
    )
    creado = cliente.post(
        '/publicaciones', json=publicacion, headers=headers_inmobiliaria
    ).json()

    respuesta = cliente.get(f'/publicaciones/{creado["id"]}/costo-entrada')

    assert respuesta.status_code == HTTPStatus.OK
    cuerpo = respuesta.json()
    assert cuerpo['total'] == {'monto': '1340000.00', 'moneda': 'ARS'}
    assert set(cuerpo['componentes_informados']) == {
        'primer_mes',
        'deposito',
        'otros_gastos',
    }
    assert cuerpo['faltantes'] == ['comision', 'seguro_caucion']


def test_entry_cost_of_a_missing_listing_is_404(cliente: TestClient) -> None:
    respuesta = cliente.get('/publicaciones/999/costo-entrada')

    assert respuesta.status_code == HTTPStatus.NOT_FOUND


def test_analysis_includes_the_entry_cost(
    cliente: TestClient, autenticar: Autenticar, aviso_id: int
) -> None:
    cabecera = autenticar('busca@example.com')
    cliente.put(
        '/usuarios/me/ingreso-referencia',
        json={'monto': '1500000'},
        headers=cabecera,
    )

    respuesta = cliente.get(
        f'/publicaciones/{aviso_id}/analisis', headers=cabecera
    )

    assert respuesta.status_code == HTTPStatus.OK
    assert respuesta.json()['costo_entrada']['total'] == {
        'monto': '650000.00',
        'moneda': 'ARS',
    }
