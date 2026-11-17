from http import HTTPStatus

from fastapi.testclient import TestClient


def datos_registro() -> dict[str, str]:
    return {
        'nombre': 'Matías',
        'email': 'matias@alquilometro.com',
        'password': 'clave-segura-123',
    }


def registrar_y_obtener_token(cliente: TestClient) -> str:
    cliente.post('/auth/registro', json=datos_registro())

    respuesta = cliente.post(
        '/auth/login',
        json={
            'email': 'matias@alquilometro.com',
            'password': 'clave-segura-123',
        },
    )

    return respuesta.json()['access_token']


def test_registro_devuelve_usuario_sin_password(
    cliente: TestClient,
) -> None:
    respuesta = cliente.post('/auth/registro', json=datos_registro())

    assert respuesta.status_code == HTTPStatus.CREATED

    usuario = respuesta.json()
    assert usuario['nombre'] == 'Matías'
    assert usuario['email'] == 'matias@alquilometro.com'
    assert usuario['rol'] == 'BUSCADOR'
    assert 'password_hash' not in usuario


def test_login_devuelve_un_token(cliente: TestClient) -> None:
    cliente.post('/auth/registro', json=datos_registro())

    respuesta = cliente.post(
        '/auth/login',
        json={
            'email': 'matias@alquilometro.com',
            'password': 'clave-segura-123',
        },
    )

    assert respuesta.status_code == HTTPStatus.OK
    assert respuesta.json()['token_type'] == 'bearer'
    assert respuesta.json()['access_token']


def test_usuario_me_devuelve_el_usuario_del_token(
    cliente: TestClient,
) -> None:
    token = registrar_y_obtener_token(cliente)

    respuesta = cliente.get(
        '/usuarios/me',
        headers={'Authorization': f'Bearer {token}'},
    )

    assert respuesta.status_code == HTTPStatus.OK
    assert respuesta.json()['email'] == 'matias@alquilometro.com'


def test_usuario_me_sin_token_devuelve_401(
    cliente: TestClient,
) -> None:
    respuesta = cliente.get('/usuarios/me')

    assert respuesta.status_code == HTTPStatus.UNAUTHORIZED
    assert respuesta.json()['detail'] == 'Se requiere un token de acceso.'
