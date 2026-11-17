from decimal import Decimal
from http import HTTPStatus

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from alquilometro_api.core.database import get_engine
from alquilometro_api.semilla import cargar_icl_de_ejemplo, crear_admin

AJUSTES_EN_UN_ANIO = 3
MESES_DE_SERIE = 24


def token_de(cliente: TestClient, email: str, password: str) -> dict[str, str]:
    login = cliente.post(
        '/auth/login', json={'email': email, 'password': password}
    )
    assert login.status_code == HTTPStatus.OK
    return {'Authorization': f'Bearer {login.json()["access_token"]}'}


def registrar(cliente: TestClient, email: str) -> dict[str, str]:
    registro = cliente.post(
        '/auth/registro',
        json={'nombre': 'Inés', 'email': email, 'password': 'clave-123456'},
    )
    assert registro.status_code == HTTPStatus.CREATED
    return token_de(cliente, email, 'clave-123456')


@pytest.fixture
def headers(cliente: TestClient) -> dict[str, str]:
    """Inquilina logueada, con la serie ICL de ejemplo ya cargada."""
    with Session(get_engine()) as sesion:
        cargar_icl_de_ejemplo(sesion)
    return registrar(cliente, 'ines@example.com')


def contrato_icl() -> dict[str, object]:
    return {
        'fecha_inicio': '2025-01-01',
        'duracion_meses': 12,
        'monto_base': {'monto': '500000', 'moneda': 'ARS'},
        'tipo_ajuste': 'INDICE',
        'meses_periodicidad': 3,
        'serie_codigo': 'ICL',
    }


def crear_contrato(cliente: TestClient, headers: dict[str, str]) -> int:
    respuesta = cliente.post(
        '/contratos', json=contrato_icl(), headers=headers
    )
    assert respuesta.status_code == HTTPStatus.CREATED
    return respuesta.json()['id']


def monto(dinero: dict[str, str]) -> Decimal:
    return Decimal(dinero['monto'])


def test_sin_token_no_se_puede_registrar_un_contrato(
    cliente: TestClient,
) -> None:
    respuesta = cliente.post('/contratos', json=contrato_icl())

    assert respuesta.status_code == HTTPStatus.UNAUTHORIZED


def test_registra_y_lista_un_contrato(
    cliente: TestClient, headers: dict[str, str]
) -> None:
    contrato_id = crear_contrato(cliente, headers)

    respuesta = cliente.get('/contratos', headers=headers)

    assert respuesta.status_code == HTTPStatus.OK
    contratos = respuesta.json()
    assert [c['id'] for c in contratos] == [contrato_id]
    assert contratos[0]['fecha_fin'] == '2026-01-01'


def test_ajuste_fijo_sin_tasa_es_invalido(
    cliente: TestClient, headers: dict[str, str]
) -> None:
    datos = {**contrato_icl(), 'tipo_ajuste': 'FIJO', 'serie_codigo': None}

    respuesta = cliente.post('/contratos', json=datos, headers=headers)

    assert respuesta.status_code == HTTPStatus.UNPROCESSABLE_ENTITY


def test_calendario_de_ajustes(
    cliente: TestClient, headers: dict[str, str]
) -> None:
    contrato_id = crear_contrato(cliente, headers)

    respuesta = cliente.get(
        f'/contratos/{contrato_id}/calendario', headers=headers
    )

    calendario = respuesta.json()
    assert respuesta.status_code == HTTPStatus.OK
    assert len(calendario) == AJUSTES_EN_UN_ANIO
    assert [a['fecha'] for a in calendario] == [
        '2025-04-01',
        '2025-07-01',
        '2025-10-01',
    ]
    assert all(a['estado'] == 'CALCULADO' for a in calendario)


def test_ajuste_vigente_en_una_fecha(
    cliente: TestClient, headers: dict[str, str]
) -> None:
    contrato_id = crear_contrato(cliente, headers)

    respuesta = cliente.get(
        f'/contratos/{contrato_id}/ajuste',
        params={'fecha': '2025-08-15'},
        headers=headers,
    )

    assert respuesta.status_code == HTTPStatus.OK
    assert monto(respuesta.json()['monto_ajustado']) == Decimal('579850.00')
    assert 'ICL' in respuesta.json()['formula']


def test_verifica_un_ajuste_encadenado_y_lo_guarda(
    cliente: TestClient, headers: dict[str, str]
) -> None:
    contrato_id = crear_contrato(cliente, headers)
    # 538.450 (primer ajuste) × 1,1597 (variación acumulada desde enero)
    informado = {'monto': '624440.47', 'moneda': 'ARS'}

    respuesta = cliente.post(
        f'/contratos/{contrato_id}/verificaciones',
        json={'fecha_ajuste': '2025-07-01', 'monto_informado': informado},
        headers=headers,
    )
    historial = cliente.get(
        f'/contratos/{contrato_id}/verificaciones', headers=headers
    )

    verificacion = respuesta.json()
    assert respuesta.status_code == HTTPStatus.CREATED
    assert verificacion['resultado'] == 'ENCADENADO'
    assert monto(verificacion['esperado']) == Decimal('579850.00')
    assert monto(verificacion['diferencia']) == Decimal('44590.47')
    assert [v['id'] for v in historial.json()] == [verificacion['id']]


def test_un_contrato_ajeno_devuelve_404(
    cliente: TestClient, headers: dict[str, str]
) -> None:
    contrato_id = crear_contrato(cliente, headers)
    otro = registrar(cliente, 'otro@example.com')

    respuesta = cliente.get(f'/contratos/{contrato_id}', headers=otro)

    assert respuesta.status_code == HTTPStatus.NOT_FOUND


def test_cualquiera_puede_ver_la_serie(
    cliente: TestClient, headers: dict[str, str]
) -> None:
    respuesta = cliente.get('/indices/icl/valores')

    assert respuesta.status_code == HTTPStatus.OK
    assert len(respuesta.json()) == MESES_DE_SERIE


def test_solo_un_admin_carga_indices(
    cliente: TestClient, headers: dict[str, str]
) -> None:
    valor = {'fecha': '2027-01-01', 'valor': '200'}
    with Session(get_engine()) as sesion:
        crear_admin(sesion, 'admin@example.com', 'clave-admin-123')
    admin = token_de(cliente, 'admin@example.com', 'clave-admin-123')

    rechazado = cliente.post(
        '/indices/IPC/valores', json=valor, headers=headers
    )
    aceptado = cliente.post('/indices/IPC/valores', json=valor, headers=admin)

    assert rechazado.status_code == HTTPStatus.FORBIDDEN
    assert aceptado.status_code == HTTPStatus.CREATED
    assert aceptado.json()['serie'] == 'IPC'
