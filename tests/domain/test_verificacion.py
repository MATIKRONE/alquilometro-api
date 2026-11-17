from datetime import date
from decimal import Decimal

import pytest

from alquilometro_api.domain.ajuste import AjusteIndice, IndicesEnMemoria
from alquilometro_api.domain.dinero import Dinero
from alquilometro_api.domain.errores import MonedaIncompatible
from alquilometro_api.domain.moneda import Moneda
from alquilometro_api.domain.verificacion import (
    ResultadoVerificacion,
    verificar_ajuste,
)

INICIO = date(2026, 1, 1)
PRIMER_AJUSTE = date(2026, 4, 1)
SEGUNDO_AJUSTE = date(2026, 7, 1)
TRIMESTRAL = 3


def pesos(monto: str) -> Dinero:
    return Dinero(Decimal(monto), Moneda.ARS)


@pytest.fixture
def mecanismo() -> AjusteIndice:
    """ICL de ejemplo: 100 en enero, 130 en abril, 169 en julio."""
    indices = IndicesEnMemoria()
    indices.cargar('ICL', INICIO, '100')
    indices.cargar('ICL', PRIMER_AJUSTE, '130')
    indices.cargar('ICL', SEGUNDO_AJUSTE, '169')
    return AjusteIndice('ICL', indices)


def verificar(
    mecanismo: AjusteIndice, fecha: date, informado: Dinero
) -> ResultadoVerificacion:
    return verificar_ajuste(
        mecanismo, pesos('500000'), INICIO, fecha, TRIMESTRAL, informado
    ).resultado


def test_monto_correcto(mecanismo: AjusteIndice) -> None:
    resultado = verificar(mecanismo, SEGUNDO_AJUSTE, pesos('845000'))

    assert resultado is ResultadoVerificacion.CORRECTO


def test_detecta_el_encadenamiento(mecanismo: AjusteIndice) -> None:
    # 650.000 (lo que pagaba) × 1,69 (variación desde el inicio)
    resultado = verificar(mecanismo, SEGUNDO_AJUSTE, pesos('1098500'))

    assert resultado is ResultadoVerificacion.ENCADENADO


def test_otra_diferencia_no_se_confunde_con_encadenamiento(
    mecanismo: AjusteIndice,
) -> None:
    resultado = verificar(mecanismo, SEGUNDO_AJUSTE, pesos('900000'))

    assert resultado is ResultadoVerificacion.DIFERENCIA


def test_en_el_primer_ajuste_no_hay_encadenamiento_posible(
    mecanismo: AjusteIndice,
) -> None:
    resultado = verificar(mecanismo, PRIMER_AJUSTE, pesos('700000'))

    assert resultado is ResultadoVerificacion.DIFERENCIA


def test_informa_diferencia_y_porcentaje(mecanismo: AjusteIndice) -> None:
    verificacion = verificar_ajuste(
        mecanismo,
        pesos('500000'),
        INICIO,
        SEGUNDO_AJUSTE,
        TRIMESTRAL,
        pesos('1098500'),
    )

    assert verificacion.monto_esperado == pesos('845000')
    assert verificacion.diferencia == pesos('253500')
    assert verificacion.diferencia_porcentual == Decimal('30.00')
    assert 'monto base' in verificacion.explicacion


def test_compara_despues_de_redondear(mecanismo: AjusteIndice) -> None:
    resultado = verificar(mecanismo, SEGUNDO_AJUSTE, pesos('845000.004'))

    assert resultado is ResultadoVerificacion.CORRECTO


def test_no_mezcla_monedas(mecanismo: AjusteIndice) -> None:
    dolares = Dinero(Decimal(845000), Moneda.USD)

    with pytest.raises(MonedaIncompatible):
        verificar(mecanismo, SEGUNDO_AJUSTE, dolares)
