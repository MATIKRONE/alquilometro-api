from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from alquilometro_api.core.database import get_session
from alquilometro_api.core.dependencias import usuario_actual
from alquilometro_api.models.usuario import Usuario
from alquilometro_api.schemas.auth import (
    IngresoReferenciaEntrada,
    LoginEntrada,
    RegistroEntrada,
    TokenRespuesta,
    UsuarioRespuesta,
)
from alquilometro_api.services.auth import ServicioAuth

router = APIRouter(tags=['autenticación'])


@router.post(
    '/auth/registro',
    response_model=UsuarioRespuesta,
    status_code=status.HTTP_201_CREATED,
)
def registrar(
    datos: RegistroEntrada,
    sesion: Session = Depends(get_session),
) -> Usuario:
    servicio_auth = ServicioAuth(sesion)

    return servicio_auth.registrar(
        nombre=datos.nombre,
        email=datos.email,
        password=datos.password,
        rol=datos.rol,
    )


@router.post('/auth/login', response_model=TokenRespuesta)
def login(
    datos: LoginEntrada,
    sesion: Session = Depends(get_session),
) -> TokenRespuesta:
    servicio_auth = ServicioAuth(sesion)
    token = servicio_auth.autenticar(datos.email, datos.password)

    return TokenRespuesta(access_token=token)


@router.get('/usuarios/me', response_model=UsuarioRespuesta)
def ver_mi_usuario(
    usuario: Usuario = Depends(usuario_actual),
) -> Usuario:
    return usuario


@router.put(
    '/usuarios/me/ingreso-referencia',
    response_model=UsuarioRespuesta,
)
def actualizar_ingreso_referencia(
    datos: IngresoReferenciaEntrada,
    sesion: Session = Depends(get_session),
    usuario: Usuario = Depends(usuario_actual),
) -> Usuario:
    servicio_auth = ServicioAuth(sesion)
    return servicio_auth.actualizar_ingreso_referencia(
        usuario,
        datos.a_dominio(),
    )
