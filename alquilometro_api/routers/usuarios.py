from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from alquilometro_api.core.database import get_session
from alquilometro_api.core.dependencias import usuario_actual
from alquilometro_api.domain.dinero import Dinero
from alquilometro_api.models.usuario import Usuario
from alquilometro_api.schemas.auth import IngresoEntrada, UsuarioRespuesta
from alquilometro_api.services.usuarios import ServicioUsuarios

router = APIRouter(prefix='/usuarios/me', tags=['usuarios'])


@router.put('/ingreso-referencia', response_model=UsuarioRespuesta)
def actualizar_ingreso_referencia(
    datos: IngresoEntrada,
    usuario: Usuario = Depends(usuario_actual),
    sesion: Session = Depends(get_session),
) -> Usuario:
    ingreso = Dinero(datos.monto, datos.moneda)
    return ServicioUsuarios(sesion).actualizar_ingreso_referencia(
        usuario, ingreso
    )


@router.delete('/ingreso-referencia', response_model=UsuarioRespuesta)
def borrar_ingreso_referencia(
    usuario: Usuario = Depends(usuario_actual),
    sesion: Session = Depends(get_session),
) -> Usuario:
    return ServicioUsuarios(sesion).actualizar_ingreso_referencia(
        usuario, None
    )
