from typing import Annotated

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from alquilometro_api.core.database import get_session
from alquilometro_api.core.dependencias import usuario_actual
from alquilometro_api.domain.analisis_economico import AnalisisEconomico
from alquilometro_api.domain.desglose_costo import DesgloseCosto
from alquilometro_api.models.publicacion import Publicacion
from alquilometro_api.models.usuario import Usuario
from alquilometro_api.schemas.publicacion import (
    AnalisisEconomicoRespuesta,
    DesgloseCostoRespuesta,
    FiltrosPublicacionesConsulta,
    PublicacionCrear,
    PublicacionRespuesta,
)
from alquilometro_api.services.publicaciones import (
    FiltrosPublicaciones,
    ServicioPublicaciones,
)

router = APIRouter(
    prefix='/publicaciones',
    tags=['publicaciones'],
)


@router.post(
    '',
    response_model=PublicacionRespuesta,
    status_code=status.HTTP_201_CREATED,
)
def crear_publicacion(
    datos: PublicacionCrear,
    sesion: Session = Depends(get_session),
    publicador: Usuario = Depends(usuario_actual),
) -> Publicacion:
    servicio = ServicioPublicaciones(sesion)
    return servicio.crear(datos, publicador)


@router.get('', response_model=list[PublicacionRespuesta])
def listar_publicaciones(
    consulta: Annotated[FiltrosPublicacionesConsulta, Query()],
    sesion: Session = Depends(get_session),
) -> list[Publicacion]:
    filtros = FiltrosPublicaciones(**consulta.model_dump())
    servicio = ServicioPublicaciones(sesion)
    return servicio.listar(filtros)


@router.get(
    '/{publicacion_id}/costo-real',
    response_model=DesgloseCostoRespuesta,
)
def obtener_costo_real(
    publicacion_id: int,
    sesion: Session = Depends(get_session),
) -> DesgloseCosto:
    servicio = ServicioPublicaciones(sesion)
    publicacion = servicio.obtener(publicacion_id)
    return publicacion.calcular_costo_real()


@router.get(
    '/{publicacion_id}/analisis',
    response_model=AnalisisEconomicoRespuesta,
)
def analizar_publicacion(
    publicacion_id: int,
    sesion: Session = Depends(get_session),
    usuario: Usuario = Depends(usuario_actual),
) -> AnalisisEconomico:
    servicio = ServicioPublicaciones(sesion)
    return servicio.analizar_para_usuario(publicacion_id, usuario)
