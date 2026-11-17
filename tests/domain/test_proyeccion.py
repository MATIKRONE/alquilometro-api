from datetime import date
from decimal import Decimal

import pytest

from alquilometro_api.domain.ajuste import AjusteFijo, AjusteIndice
from alquilometro_api.domain.dinero import Dinero
from alquilometro_api.domain.errores import (
    IndiceNoDisponible,
    ValidacionError,
)
from alquilometro_api.domain.moneda import Moneda
from alquilometro_api.domain.proyeccion import (
    OrigenEscenario,
    escenario_desde_historia,
    escenario_indicado,
    indices_proyectados,
    proyectar,
)

INICIO = date(2026, 1, 1)
TRIMESTRAL = 3
ANUAL = 12
AJUSTES_AL_MES_12 = 3
AJUSTES_AL_MES_24 = 7


def pesos(monto: str) -> Dinero:
    return Dinero(Decimal(monto), Moneda.ARS)


def test_ajuste_fijo_a_12_y_24_meses() -> None:
    meses = proyectar(
        AjusteFijo('10'),
        pesos('500000'),
        pesos('100000'),
        INICIO,
        TRIMESTRAL,
        pesos('2000000'),
    )

    mes_12, mes_24 = meses
    assert mes_12.ajustes_aplicados == AJUSTES_AL_MES_12
    assert mes_12.alquiler == pesos('665500')  # 500.000 × 1,1³
    assert mes_12.costo_mensual == pesos('765500')
    assert mes_12.porcentaje_ingreso == Decimal('38.28')
    assert mes_24.ajustes_aplicados == AJUSTES_AL_MES_24
    assert mes_24.alquiler == pesos('974358.55')  # 500.000 × 1,1⁷


def test_si_todavia_no_hay_ajustes_se_paga_el_inicial() -> None:
    mes_12, _ = proyectar(
        AjusteFijo('10'), pesos('500000'), pesos('0'), INICIO, ANUAL, None
    )

    assert mes_12.ajustes_aplicados == 0
    assert mes_12.alquiler == pesos('500000')


def test_sin_ingreso_o_en_otra_moneda_no_hay_porcentaje() -> None:
    dolares = Dinero(Decimal(2000), Moneda.USD)

    con_dolares, _ = proyectar(
        AjusteFijo('10'), pesos('500000'), pesos('0'), INICIO, 3, dolares
    )

    assert con_dolares.porcentaje_ingreso is None


def test_el_escenario_historico_promedia_los_ultimos_12_meses() -> None:
    serie = [Decimal(100) * Decimal('1.02') ** mes for mes in range(13)]

    escenario = escenario_desde_historia(serie)

    assert escenario.tasa_mensual_porcentual == Decimal('2.00')
    assert escenario.origen is OrigenEscenario.PROMEDIO_ULTIMOS_12_MESES


def test_con_menos_de_un_anio_de_historia_pide_una_tasa() -> None:
    with pytest.raises(IndiceNoDisponible):
        escenario_desde_historia([Decimal(100), Decimal(102)])


def test_la_tasa_indicada_no_puede_ser_negativa() -> None:
    with pytest.raises(ValidacionError):
        escenario_indicado(Decimal(-1))


def test_por_indice_proyecta_con_la_misma_estrategia() -> None:
    """Escenario del 2% mensual: al mes 12 van 3 ajustes (mes 9)."""
    indices = indices_proyectados(
        'ICL', INICIO, Decimal(100), escenario_indicado(Decimal(2))
    )

    mes_12, _ = proyectar(
        AjusteIndice('ICL', indices),
        pesos('500000'),
        pesos('0'),
        INICIO,
        TRIMESTRAL,
        None,
    )

    esperado = pesos('500000').multiplicar(Decimal('1.02') ** 9).redondear()
    assert mes_12.alquiler == esperado
    assert 'ICL' in mes_12.formula
