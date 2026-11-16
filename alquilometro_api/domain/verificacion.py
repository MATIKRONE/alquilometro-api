"""Verificación de un ajuste: ¿lo que me quieren cobrar está bien?

Este es el diferencial del producto. Una calculadora dice cuánto debería
valer el alquiler; acá además se compara contra lo que informó la
inmobiliaria y, si no coincide, se intenta explicar por qué.

El caso que más importa es el encadenamiento: aplicar la variación
acumulada desde el inicio del contrato sobre el alquiler que ya venía
ajustado, en lugar de sobre el monto base. Da un número más alto que el
pactado y es un error frecuente.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from enum import StrEnum

from alquilometro_api.domain.ajuste import (
    MecanismoAjuste,
    ResultadoAjuste,
    sumar_meses,
)
from alquilometro_api.domain.dinero import Dinero


class ResultadoVerificacion(StrEnum):
    CORRECTO = 'CORRECTO'
    ENCADENADO = 'ENCADENADO'
    DIFERENCIA = 'DIFERENCIA'


@dataclass(frozen=True, slots=True)
class Verificacion:
    """Comparación entre el monto informado y el que corresponde."""

    resultado: ResultadoVerificacion
    monto_informado: Dinero
    monto_esperado: Dinero
    diferencia: Dinero
    diferencia_porcentual: Decimal
    explicacion: str
    detalle: ResultadoAjuste


def verificar_ajuste(  # noqa: PLR0913, PLR0917
    mecanismo: MecanismoAjuste,
    monto_base: Dinero,
    fecha_base: date,
    fecha_ajuste: date,
    meses_periodicidad: int,
    monto_informado: Dinero,
) -> Verificacion:
    """Compara el monto informado contra el que surge del contrato.

    Los importes se comparan después de aplicar la misma regla de
    redondeo de la moneda: si coinciden, el ajuste es correcto.
    """
    esperado = mecanismo.ajustar(
        monto_base, fecha_base, fecha_ajuste, meses_periodicidad
    )
    informado = monto_informado.redondear()
    diferencia = informado.restar(esperado.monto_ajustado)
    porcentaje = diferencia.porcentaje_de(esperado.monto_ajustado)

    if diferencia.monto == 0:
        resultado = ResultadoVerificacion.CORRECTO
        explicacion = (
            'El monto coincide con el ajuste que corresponde según el '
            f'contrato: {esperado.formula}.'
        )
    elif informado == _monto_encadenado(
        mecanismo, monto_base, fecha_base, meses_periodicidad, esperado
    ):
        resultado = ResultadoVerificacion.ENCADENADO
        explicacion = (
            'Aplicaron la variación acumulada desde el inicio del contrato '
            'sobre el alquiler que ya venías pagando, en lugar de sobre el '
            f'monto base. Lo correcto es {esperado.monto_ajustado}: te '
            f'están cobrando {diferencia} de más.'
        )
    else:
        resultado = ResultadoVerificacion.DIFERENCIA
        sentido = 'de más' if diferencia.monto > 0 else 'de menos'
        explicacion = (
            f'El monto no coincide con el ajuste del contrato: hay '
            f'{_valor_absoluto(diferencia)} {sentido}. Conviene pedir por '
            'escrito qué índice y qué meses usaron para calcularlo.'
        )

    return Verificacion(
        resultado=resultado,
        monto_informado=informado,
        monto_esperado=esperado.monto_ajustado,
        diferencia=diferencia,
        diferencia_porcentual=porcentaje,
        explicacion=explicacion,
        detalle=esperado,
    )


def _monto_encadenado(
    mecanismo: MecanismoAjuste,
    monto_base: Dinero,
    fecha_base: date,
    meses_periodicidad: int,
    esperado: ResultadoAjuste,
) -> Dinero | None:
    """Lo que daría aplicar el coeficiente acumulado al monto anterior.

    En el primer ajuste no hay monto anterior distinto del base, así que
    el encadenamiento no se puede distinguir de un cálculo correcto.
    """
    if esperado.periodos < 2:  # noqa: PLR2004
        return None
    fecha_anterior = sumar_meses(
        fecha_base, (esperado.periodos - 1) * meses_periodicidad
    )
    anterior = mecanismo.ajustar(
        monto_base, fecha_base, fecha_anterior, meses_periodicidad
    )
    return anterior.monto_ajustado.multiplicar(
        esperado.coeficiente
    ).redondear()


def _valor_absoluto(dinero: Dinero) -> Dinero:
    return Dinero(abs(dinero.monto), dinero.moneda)
