from collections.abc import Callable
from http import HTTPStatus

import pytest
from fastapi.testclient import TestClient

URL = '/usuarios/me/ingreso-referencia'
Autenticar = Callable[..., dict[str, str]]


def test_set_income_in_ars_is_returned_and_visible_in_me(
    cliente: TestClient, autenticar: Autenticar
) -> None:
    cabecera = autenticar()

    respuesta = cliente.put(
        URL, json={'monto': '1200000.50'}, headers=cabecera
    )

    assert respuesta.status_code == HTTPStatus.OK
    esperado = {'monto': '1200000.50', 'moneda': 'ARS'}
    assert respuesta.json()['ingreso_referencia'] == esperado
    me = cliente.get('/usuarios/me', headers=cabecera).json()
    assert me['ingreso_referencia'] == esperado


def test_set_income_in_usd_and_replace_it(
    cliente: TestClient, autenticar: Autenticar
) -> None:
    cabecera = autenticar()
    cliente.put(URL, json={'monto': '1000'}, headers=cabecera)

    respuesta = cliente.put(
        URL, json={'monto': '2500', 'moneda': 'USD'}, headers=cabecera
    )

    assert respuesta.json()['ingreso_referencia'] == {
        'monto': '2500.00',
        'moneda': 'USD',
    }


def test_user_without_income_has_null(
    cliente: TestClient, autenticar: Autenticar
) -> None:
    me = cliente.get('/usuarios/me', headers=autenticar()).json()

    assert me['ingreso_referencia'] is None


def test_delete_income_clears_it(
    cliente: TestClient, autenticar: Autenticar
) -> None:
    cabecera = autenticar()
    cliente.put(URL, json={'monto': '1000'}, headers=cabecera)

    respuesta = cliente.delete(URL, headers=cabecera)

    assert respuesta.status_code == HTTPStatus.OK
    assert respuesta.json()['ingreso_referencia'] is None


@pytest.mark.parametrize(
    'cuerpo',
    [
        {'monto': '0'},
        {'monto': '-5'},
        {'monto': '1000.123'},
        {'monto': '1000', 'moneda': 'EUR'},
        {'monto': 'abc'},
        {},
    ],
    ids=['cero', 'negativo', '3-decimales', 'moneda', 'no-numerico', 'vacio'],
)
def test_invalid_income_is_a_422(
    cliente: TestClient, autenticar: Autenticar, cuerpo: dict[str, str]
) -> None:
    respuesta = cliente.put(URL, json=cuerpo, headers=autenticar())

    assert respuesta.status_code == HTTPStatus.UNPROCESSABLE_ENTITY


def test_income_requires_authentication(cliente: TestClient) -> None:
    put = cliente.put(URL, json={'monto': '1000'})
    borrar = cliente.delete(URL)

    assert put.status_code == HTTPStatus.UNAUTHORIZED
    assert borrar.status_code == HTTPStatus.UNAUTHORIZED


def test_income_belongs_to_each_user(
    cliente: TestClient, autenticar: Autenticar
) -> None:
    ana = autenticar('ana@example.com')
    beto = autenticar('beto@example.com')

    cliente.put(URL, json={'monto': '1000'}, headers=ana)

    assert (
        cliente.get('/usuarios/me', headers=beto).json()['ingreso_referencia']
        is None
    )
