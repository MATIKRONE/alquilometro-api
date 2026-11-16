from http import HTTPStatus

import pytest

from alquilometro_api.domain.errores import (
    ConflictoDominio,
    ErrorDominio,
    IndiceNoDisponible,
    MonedaIncompatible,
    NoAutenticado,
    PermisoInsuficiente,
    RecursoNoEncontrado,
    ValidacionError,
)


@pytest.mark.parametrize(
    ('tipo_error', 'codigo_http_esperado'),
    [
        (ValidacionError, HTTPStatus.UNPROCESSABLE_ENTITY),
        (MonedaIncompatible, HTTPStatus.UNPROCESSABLE_ENTITY),
        (RecursoNoEncontrado, HTTPStatus.NOT_FOUND),
        (PermisoInsuficiente, HTTPStatus.FORBIDDEN),
        (ConflictoDominio, HTTPStatus.CONFLICT),
        (IndiceNoDisponible, HTTPStatus.UNPROCESSABLE_ENTITY),
    ],
)
def test_errores_de_dominio_guardan_mensaje_y_codigo_http(
    tipo_error: type[ErrorDominio],
    codigo_http_esperado: HTTPStatus,
) -> None:
    mensaje = 'algo salió mal'

    excepcion = tipo_error(mensaje)

    assert str(excepcion) == mensaje
    assert excepcion.codigo_http == codigo_http_esperado
    assert isinstance(excepcion, ErrorDominio)


def test_no_autenticado_is_a_401() -> None:
    assert NoAutenticado.codigo_http == 401  # noqa: PLR2004
