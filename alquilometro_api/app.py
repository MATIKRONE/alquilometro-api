from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from alquilometro_api.domain.errores import ErrorDominio
from alquilometro_api.routers.publicaciones import (
    router as publicaciones_router,
)

app = FastAPI(
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


app.include_router(publicaciones_router)


@app.get('/')
def read_root() -> dict[str, str]:
    return {'message': 'Bienvenido a Alquilómetro'}
