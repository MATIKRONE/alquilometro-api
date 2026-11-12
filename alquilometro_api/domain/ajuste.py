"""Mecanismos de ajuste de un alquiler (patrón Strategy).

Por qué hace falta el patrón acá
--------------------------------
El DNU 70/2023 dejó el índice de ajuste a libre elección de las partes:
un contrato ajusta por un porcentaje fijo pactado y otro por una serie
publicada (ICL, IPC, UVA, Casa Propia). Las dos responden a la misma
pregunta, "cuánto pasa a valer este alquiler", pero con fórmulas
distintas.

Sin Strategy esto termina siendo un `if tipo == ...` dentro del servicio
de contratos, imposible de testear por separado. Con Strategy cada forma
de ajustar es una clase con la misma interfaz, y sumar un mecanismo
nuevo no toca el código que ya funciona.

La regla de oro del módulo
--------------------------
El ajuste por índice se calcula SIEMPRE contra el monto base:

    monto_base × (índice del mes de ajuste ÷ índice del mes de inicio)

y nunca encadenando un ajuste sobre el monto ya ajustado. El
encadenamiento es un error frecuente que termina cobrándole de más al
inquilino: da un número más alto que el pactado.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from enum import StrEnum
from typing import ClassVar, Protocol

from alquilometro_api.domain.dinero import Dinero, Numero
from alquilometro_api.domain.errores import (
    ConflictoDominio,
    IndiceNoDisponible,
    ValidacionError,
)

TASA_MAXIMA = Decimal(1000)


class TipoAjuste(StrEnum):
    """Mecanismos de ajuste que el sistema sabe calcular."""

    FIJO = 'FIJO'
    INDICE = 'INDICE'


@dataclass(frozen=True, slots=True)
class ResultadoAjuste:
    """Un ajuste calculado, con todo lo necesario para auditarlo."""

    monto_base: Dinero
    monto_ajustado: Dinero
    coeficiente: Decimal
    periodos: int
    formula: str


class RepositorioIndices(Protocol):
    """Fuente de valores de una serie de índices.

    Es un Protocol y no una clase concreta para que los tests puedan
    pasar un diccionario en memoria y no necesiten base de datos.
    """

    def valor(self, serie: str, momento: date) -> Decimal | None: ...


class IndicesEnMemoria:
    """Repositorio de índices sin base de datos (tests y semillas)."""

    def __init__(self) -> None:
        self._valores: dict[tuple[str, date], Decimal] = {}

    def cargar(self, serie: str, momento: date, valor: Numero) -> None:
        clave = (_normalizar_serie(serie), _primer_dia(momento))
        self._valores[clave] = _a_decimal(valor)

    def valor(self, serie: str, momento: date) -> Decimal | None:
        clave = (_normalizar_serie(serie), _primer_dia(momento))
        return self._valores.get(clave)


class MecanismoAjuste(ABC):
    """Interfaz común de las estrategias de ajuste."""

    tipo: ClassVar[TipoAjuste]

    @abstractmethod
    def _coeficiente(
        self,
        fecha_base: date,
        fecha_ajuste: date,
        periodos: int,
    ) -> tuple[Decimal, str]:
        """Devuelve el coeficiente y la fórmula legible que lo explica."""

    def ajustar(
        self,
        monto_base: Dinero,
        fecha_base: date,
        fecha_ajuste: date,
        meses_periodicidad: int,
    ) -> ResultadoAjuste:
        """Calcula cuánto pasa a valer el alquiler en `fecha_ajuste`."""
        if meses_periodicidad <= 0:
            msg = 'La periodicidad debe ser de al menos un mes.'
            raise ValidacionError(msg)
        if fecha_ajuste < fecha_base:
            msg = 'La fecha de ajuste es anterior al inicio del contrato.'
            raise ValidacionError(msg)

        transcurridos = _meses_entre(fecha_base, fecha_ajuste)
        periodos = transcurridos // meses_periodicidad
        if periodos < 1:
            msg = (
                f'Todavía no corresponde ajustar: pasaron {transcurridos} '
                f'meses y el contrato ajusta cada {meses_periodicidad}.'
            )
            raise ConflictoDominio(msg)

        coeficiente, formula = self._coeficiente(
            fecha_base, fecha_ajuste, periodos
        )
        return ResultadoAjuste(
            monto_base=monto_base,
            monto_ajustado=monto_base.multiplicar(coeficiente).redondear(),
            coeficiente=coeficiente,
            periodos=periodos,
            formula=formula,
        )


class AjusteFijo(MecanismoAjuste):
    """Ajuste de un porcentaje pactado por período.

    Acá SÍ se capitaliza período a período, porque lo pactado es "sube
    X% cada trimestre". En el ajuste por índice no se capitaliza, porque
    lo pactado es una proporción contra el valor de inicio. Confundir
    los dos casos es justamente el error de encadenamiento.
    """

    tipo = TipoAjuste.FIJO

    def __init__(self, tasa_porcentual: Numero) -> None:
        tasa = _a_decimal(tasa_porcentual)
        if tasa < 0 or tasa > TASA_MAXIMA:
            msg = f'La tasa pactada debe estar entre 0 y {TASA_MAXIMA}.'
            raise ValidacionError(msg)
        self.tasa_porcentual = tasa

    def _coeficiente(
        self,
        fecha_base: date,
        fecha_ajuste: date,
        periodos: int,
    ) -> tuple[Decimal, str]:
        factor = (1 + self.tasa_porcentual / 100) ** periodos
        formula = (
            f'monto_base × (1 + {self.tasa_porcentual}%)^{periodos} períodos'
        )
        return factor, formula


class AjusteIndice(MecanismoAjuste):
    """Ajuste por una serie publicada (ICL, IPC, UVA, Casa Propia).

    Todas las series comparten la fórmula; lo único que cambia es de
    dónde se leen los valores. Por eso es una sola clase parametrizada
    por el código de la serie y no una subclase por índice.
    """

    tipo = TipoAjuste.INDICE

    def __init__(self, serie: str, repositorio: RepositorioIndices) -> None:
        if not serie or not serie.strip():
            msg = 'El ajuste por índice necesita el código de la serie.'
            raise ValidacionError(msg)
        self.serie = _normalizar_serie(serie)
        self.repositorio = repositorio

    def _coeficiente(
        self,
        fecha_base: date,
        fecha_ajuste: date,
        periodos: int,
    ) -> tuple[Decimal, str]:
        valor_base = self._valor_en(fecha_base)
        valor_actual = self._valor_en(fecha_ajuste)
        if valor_base == 0:
            msg = (
                f'El valor base de {self.serie} es cero: no se puede '
                'dividir por él.'
            )
            raise IndiceNoDisponible(msg)

        formula = (
            f'monto_base × ({self.serie} {fecha_ajuste.isoformat()} ÷ '
            f'{self.serie} {fecha_base.isoformat()})'
        )
        return valor_actual / valor_base, formula

    def _valor_en(self, momento: date) -> Decimal:
        valor = self.repositorio.valor(self.serie, momento)
        if valor is None:
            msg = (
                f'No tenemos el valor de {self.serie} para '
                f'{momento.isoformat()}.'
            )
            raise IndiceNoDisponible(msg)
        return valor


class FabricaMecanismoAjuste:
    """Simple Factory: del dato guardado al objeto de dominio.

    Es el puente entre la persistencia y el dominio: la publicación y el
    contrato guardan un texto ("FIJO", "INDICE") y acá se traduce a la
    estrategia concreta. Sumar un mecanismo nuevo es una clase más y una
    rama acá; ningún servicio cambia.
    """

    @staticmethod
    def crear(
        tipo: str,
        *,
        tasa_porcentual: Numero | None = None,
        serie: str | None = None,
        repositorio: RepositorioIndices | None = None,
    ) -> MecanismoAjuste:
        try:
            tipo_ajuste = TipoAjuste(tipo.strip().upper())
        except ValueError:
            disponibles = ', '.join(t.value for t in TipoAjuste)
            msg = (
                f'Tipo de ajuste desconocido: "{tipo}". '
                f'Disponibles: {disponibles}.'
            )
            raise ValidacionError(msg) from None

        if tipo_ajuste is TipoAjuste.FIJO:
            if tasa_porcentual is None:
                msg = 'Un ajuste FIJO necesita la tasa pactada.'
                raise ValidacionError(msg)
            return AjusteFijo(tasa_porcentual)

        if serie is None or repositorio is None:
            msg = (
                'Un ajuste por índice necesita el código de la serie y '
                'una fuente de valores.'
            )
            raise ValidacionError(msg)
        return AjusteIndice(serie, repositorio)


def _normalizar_serie(serie: str) -> str:
    return serie.strip().upper()


def _primer_dia(momento: date) -> date:
    """Los índices son mensuales: toda fecha cae al 1 de su mes."""
    return date(momento.year, momento.month, 1)


def _meses_entre(desde: date, hasta: date) -> int:
    """Meses completos transcurridos entre dos fechas."""
    meses = (hasta.year - desde.year) * 12 + (hasta.month - desde.month)
    if hasta.day < desde.day:
        meses -= 1
    return meses


def _a_decimal(valor: Numero) -> Decimal:
    """Convierte a Decimal sin pasar nunca por float."""
    if isinstance(valor, bool | float):
        msg = (
            f'Se recibió {type(valor).__name__}: usá Decimal, int o str '
            'para no perder precisión.'
        )
        raise TypeError(msg)
    return Decimal(valor)
