from fastapi import FastAPI, status
from fastapi.testclient import TestClient

from alquilometro_api.app import app, manejar_error_dominio
from alquilometro_api.domain.errores import (
    ErrorDominio,
    MonedaIncompatible,
)

app_de_prueba = FastAPI()
app_de_prueba.add_exception_handler(
    ErrorDominio,
    manejar_error_dominio,
)


@app_de_prueba.get('/probar-error')
def lanzar_error_de_moneda() -> None:
    raise MonedaIncompatible('No se puede sumar ARS con USD')


cliente = TestClient(app_de_prueba)


def test_app_registra_el_handler_de_errores() -> None:
    assert app.exception_handlers[ErrorDominio] is manejar_error_dominio


def test_handler_traduce_error_de_dominio_a_respuesta_http() -> None:
    respuesta = cliente.get('/probar-error')

    assert respuesta.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT
    assert respuesta.json() == {
        'detail': 'No se puede sumar ARS con USD',
    }
