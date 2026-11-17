from collections.abc import Callable
from http import HTTPStatus

import pytest
from fastapi.testclient import TestClient

CLAVE = 'clave-segura-123'  # noqa: S105


@pytest.fixture
def autenticar(cliente: TestClient) -> Callable[..., dict[str, str]]:
    """Regustra un usuario, inicia sesion y devuelve su cabecera Bearer."""

    def _autenticar(email: str = 'ana@example.com') -> dict[str, str]:
        cliente.post(
            '/auth/registro',
            json={'nombre': 'Ana', 'email': email, 'password': CLAVE},
        )
        respuesta = cliente.post(
            '/auth/login', json={'email': email, 'password': CLAVE}
        )
        return {'Authorization': f'Bearer {respuesta.json()["access_token"]}'}

    return _autenticar


@pytest.fixture
def headers_inmobiliaria(
    cliente: TestClient,
) -> dict[str, str]:
    """Registra una inmobiliaria y devuelve su token para los tests."""

    registro = cliente.post(
        '/auth/registro',
        json={
            'nombre': 'Inmobiliaria de prueba',
            'email': 'inmobiliaria@example.com',
            'password': 'clave-segura-123',
            'rol': 'INMOBILIARIA',
        },
    )
    assert registro.status_code == HTTPStatus.CREATED

    login = cliente.post(
        '/auth/login',
        json={
            'email': 'inmobiliaria@example.com',
            'password': 'clave-segura-123',
        },
    )
    assert login.status_code == HTTPStatus.OK

    token = login.json()['access_token']
    return {'Authorization': f'Bearer {token}'}
