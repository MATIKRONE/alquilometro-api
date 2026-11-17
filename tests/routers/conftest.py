from http import HTTPStatus

import pytest
from fastapi.testclient import TestClient


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
