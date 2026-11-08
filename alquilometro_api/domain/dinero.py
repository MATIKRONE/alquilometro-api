from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation
from functools import total_ordering

from alquilometro_api.domain.errores import MonedaIncompatible, ValidacionError
from alquilometro_api.domain.moneda import Moneda

type Numero = Decimal | int | str


def _a_decimal(valor: object) -> Decimal:
    """Convierte a Decimal sin pasar nunca por float."""
    if isinstance(valor, bool | float):
        msg = (
            f'Se recibió {type(valor).__name__}: usá Decimal, int o str '
            'para no perder precisión en importes.'
        )
        raise TypeError(msg)
    if not isinstance(valor, Decimal | int | str):
        msg = f'No se puede convertir {type(valor).__name__} a Decimal.'
        raise TypeError(msg)
    try:
        decimal = Decimal(valor)
    except InvalidOperation:
        msg = f'"{valor}" no es un número válido.'
        raise ValidacionError(msg) from None
    if not decimal.is_finite():
        msg = 'El valor debe ser un número finito.'
        raise ValidacionError(msg)
    return decimal


@total_ordering
@dataclass(frozen=True, slots=True)
class Dinero:
    """Importe con su moneda (value object, inmutable).

    Reglas:
    - El monto es siempre Decimal, nunca float.
    - No se mezclan monedas: sumar ARS con USD lanza MonedaIncompatible.
    - Las operaciones conservan la precisión completa; el redondeo se
      aplica sólo al llamar a `redondear()`, para no acumular error en
      los cálculos intermedios (ajustes, proyecciones).
    """

    monto: Decimal
    moneda: Moneda

    def __post_init__(self) -> None:
        object.__setattr__(self, 'monto', _a_decimal(self.monto))
        try:
            moneda = Moneda(self.moneda)
        except ValueError:
            msg = f'Moneda no soportada: "{self.moneda}".'
            raise ValidacionError(msg) from None
        object.__setattr__(self, 'moneda', moneda)

    @classmethod
    def cero(cls, moneda: Moneda) -> Dinero:
        return cls(Decimal(0), moneda)

    @classmethod
    def total(cls, montos: Iterable[Dinero], moneda: Moneda) -> Dinero:
        """Suma una colección (vacía da cero) exigiendo una sola moneda."""
        resultado = cls.cero(moneda)
        for monto in montos:
            resultado = resultado.sumar(monto)
        return resultado

    def sumar(self, otro: Dinero) -> Dinero:
        self._exigir_misma_moneda(otro)
        return Dinero(self.monto + otro.monto, self.moneda)

    def restar(self, otro: Dinero) -> Dinero:
        self._exigir_misma_moneda(otro)
        return Dinero(self.monto - otro.monto, self.moneda)

    def multiplicar(self, factor: Numero) -> Dinero:
        """Escala el importe (tasas, razones entre índices, etc.)."""
        return Dinero(self.monto * _a_decimal(factor), self.moneda)

    def porcentaje_de(self, base: Dinero, decimales: int = 2) -> Decimal:
        """Qué porcentaje de `base` representa este importe.

        Ejemplo: $600.000 sobre un ingreso de $1.200.000 -> 50.00
        """
        self._exigir_misma_moneda(base)
        if base.monto == 0:
            msg = 'No se puede calcular un porcentaje sobre una base de cero.'
            raise ValidacionError(msg)
        porcentaje = self.monto / base.monto * 100
        return _cuantizar(porcentaje, decimales)

    def redondear(self) -> Dinero:
        """Aplica la regla de redondeo de la moneda (mitad hacia arriba)."""
        return Dinero(
            _cuantizar(self.monto, self.moneda.decimales), self.moneda
        )

    def __lt__(self, otro: object) -> bool:
        if not isinstance(otro, Dinero):
            return NotImplemented
        self._exigir_misma_moneda(otro)
        return self.monto < otro.monto

    def __str__(self) -> str:
        monto = self.redondear().monto
        return f'{self.moneda} {monto:.{self.moneda.decimales}f}'

    def _exigir_misma_moneda(self, otro: Dinero) -> None:
        if self.moneda != otro.moneda:
            msg = (
                f'No se pueden combinar {self.moneda} y {otro.moneda} '
                'sin una cotización explícita.'
            )
            raise MonedaIncompatible(msg)


def _cuantizar(valor: Decimal, decimales: int) -> Decimal:
    return valor.quantize(
        Decimal(1).scaleb(-decimales), rounding=ROUND_HALF_UP
    )
