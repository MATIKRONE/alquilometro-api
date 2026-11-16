import re
from functools import lru_cache

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from alquilometro_api.core.seguridad import (
    hashear_password,
    verificar_password,
)
from alquilometro_api.core.tokens import crear_token, validar_token
from alquilometro_api.domain.errores import (
    ConflictoDominio,
    NoAutenticado,
    PermisoInsuficiente,
    ValidacionError,
)
from alquilometro_api.domain.rol import Rol
from alquilometro_api.models.usuario import Usuario

LARGO_MINIMO_PASSWORD = 8
LARGO_MAXIMO_NOMBRE = 100
_FORMATO_EMAIL = re.compile(r'[^@\s]+@[^@\s]+\.[^@\s]+')
_ROLES_DE_AUTOREGISTRO = {Rol.BUSCADOR, Rol.INMOBILIARIA}


@lru_cache
def _hash_falso() -> str:
    return hashear_password('hash-para-igualar-tiempos')


def _normalizar_email(email: str) -> str:
    return email.strip().lower()


class ServicioAuth:
    """Registro, login y resolución del usuario de un token."""

    def __init__(self, sesion: Session) -> None:
        self.sesion = sesion

    def registrar(
        self,
        nombre: str,
        email: str,
        password: str,
        rol: Rol = Rol.BUSCADOR,
    ) -> Usuario:
        nombre = nombre.strip()
        email = _normalizar_email(email)
        if not nombre or len(nombre) > LARGO_MAXIMO_NOMBRE:
            msg = (
                f'El nombre debe tener entre 1 y {LARGO_MAXIMO_NOMBRE} letras.'
            )
            raise ValidacionError(msg)
        if not _FORMATO_EMAIL.fullmatch(email):
            msg = 'El email no es válido.'
            raise ValidacionError(msg)
        if len(password) < LARGO_MINIMO_PASSWORD:
            msg = (
                'La contraseña debe tener al menos '
                f'{LARGO_MINIMO_PASSWORD} caracteres.'
            )
            raise ValidacionError(msg)
        if rol not in _ROLES_DE_AUTOREGISTRO:
            msg = 'Ese rol no puede asignarse al registrarse.'
            raise PermisoInsuficiente(msg)
        if self._buscar_por_email(email) is not None:
            msg = 'Ya existe un usuario con ese email.'
            raise ConflictoDominio(msg)

        usuario = Usuario(
            nombre=nombre,
            email=email,
            password_hash=hashear_password(password),
            rol=rol,
        )
        self.sesion.add(usuario)
        try:
            self.sesion.commit()
        except IntegrityError:
            self.sesion.rollback()
            msg = 'Ya existe un usuario con ese email.'
            raise ConflictoDominio(msg) from None
        return usuario

    def autenticar(self, email: str, password: str) -> str:
        """Devuelve un token JWT si las credenciales son correctas."""
        usuario = self._buscar_por_email(_normalizar_email(email))
        # Se verifica siempre contra algun hash: tarda lo mismo exista o no
        # el mail, y el mensaje es identico /no revela q fallo)
        hash_ = usuario.password_hash if usuario else _hash_falso()
        if not verificar_password(password, hash_) or usuario is None:
            msg = 'Email o contraseña incorrectos.'
            raise NoAutenticado(msg)
        return crear_token(usuario.id)

    def usuario_actual(self, token: str) -> Usuario:
        usuario = self.sesion.get(Usuario, validar_token(token))
        if usuario is None:
            msg = 'El usuario del token ya no existe.'
            raise NoAutenticado(msg)
        return usuario

    def _buscar_por_email(self, email: str) -> Usuario | None:
        consulta = select(Usuario).where(Usuario.email == email)
        return self.sesion.scalars(consulta).first()
