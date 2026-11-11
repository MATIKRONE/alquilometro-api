from collections.abc import Iterator

import pytest

from alquilometro_api.core.config import get_config
from alquilometro_api.core.database import get_engine


@pytest.fixture(autouse=True)
def limpiar_caches() -> Iterator[None]:
    get_config.cache_clear()
    get_engine.cache_clear()
    yield
    get_config.cache_clear()
    get_engine.cache_clear()
