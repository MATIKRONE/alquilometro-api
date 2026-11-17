from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from alquilometro_api.domain.rol import Rol


class RegistroEntrada(BaseModel):
    """Datos que recibe POST /auth/registro."""

    nombre: str = Field(min_length=1, max_length=100)
    email: str = Field(min_length=3, max_length=255)
    password: str = Field(min_length=8)
    rol: Rol = Rol.BUSCADOR


class LoginEntrada(BaseModel):
    """Datos que recibe POST /auth/login"""

    email: str = Field(min_length=3, max_length=255)
    password: str = Field(min_length=1)


class TokenRespuesta(BaseModel):
    """Token que se entrega después de un login correcto."""

    access_token: str
    token_type: Literal['bearer'] = 'bearer'


class UsuarioRespuesta(BaseModel):
    """Datos públicos de un usuario: nunca incluye su contraseña."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    nombre: str
    email: str
    rol: Rol
