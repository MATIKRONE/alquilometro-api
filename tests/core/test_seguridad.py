import pytest

from alquilometro_api.core.seguridad import (
    hashear_password,
    verificar_password,
)
from alquilometro_api.domain.errores import ValidacionError

PASSWORD = 'clave-Segura-123'  # noqa: S105


def test_hash_is_argon2_and_never_contains_the_password() -> None:
    hash_ = hashear_password(PASSWORD)

    assert hash_.startswith('$argon2id$')
    assert PASSWORD not in hash_


def test_same_password_gives_different_hashes_because_of_the_salt() -> None:
    assert hashear_password(PASSWORD) != hashear_password(PASSWORD)


def test_verify_accepts_the_right_password() -> None:
    assert verificar_password(PASSWORD, hashear_password(PASSWORD)) is True


@pytest.mark.parametrize('intento', ['otra-clave', PASSWORD.upper(), ''])
def test_verify_rejects_a_wrong_password(intento: str) -> None:
    assert verificar_password(intento, hashear_password(PASSWORD)) is False


@pytest.mark.parametrize('hash_roto', ['', 'texto-plano', '$argon2id$roto'])
def test_verify_returns_false_for_malformed_hashes(hash_roto: str) -> None:
    assert verificar_password(PASSWORD, hash_roto) is False


def test_hashing_an_empty_password_is_a_validation_error() -> None:
    with pytest.raises(ValidacionError):
        hashear_password('')


def test_unicode_and_long_passwords_are_supported() -> None:
    larga = 'ñandú-🔒-' * 50

    assert verificar_password(larga, hashear_password(larga)) is True
