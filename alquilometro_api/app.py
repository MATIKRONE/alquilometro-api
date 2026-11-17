from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

import alquilometro_api.models  # noqa: F401
from alquilometro_api.core.database import crear_tablas
from alquilometro_api.domain.errores import ErrorDominio
from alquilometro_api.routers.auth import router as auth_router
from alquilometro_api.routers.contratos import router as contratos_router
from alquilometro_api.routers.indices import router as indices_router
from alquilometro_api.routers.proyecciones import (
    router as proyecciones_router,
)
from alquilometro_api.routers.publicaciones import (
    router as publicaciones_router,
)


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    crear_tablas()
    yield


app = FastAPI(
    lifespan=lifespan,
    title='Alquilómetro API',
    description=(
        'API para analizar el costo real de alquileres y sus ajustes.'
    ),
)


@app.exception_handler(ErrorDominio)
def manejar_error_dominio(
    _request: Request,
    error: ErrorDominio,
) -> JSONResponse:
    return JSONResponse(
        status_code=error.codigo_http,
        content={'detail': str(error)},
    )


app.include_router(auth_router)
app.include_router(publicaciones_router)
app.include_router(contratos_router)
app.include_router(indices_router)
app.include_router(proyecciones_router)


@app.get('/')
def read_root() -> dict[str, str]:
    return {'message': 'Bienvenido a Alquilómetro'}
