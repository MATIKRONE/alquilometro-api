from decimal import Decimal
from http import HTTPStatus

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from alquilometro_api.core.database import get_engine
from alquilometro_api.semilla import cargar_icl_de_ejemplo

MESES = [12, 24]


def publicacion(**cambios: object) -> dict[str, object]:
    datos: dict[str, object] = {
        'propiedad': {
            'direccion': 'Avenida Rivadavia 5500',
            'zona': 'Caballito',
            'tipo': 'departamento',
            'ambientes': 2,
        },
        'precio_alquiler': {'monto': '500000', 'moneda': 'ARS'},
        'expensas_mensuales': {'monto': '80000', 'moneda': 'ARS'},
        'tipo_ajuste': 'INDICE',
        'serie_codigo': 'ICL',
    }
    datos.update(cambios)
    return datos


@pytest.fixture
def headers_inquilino(cliente: TestClient) -> dict[str, str]:
    """Inquilina con ingreso de referencia y el ICL de ejemplo cargado."""
    with Session(get_engine()) as sesion:
        cargar_icl_de_ejemplo(sesion)
    cliente.post(
        '/auth/registro',
        json={
            'nombre': 'Inés',
            'email': 'ines@example.com',
            'password': 'clave-123456',
        },
    )
    token = cliente.post(
        '/auth/login',
        json={'email': 'ines@example.com', 'password': 'clave-123456'},
    ).json()['access_token']
    headers = {'Authorization': f'Bearer {token}'}
    cliente.put(
        '/usuarios/me/ingreso-referencia',
        json={'monto': '2000000', 'moneda': 'ARS'},
        headers=headers,
    )
    return headers


def publicar(
    cliente: TestClient, headers: dict[str, str], datos: dict[str, object]
) -> int:
    respuesta = cliente.post('/publicaciones', json=datos, headers=headers)
    assert respuesta.status_code == HTTPStatus.CREATED
    return respuesta.json()['id']


def test_proyeccion_por_indice_con_el_promedio_historico(
    cliente: TestClient,
    headers_inmobiliaria: dict[str, str],
    headers_inquilino: dict[str, str],
) -> None:
    publicacion_id = publicar(cliente, headers_inmobiliaria, publicacion())

    respuesta = cliente.get(
        f'/publicaciones/{publicacion_id}/proyeccion',
        headers=headers_inquilino,
    )

    proyeccion = respuesta.json()
    assert respuesta.status_code == HTTPStatus.OK
    assert proyeccion['serie'] == 'ICL'
    assert proyeccion['fecha_referencia'] == '2026-12-01'
    assert proyeccion['escenario']['origen'] == 'PROMEDIO_ULTIMOS_12_MESES'
    assert Decimal(proyeccion['escenario']['tasa_mensual_porcentual']) == (
        Decimal('2.50')
    )
    assert [m['mes'] for m in proyeccion['meses']] == MESES
    assert proyeccion['meses'][0]['porcentaje_ingreso'] is not None
    assert 'abl' in proyeccion['faltantes']


def test_proyeccion_con_una_tasa_indicada(
    cliente: TestClient,
    headers_inmobiliaria: dict[str, str],
    headers_inquilino: dict[str, str],
) -> None:
    publicacion_id = publicar(cliente, headers_inmobiliaria, publicacion())

    respuesta = cliente.get(
        f'/publicaciones/{publicacion_id}/proyeccion',
        params={'tasa_mensual': '0'},
        headers=headers_inquilino,
    )

    mes_12 = respuesta.json()['meses'][0]
    assert respuesta.json()['escenario']['origen'] == 'TASA_INDICADA'
    assert Decimal(mes_12['alquiler']['monto']) == Decimal('500000')
    assert Decimal(mes_12['costo_mensual']['monto']) == Decimal('580000')
    assert Decimal(mes_12['porcentaje_ingreso']) == Decimal('29.00')


def test_sin_mecanismo_de_ajuste_no_se_proyecta(
    cliente: TestClient,
    headers_inmobiliaria: dict[str, str],
    headers_inquilino: dict[str, str],
) -> None:
    datos = publicacion(tipo_ajuste=None, serie_codigo=None)
    publicacion_id = publicar(cliente, headers_inmobiliaria, datos)

    respuesta = cliente.get(
        f'/publicaciones/{publicacion_id}/proyeccion',
        headers=headers_inquilino,
    )

    assert respuesta.status_code == HTTPStatus.UNPROCESSABLE_ENTITY


def test_proyectar_requiere_login(
    cliente: TestClient, headers_inmobiliaria: dict[str, str]
) -> None:
    publicacion_id = publicar(cliente, headers_inmobiliaria, publicacion())

    respuesta = cliente.get(f'/publicaciones/{publicacion_id}/proyeccion')

    assert respuesta.status_code == HTTPStatus.UNAUTHORIZED
