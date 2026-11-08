from fastapi import FastAPI

from alquilometro_api.routers.publicaciones import (
    router as publicaciones_router,
)

app = FastAPI(
    title='Alquilómetro API',
    description=(
        'API para analizar el costo real de alquileres y sus ajustes.'
    ),
)

app.include_router(publicaciones_router)


@app.get('/')
def read_root() -> dict[str, str]:
    return {'message': 'Bienvenido a Alquilómetro'}
