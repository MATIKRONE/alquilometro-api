"""RQ3: proyección del costo de una publicación a 12 y 24 meses.

Vive en su propio router para no mezclarse con el listado y los filtros
de publicaciones (RQ1).
"""

from decimal import Decimal

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from alquilometro_api.core.database import get_session
from alquilometro_api.core.dependencias import usuario_actual
from alquilometro_api.models.usuario import Usuario
from alquilometro_api.schemas.proyeccion import ProyeccionRespuesta
from alquilometro_api.services.proyecciones import (
    Proyeccion,
    ServicioProyecciones,
)
from alquilometro_api.services.publicaciones import ServicioPublicaciones

router = APIRouter(prefix='/publicaciones', tags=['publicaciones'])


@router.get(
    '/{publicacion_id}/proyeccion',
    response_model=ProyeccionRespuesta,
)
def proyectar_publicacion(
    publicacion_id: int,
    meses_periodicidad: int = Query(
        default=3,
        ge=1,
        le=24,
        description='Cada cuántos meses ajusta el contrato.',
    ),
    tasa_mensual: Decimal | None = Query(
        default=None,
        ge=0,
        description=(
            'Variación mensual del índice en puntos porcentuales. Si no se '
            'indica, se usa el promedio de los últimos 12 meses de la serie.'
        ),
    ),
    sesion: Session = Depends(get_session),
    usuario: Usuario = Depends(usuario_actual),
) -> Proyeccion:
    """Cuánto se pagaría en los meses 12 y 24, y qué parte del ingreso es."""
    publicacion = ServicioPublicaciones(sesion).obtener(publicacion_id)
    return ServicioProyecciones(sesion).proyectar(
        publicacion,
        usuario,
        meses_periodicidad=meses_periodicidad,
        tasa_mensual=tasa_mensual,
    )
