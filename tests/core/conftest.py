from collections.abc import Iterator

import pytest

from alquilometro_api.core.config import get_config
from alquilometro_api.core.database import get_engine


def cerrar_engine_cacheado() -> None:
    """Cierra el motor guardado en caché, si algún test llegó a crearlo."""
    if get_engine.cache_info().currsize:
        get_engine().dispose()

    get_engine.cache_clear()


@pytest.fixture(autouse=True)
def limpiar_caches() -> Iterator[None]:
    cerrar_engine_cacheado()
    get_config.cache_clear()

    yield

    cerrar_engine_cacheado()
    get_config.cache_clear()
