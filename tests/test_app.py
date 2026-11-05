from http import HTTPStatus

from fastapi.testclient import TestClient

from alquilometro_api.app import app


def test_root_returns_ok_and_welcome_message() -> None:
    client = TestClient(app)

    response = client.get('/')

    assert response.status_code == HTTPStatus.OK
    assert response.json() == {'message': 'Bienvenido a Alquilómetro'}
