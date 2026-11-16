"Errores propios de las reglas de negocio de Alquilómetro."

from http import HTTPStatus


class ErrorDominio(Exception):
    """Clase base para los errores del negocio."""

    codigo_http = HTTPStatus.INTERNAL_SERVER_ERROR


class ValidacionError(ErrorDominio):
    """Una regla de negocio no se cumple."""

    codigo_http = HTTPStatus.UNPROCESSABLE_ENTITY


class MonedaIncompatible(ErrorDominio):
    """No se pueden operar montos de monedas diferentes."""

    codigo_http = HTTPStatus.UNPROCESSABLE_ENTITY


class RecursoNoEncontrado(ErrorDominio):
    """El recurso solicitado no existe."""

    codigo_http = HTTPStatus.NOT_FOUND


class PermisoInsuficiente(ErrorDominio):
    """El usuario no tiene permiso para realizar la acción."""

    codigo_http = HTTPStatus.FORBIDDEN


class ConflictoDominio(ErrorDominio):
    """La operación entra en conflicto con el estado actual."""

    codigo_http = HTTPStatus.CONFLICT


class IndiceNoDisponible(ErrorDominio):
    """No existen datos del índice para realizar el cálculo."""

    codigo_http = HTTPStatus.UNPROCESSABLE_ENTITY


class NoAutenticado(ErrorDominio):
    """Credenciales o token inválidos, o token vencido."""

    codigo_http = HTTPStatus.UNAUTHORIZED
