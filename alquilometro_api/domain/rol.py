from enum import StrEnum


class Rol(StrEnum):
    """Perfil de un usuario dentro de una plataforma"""

    BUSCADOR = 'BUSCADOR'
    INMOBILIARIA = 'INMOBILIARIA'
    ADMIN = 'ADMIN'
