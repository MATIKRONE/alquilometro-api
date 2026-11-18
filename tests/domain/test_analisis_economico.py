from decimal import Decimal

import pytest

from alquilometro_api.domain.analisis_economico import AnalisisEconomico
from alquilometro_api.domain.desglose_costo import CostoEntrada, DesgloseCosto
from alquilometro_api.domain.dinero import Dinero
from alquilometro_api.domain.errores import MonedaIncompatible
from alquilometro_api.domain.moneda import Moneda


def pesos(monto: str) -> Dinero:
    return Dinero(Decimal(monto), Moneda.ARS)


def test_calcula_que_porcentaje_del_ingreso_representa_el_costo() -> None:
    costo_real = DesgloseCosto(
        alquiler=pesos('650000'),
        expensas=pesos('85000'),
        abl=pesos('12000'),
        seguro_caucion=pesos('180000'),
        duracion_contrato_meses=24,
    )
    analisis = AnalisisEconomico(
        costo_real=costo_real,
        ingreso_referencia=pesos('1500000'),
        costo_entrada=CostoEntrada(primer_mes=pesos('650000')),
    )

    assert analisis.porcentaje_ingreso == Decimal('50.30')


def test_no_calcula_porcentaje_con_monedas_distintas() -> None:
    costo_real = DesgloseCosto(alquiler=pesos('650000'))
    ingreso_en_dolares = Dinero(Decimal('1500'), Moneda.USD)
    analisis = AnalisisEconomico(
        costo_real=costo_real,
        ingreso_referencia=ingreso_en_dolares,
        costo_entrada=CostoEntrada(primer_mes=pesos('650000')),
    )

    with pytest.raises(MonedaIncompatible):
        analisis.porcentaje_ingreso
