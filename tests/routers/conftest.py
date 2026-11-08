import itertools

import pytest

import alquilometro_api.routers.publicaciones as router_pub


@pytest.fixture(autouse=True)
def limpiar_publicaciones() -> None:
    """
    Se ejecuta automáticamente antes de cada test dentro de la carpeta /routers
    Asegura que la "base de datos" en memoria y los IDs arranquen limpios.
    """
    router_pub.publicaciones.clear()
    router_pub.generador_ids = itertools.count(1)
