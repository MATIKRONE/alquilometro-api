"""Errores de dominio.

Cada error lleva el código HTTP con el que la API lo traduce (ver el
diagrama de clases, sección "Excepciones de dominio"). El handler de
FastAPI que hace esa traducción es la tarea F7.
"""

from http import HTTPStatus


class ErrorDominio(Exception):
    """Base abstracta de los errores de negocio de la API."""

    codigo_http: int = HTTPStatus.INTERNAL_SERVER_ERROR

    def __init__(self, mensaje: str) -> None:
        if type(self) is ErrorDominio:
            msg = 'ErrorDominio es abstracta: usá una subclase.'
            raise TypeError(msg)
        super().__init__(mensaje)
        self.mensaje = mensaje


class ValidacionError(ErrorDominio):
    """Datos de entrada inválidos (rangos, criterios, tasas, etc.)."""

    codigo_http = HTTPStatus.UNPROCESSABLE_ENTITY


class MonedaIncompatible(ErrorDominio):
    """Se intentó mezclar ARS y USD sin una cotización explícita."""

    codigo_http = HTTPStatus.UNPROCESSABLE_ENTITY
