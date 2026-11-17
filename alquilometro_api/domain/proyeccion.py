"""Proyección del costo de un alquiler a los meses 12 y 24 (RQ3).

La proyección no tiene una fórmula propia: arma un escenario de índices
futuros y se lo pasa a la misma estrategia de ajuste que usan los
contratos (`AjusteIndice` o `AjusteFijo`). Así el cálculo proyectado y el
real nunca pueden divergir, y la regla de no encadenar vale en los dos.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from enum import StrEnum

from alquilometro_api.domain.ajuste import (
    IndicesEnMemoria,
    MecanismoAjuste,
    sumar_meses,
)
from alquilometro_api.domain.dinero import Dinero
from alquilometro_api.domain.errores import (
    IndiceNoDisponible,
    ValidacionError,
)

MESES_PROYECTADOS = (12, 24)
MESES_DE_HISTORIA = 12
CENTESIMO = Decimal('0.01')


class OrigenEscenario(StrEnum):
    PROMEDIO_ULTIMOS_12_MESES = 'PROMEDIO_ULTIMOS_12_MESES'
    TASA_INDICADA = 'TASA_INDICADA'


@dataclass(frozen=True, slots=True)
class Escenario:
    """Supuesto de variación mensual del índice para el futuro."""

    tasa_mensual_porcentual: Decimal
    origen: OrigenEscenario


@dataclass(frozen=True, slots=True)
class MesProyectado:
    """Lo que se pagaría en un mes del contrato según el escenario."""

    mes: int
    ajustes_aplicados: int
    alquiler: Dinero
    costo_mensual: Dinero
    porcentaje_ingreso: Decimal | None
    formula: str


def escenario_desde_historia(valores: Iterable[Decimal]) -> Escenario:
    """Variación mensual promedio (geométrica) de los últimos 12 meses."""
    serie = list(valores)
    if len(serie) <= MESES_DE_HISTORIA:
        msg = (
            f'Hacen falta {MESES_DE_HISTORIA + 1} meses de la serie para '
            'estimar la variación: indicá una tasa mensual.'
        )
        raise IndiceNoDisponible(msg)
    razon = serie[-1] / serie[-1 - MESES_DE_HISTORIA]
    tasa = (razon ** (Decimal(1) / MESES_DE_HISTORIA) - 1) * 100
    return Escenario(
        tasa.quantize(CENTESIMO), OrigenEscenario.PROMEDIO_ULTIMOS_12_MESES
    )


def escenario_indicado(tasa_mensual_porcentual: Decimal) -> Escenario:
    if tasa_mensual_porcentual < 0:
        msg = 'La tasa mensual del escenario no puede ser negativa.'
        raise ValidacionError(msg)
    return Escenario(tasa_mensual_porcentual, OrigenEscenario.TASA_INDICADA)


def indices_proyectados(
    serie: str,
    fecha_referencia: date,
    valor_referencia: Decimal,
    escenario: Escenario,
) -> IndicesEnMemoria:
    """Valores futuros de la serie si se cumple el escenario."""
    factor = 1 + escenario.tasa_mensual_porcentual / 100
    indices = IndicesEnMemoria()
    for mes in range(max(MESES_PROYECTADOS) + 1):
        indices.cargar(
            serie,
            sumar_meses(fecha_referencia, mes),
            valor_referencia * factor**mes,
        )
    return indices


def proyectar(  # noqa: PLR0913, PLR0917
    mecanismo: MecanismoAjuste,
    alquiler_inicial: Dinero,
    otros_costos: Dinero,
    fecha_inicio: date,
    meses_periodicidad: int,
    ingreso: Dinero | None,
) -> list[MesProyectado]:
    """Alquiler y costo mensual en los meses 12 y 24 del contrato.

    El mes N es el N-ésimo que se paga: ya pasaron N - 1 meses desde el
    inicio, y se aplicaron los ajustes vencidos hasta ese momento.
    """
    proyectados = []
    for mes in MESES_PROYECTADOS:
        transcurridos = mes - 1
        if transcurridos < meses_periodicidad:
            alquiler = alquiler_inicial.redondear()
            ajustes = 0
            formula = 'Todavía no corresponde ningún ajuste.'
        else:
            # El índice se toma del mes en que vence el último período, no
            # del mes que se está pagando.
            vencido = transcurridos // meses_periodicidad * meses_periodicidad
            resultado = mecanismo.ajustar(
                alquiler_inicial,
                fecha_inicio,
                sumar_meses(fecha_inicio, vencido),
                meses_periodicidad,
            )
            alquiler = resultado.monto_ajustado
            ajustes = resultado.periodos
            formula = resultado.formula
        costo = alquiler.sumar(otros_costos)
        proyectados.append(
            MesProyectado(
                mes=mes,
                ajustes_aplicados=ajustes,
                alquiler=alquiler,
                costo_mensual=costo,
                porcentaje_ingreso=_porcentaje(costo, ingreso),
                formula=formula,
            )
        )
    return proyectados


def _porcentaje(costo: Dinero, ingreso: Dinero | None) -> Decimal | None:
    """Solo si la moneda es comparable: no se mezclan pesos y dólares."""
    if ingreso is None or ingreso.moneda != costo.moneda:
        return None
    return costo.porcentaje_de(ingreso)
