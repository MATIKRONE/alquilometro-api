from decimal import Decimal

import pytest

from alquilometro_api.domain.desglose_costo import CostoEntrada
from alquilometro_api.domain.dinero import Dinero
from alquilometro_api.domain.errores import MonedaIncompatible
from alquilometro_api.domain.moneda import Moneda


def ars(monto: int) -> Dinero:
    return Dinero(Decimal(monto), Moneda.ARS)


def test_total_sums_every_informed_component() -> None:
    entrada = CostoEntrada(
        primer_mes=ars(650000),
        deposito=ars(650000),
        comision=ars(650000),
        seguro_caucion=ars(180000),
        otros_gastos=ars(50000),
    )

    assert entrada.total == ars(2180000)
    assert list(entrada.componentes_informados) == [
        'primer_mes',
        'deposito',
        'comision',
        'seguro_caucion',
        'otros_gastos',
    ]
    assert entrada.faltantes == []


def test_only_informed_concepts_are_added_and_the_rest_are_missing() -> None:
    entrada = CostoEntrada(primer_mes=ars(650000), deposito=ars(650000))

    assert entrada.total == ars(1300000)
    assert entrada.componentes_informados == {
        'primer_mes': ars(650000),
        'deposito': ars(650000),
    }
    assert entrada.faltantes == ['comision', 'seguro_caucion']


def test_other_expenses_are_optional_and_never_reported_missing() -> None:
    entrada = CostoEntrada(primer_mes=ars(1))

    assert 'otros_gastos' not in entrada.faltantes


def test_zero_is_informed_not_missing() -> None:
    entrada = CostoEntrada(primer_mes=ars(650000), comision=ars(0))

    assert 'comision' not in entrada.faltantes
    assert entrada.total == ars(650000)


def test_mixing_currencies_is_rejected() -> None:
    entrada = CostoEntrada(
        primer_mes=ars(650000),
        deposito=Dinero(Decimal(500), Moneda.USD),
    )

    with pytest.raises(MonedaIncompatible):
        _ = entrada.total
