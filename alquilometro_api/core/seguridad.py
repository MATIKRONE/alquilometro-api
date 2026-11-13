# largo minimo de contraseña no esta aca hasta el schema registro A3/A6
from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError

from alquilometro_api.domain.errores import ValidacionError

# ARgon2id con los parametros recomendados por defecto
# La sal es aleatoria y viaja dentro del propio hash
_hasher = PasswordHasher()


def hashear_password(password: str) -> str:
    if not password:
        msg = 'La contraseña no puede estar vacía.'
        raise ValidacionError(msg)
    return _hasher.hash(password)


def verificar_password(password: str, password_hash: str) -> bool:
    """True si coincide, False si no coincide el o el hash es inválido"""
    try:
        return _hasher.verify(password_hash, password)
    except (VerificationError, InvalidHashError):
        return False
