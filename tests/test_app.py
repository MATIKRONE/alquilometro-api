from http import HTTPStatus

from fastapi.testclient import TestClient


def test_root_returns_ok_and_welcome_message(cliente: TestClient) -> None:
    response = cliente.get('/')

    assert response.status_code == HTTPStatus.OK
    assert response.json() == {'message': 'Bienvenido a Alquilómetro'}
