from datetime import timedelta
from http import HTTPStatus

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import delete
from sqlalchemy.orm import Session

from alquilometro_api.core.database import get_engine
from alquilometro_api.core.tokens import crear_token
from alquilometro_api.models.usuario import Usuario


def datos_registro() -> dict[str, str]:
    return {
        'nombre': 'Matías',
        'email': 'matias@alquilometro.com',
        'password': 'clave-segura-123',
    }


# --- A8: casos de error --------------------------------------------------

CLAVE = 'clave-segura-123'  # noqa: S105


@pytest.mark.parametrize(
    'email', ['matias@alquilometro.com', 'MATIAS@Alquilometro.com']
)
def test_registro_con_email_repetido_devuelve_409(
    cliente: TestClient, email: str
) -> None:
    cliente.post('/auth/registro', json=datos_registro())

    respuesta = cliente.post(
        '/auth/registro', json={**datos_registro(), 'email': email}
    )

    assert respuesta.status_code == HTTPStatus.CONFLICT


@pytest.mark.parametrize(
    'cambio',
    [
        {'email': 'sin-arroba'},
        {'email': 'a@sin-punto'},
        {'password': 'corta'},
        {'nombre': ''},
        {'nombre': '   '},
    ],
)
def test_registro_con_datos_invalidos_devuelve_422(
    cliente: TestClient, cambio: dict[str, str]
) -> None:
    respuesta = cliente.post(
        '/auth/registro', json={**datos_registro(), **cambio}
    )

    assert respuesta.status_code == HTTPStatus.UNPROCESSABLE_ENTITY


def test_registro_como_admin_devuelve_403(cliente: TestClient) -> None:
    respuesta = cliente.post(
        '/auth/registro', json={**datos_registro(), 'rol': 'ADMIN'}
    )

    assert respuesta.status_code == HTTPStatus.FORBIDDEN


def test_login_con_clave_incorrecta_devuelve_401(cliente: TestClient) -> None:
    cliente.post('/auth/registro', json=datos_registro())

    respuesta = cliente.post(
        '/auth/login',
        json={'email': 'matias@alquilometro.com', 'password': 'otra-clave'},
    )

    assert respuesta.status_code == HTTPStatus.UNAUTHORIZED


def test_login_no_revela_si_el_email_existe(cliente: TestClient) -> None:
    cliente.post('/auth/registro', json=datos_registro())

    clave_mala = cliente.post(
        '/auth/login',
        json={'email': 'matias@alquilometro.com', 'password': 'otra-clave'},
    )
    sin_usuario = cliente.post(
        '/auth/login',
        json={'email': 'nadie@alquilometro.com', 'password': CLAVE},
    )

    assert sin_usuario.status_code == HTTPStatus.UNAUTHORIZED
    assert sin_usuario.json() == clave_mala.json()


def test_login_ignora_mayusculas_del_email(cliente: TestClient) -> None:
    cliente.post('/auth/registro', json=datos_registro())

    respuesta = cliente.post(
        '/auth/login',
        json={'email': 'MATIAS@alquilometro.com', 'password': CLAVE},
    )

    assert respuesta.status_code == HTTPStatus.OK


def test_login_sin_datos_devuelve_422(cliente: TestClient) -> None:
    respuesta = cliente.post('/auth/login', json={})

    assert respuesta.status_code == HTTPStatus.UNPROCESSABLE_ENTITY


@pytest.mark.parametrize(
    'authorization',
    ['Bearer token-falso', 'Bearer ', 'Basic dXNlcjpwYXNz', 'token-suelto'],
)
def test_usuario_me_con_token_invalido_devuelve_401(
    cliente: TestClient, authorization: str
) -> None:
    respuesta = cliente.get(
        '/usuarios/me', headers={'Authorization': authorization}
    )

    assert respuesta.status_code == HTTPStatus.UNAUTHORIZED


def test_usuario_me_con_token_vencido_devuelve_401(
    cliente: TestClient,
) -> None:
    token = crear_token(1, vigencia=timedelta(seconds=-1))

    respuesta = cliente.get(
        '/usuarios/me', headers={'Authorization': f'Bearer {token}'}
    )

    assert respuesta.status_code == HTTPStatus.UNAUTHORIZED
    assert respuesta.json()['detail'] == 'Token inválido o vencido.'


def test_usuario_me_con_token_de_usuario_borrado_devuelve_401(
    cliente: TestClient,
) -> None:
    token = registrar_y_obtener_token(cliente)
    with Session(get_engine()) as sesion:
        sesion.execute(delete(Usuario))
        sesion.commit()

    respuesta = cliente.get(
        '/usuarios/me', headers={'Authorization': f'Bearer {token}'}
    )

    assert respuesta.status_code == HTTPStatus.UNAUTHORIZED


def test_las_respuestas_nunca_exponen_la_clave(cliente: TestClient) -> None:
    registro = cliente.post('/auth/registro', json=datos_registro())
    token = registrar_y_obtener_token(cliente)
    me = cliente.get(
        '/usuarios/me', headers={'Authorization': f'Bearer {token}'}
    )

    for respuesta in (registro, me):
        assert 'password' not in respuesta.text
        assert 'argon2' not in respuesta.text


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


def test_usuario_actualiza_su_ingreso_referencia(
    cliente: TestClient,
) -> None:
    token = registrar_y_obtener_token(cliente)

    respuesta = cliente.put(
        '/usuarios/me/ingreso-referencia',
        json={
            'monto': '1500000',
            'moneda': 'ARS',
        },
        headers={'Authorization': f'Bearer {token}'},
    )

    assert respuesta.status_code == HTTPStatus.OK
    assert respuesta.json()['ingreso_referencia'] == {
        'monto': '1500000.00',
        'moneda': 'ARS',
    }
