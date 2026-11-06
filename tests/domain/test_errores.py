from http import HTTPStatus

import pytest

from alquilometro_api.domain.errores import (
    ErrorDominio,
    MonedaIncompatible,
    ValidacionError,
)


def test_error_dominio_base_is_abstract() -> None:
    with pytest.raises(TypeError):
        ErrorDominio('no se puede instanciar')


@pytest.mark.parametrize(
    ('error', 'codigo'),
    [
        (ValidacionError, HTTPStatus.UNPROCESSABLE_ENTITY),
        (MonedaIncompatible, HTTPStatus.UNPROCESSABLE_ENTITY),
    ],
)
def test_domain_errors_carry_message_and_http_code(
    error: type[ErrorDominio], codigo: HTTPStatus
) -> None:
    excepcion = error('algo salió mal')

    assert excepcion.mensaje == 'algo salió mal'
    assert excepcion.codigo_http == codigo
    assert isinstance(excepcion, ErrorDominio)
