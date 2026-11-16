from datetime import timedelta

import jwt
import pytest

from alquilometro_api.core.config import get_config
from alquilometro_api.core.tokens import crear_token, validar_token
from alquilometro_api.domain.errores import NoAutenticado


def test_token_roundtrip_returns_the_user_id() -> None:
    assert validar_token(crear_token(42)) == 42  # noqa: PLR2004


def test_expired_token_is_rejected() -> None:
    token = crear_token(1, vigencia=timedelta(seconds=-1))

    with pytest.raises(NoAutenticado):
        validar_token(token)


def test_token_signed_with_another_key_is_rejected() -> None:
    config = get_config()
    ajeno = jwt.encode(
        {'sub': '1', 'exp': 9999999999},
        'otra-clave-distinta-de-32-bytes-o-mas-xx',
        algorithm=config.jwt_algoritmo,
    )

    with pytest.raises(NoAutenticado):
        validar_token(ajeno)


def test_tampered_token_is_rejected() -> None:
    cabecera, cuerpo, firma = crear_token(1).split('.')

    with pytest.raises(NoAutenticado):
        validar_token(f'{cabecera}.{cuerpo}x.{firma}')


def test_unsigned_token_with_alg_none_is_rejected() -> None:
    sin_firma = jwt.encode({'sub': '1', 'exp': 9999999999}, None, 'none')

    with pytest.raises(NoAutenticado):
        validar_token(sin_firma)


@pytest.mark.parametrize(
    'payload',
    [{'exp': 9999999999}, {'sub': '1'}, {'sub': 'abc', 'exp': 9999999999}],
    ids=['sin-sub', 'sin-exp', 'sub-no-numerico'],
)
def test_token_with_missing_or_invalid_claims_is_rejected(
    payload: dict[str, object],
) -> None:
    config = get_config()
    token = jwt.encode(
        payload, config.jwt_secret_key, algorithm=config.jwt_algoritmo
    )

    with pytest.raises(NoAutenticado):
        validar_token(token)


@pytest.mark.parametrize('basura', ['', 'abc', 'a.b.c'])
def test_garbage_is_rejected(basura: str) -> None:
    with pytest.raises(NoAutenticado):
        validar_token(basura)


def test_expiration_comes_from_settings(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv('JWT_MINUTOS_EXPIRACION', '5')
    config = get_config()
    payload = jwt.decode(
        crear_token(1), config.jwt_secret_key, algorithms=['HS256']
    )

    assert payload['exp'] - payload['iat'] == 5 * 60  # noqa: PLR2004
