from fastapi import APIRouter, status

from alquilometro_api.schemas.publicacion import (
    PublicacionCrear,
    PublicacionRespuesta,
)

router = APIRouter(
    prefix='/publicaciones',
    tags=['publicaciones'],
)

# Por ahora guardamos los avisos en memoria.
# Más adelante SQLAlchemy reemplazará esta lista.
publicaciones: list[PublicacionRespuesta] = []


@router.post(
    '',
    response_model=PublicacionRespuesta,
    status_code=status.HTTP_201_CREATED,
)
def crear_publicacion(datos: PublicacionCrear) -> PublicacionRespuesta:
    publicacion = PublicacionRespuesta(
        id=len(publicaciones) + 1,
        **datos.model_dump(),
    )
    publicaciones.append(publicacion)
    return publicacion


@router.get('', response_model=list[PublicacionRespuesta])
def listar_publicaciones() -> list[PublicacionRespuesta]:
    return publicaciones
