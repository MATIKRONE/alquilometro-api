from dataclasses import FrozenInstanceError
from decimal import Decimal

import pytest

from alquilometro_api.domain.dinero import Dinero
from alquilometro_api.domain.errores import MonedaIncompatible, ValidacionError
from alquilometro_api.domain.moneda import Moneda


def ars(monto: str) -> Dinero:
    return Dinero(Decimal(monto), Moneda.ARS)


def usd(monto: str) -> Dinero:
    return Dinero(Decimal(monto), Moneda.USD)


# --- construcción ---------------------------------------------------------


@pytest.mark.parametrize('valor', ['600000', 600000, Decimal(600000)])
def test_amount_is_stored_as_decimal(valor: str | int | Decimal) -> None:
    dinero = Dinero(valor, Moneda.ARS)

    assert dinero.monto == Decimal(600000)
    assert isinstance(dinero.monto, Decimal)


@pytest.mark.parametrize('valor', [0.1, True])
def test_float_amounts_are_rejected(valor: object) -> None:
    with pytest.raises(TypeError):
        Dinero(valor, Moneda.ARS)  # type: ignore[arg-type]


@pytest.mark.parametrize('valor', ['abc', '', 'NaN', 'Infinity'])
def test_non_numeric_or_non_finite_amounts_are_validation_errors(
    valor: str,
) -> None:
    with pytest.raises(ValidacionError):
        Dinero(valor, Moneda.ARS)  # type: ignore[arg-type]


def test_unknown_currency_is_a_validation_error() -> None:
    with pytest.raises(ValidacionError):
        Dinero(Decimal(1), 'EUR')  # type: ignore[arg-type]


def test_currency_code_string_is_converted_to_enum() -> None:
    assert Dinero(Decimal(1), 'USD').moneda is Moneda.USD  # type: ignore[arg-type]


def test_dinero_is_immutable() -> None:
    dinero = ars('100')

    with pytest.raises(FrozenInstanceError):
        dinero.monto = Decimal(200)  # type: ignore[misc]


def test_equal_amounts_are_equal_and_hashable() -> None:
    assert ars('100.00') == ars('100')
    assert hash(ars('100.00')) == hash(ars('100'))
    assert ars('100') != usd('100')


# --- sumar / restar / total ----------------------------------------------


def test_sumar_adds_amounts_of_the_same_currency() -> None:
    alquiler = ars('600000')
    expensas = ars('85000.50')

    assert alquiler.sumar(expensas) == ars('685000.50')


def test_sumar_mixing_currencies_raises_moneda_incompatible() -> None:
    with pytest.raises(MonedaIncompatible):
        ars('100').sumar(usd('100'))


def test_restar_gives_the_difference() -> None:
    assert ars('700000').restar(ars('650000')) == ars('50000')


def test_restar_can_be_negative_for_adjustment_differences() -> None:
    assert ars('650000').restar(ars('700000')) == ars('-50000')


def test_total_sums_a_collection_and_empty_gives_zero() -> None:
    componentes = [ars('600000'), ars('85000'), ars('12000')]

    assert Dinero.total(componentes, Moneda.ARS) == ars('697000')
    assert Dinero.total([], Moneda.ARS) == ars('0')


def test_total_with_a_foreign_currency_raises() -> None:
    with pytest.raises(MonedaIncompatible):
        Dinero.total([ars('1'), usd('1')], Moneda.ARS)


# --- multiplicar ----------------------------------------------------------


def test_multiplicar_scales_the_amount() -> None:
    assert ars('1000').multiplicar('1.5') == ars('1500')
    assert ars('1000').multiplicar(2) == ars('2000')


def test_multiplicar_rejects_float_factors() -> None:
    with pytest.raises(TypeError):
        ars('1000').multiplicar(1.5)  # type: ignore[arg-type]


def test_index_adjustment_formula_from_base_amount() -> None:
    # monto base x indice del periodo / indice base
    base = ars('600000')
    indice_base = Decimal(100)
    indice_periodo = Decimal(130)

    ajustado = base.multiplicar(indice_periodo / indice_base)

    assert ajustado == ars('780000')


def test_fixed_adjustment_compounds_the_rate() -> None:
    # monto base x (1 + tasa) ** ajustes aplicados
    base = ars('100000')

    ajustado = base.multiplicar((1 + Decimal('0.10')) ** 2)

    assert ajustado == ars('121000')


# --- porcentaje_de --------------------------------------------------------


def test_porcentaje_de_is_the_share_over_the_base() -> None:
    assert ars('600000').porcentaje_de(ars('1200000')) == Decimal('50.00')


def test_porcentaje_de_rounds_half_up_to_requested_decimals() -> None:
    assert ars('1').porcentaje_de(ars('3')) == Decimal('33.33')
    assert ars('2').porcentaje_de(ars('3'), decimales=1) == Decimal('66.7')


def test_porcentaje_de_with_zero_base_is_a_validation_error() -> None:
    with pytest.raises(ValidacionError):
        ars('100').porcentaje_de(ars('0'))


def test_porcentaje_de_with_different_currency_raises() -> None:
    with pytest.raises(MonedaIncompatible):
        ars('100').porcentaje_de(usd('1000'))


# --- redondear ------------------------------------------------------------


@pytest.mark.parametrize(
    ('entrada', 'esperado'),
    [
        ('10.005', '10.01'),  # mitad hacia arriba (no "bancario")
        ('10.004', '10.00'),
        ('10.015', '10.02'),
        ('-10.005', '-10.01'),
    ],
)
def test_redondear_applies_half_up_to_two_decimals(
    entrada: str, esperado: str
) -> None:
    assert ars(entrada).redondear().monto == Decimal(esperado)


def test_intermediate_results_keep_full_precision_until_redondear() -> None:
    un_tercio = ars('100').multiplicar(Decimal(1) / Decimal(3))

    assert un_tercio.monto != Decimal('33.33')
    assert un_tercio.redondear().monto == Decimal('33.33')


# --- comparación y texto --------------------------------------------------


def test_amounts_of_the_same_currency_can_be_ordered() -> None:
    montos = [ars('700'), ars('500'), ars('600')]

    assert sorted(montos) == [ars('500'), ars('600'), ars('700')]
    assert max(montos) == ars('700')
    assert ars('500') <= ars('500')


def test_ordering_across_currencies_raises() -> None:
    with pytest.raises(MonedaIncompatible):
        _ = ars('1') < usd('1')


def test_str_shows_currency_and_rounded_amount() -> None:
    assert str(ars('600000')) == 'ARS 600000.00'
    assert str(usd('1500.555')) == 'USD 1500.56'


def test_unsupported_amount_types_are_rejected() -> None:
    with pytest.raises(TypeError):
        Dinero(None, Moneda.ARS)  # type: ignore[arg-type]


def test_ordering_against_a_non_dinero_is_not_supported() -> None:
    with pytest.raises(TypeError):
        _ = ars('1') < 1  # type: ignore[operator]
