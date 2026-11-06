import pytest

from alquilometro_api.domain.moneda import Moneda


@pytest.mark.parametrize('moneda', list(Moneda))
def test_every_currency_has_a_rounding_rule(moneda: Moneda) -> None:
    assert moneda.decimales >= 0


def test_currency_is_built_from_its_code() -> None:
    assert Moneda('ARS') is Moneda.ARS
    assert Moneda('USD') is Moneda.USD
