"""Series de índices (ICL, IPC, UVA) que usan los ajustes por índice."""

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from alquilometro_api.core.database import get_session
from alquilometro_api.core.dependencias import usuario_actual
from alquilometro_api.domain.errores import PermisoInsuficiente
from alquilometro_api.domain.rol import Rol
from alquilometro_api.models.indice import ValorIndice
from alquilometro_api.models.usuario import Usuario
from alquilometro_api.schemas.indice import (
    ValorIndiceCrear,
    ValorIndiceRespuesta,
)
from alquilometro_api.services.indices import RepositorioIndicesDB

router = APIRouter(prefix='/indices', tags=['índices'])


@router.get('/{serie}/valores', response_model=list[ValorIndiceRespuesta])
def listar_valores(
    serie: str,
    sesion: Session = Depends(get_session),
) -> list[ValorIndice]:
    return RepositorioIndicesDB(sesion).listar(serie)


@router.post(
    '/{serie}/valores',
    response_model=ValorIndiceRespuesta,
    status_code=status.HTTP_201_CREATED,
)
def cargar_valor(
    serie: str,
    datos: ValorIndiceCrear,
    sesion: Session = Depends(get_session),
    usuario: Usuario = Depends(usuario_actual),
) -> ValorIndice:
    """Carga o corrige el valor de un mes. Solo administradores."""
    if usuario.rol is not Rol.ADMIN:
        msg = 'Solo un administrador puede cargar valores de índices.'
        raise PermisoInsuficiente(msg)
    return RepositorioIndicesDB(sesion).cargar(serie, datos.fecha, datos.valor)
