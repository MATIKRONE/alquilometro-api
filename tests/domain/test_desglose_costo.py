from decimal import Decimal

from alquilometro_api.domain.desglose_costo import DesgloseCosto
from alquilometro_api.domain.dinero import Dinero
from alquilometro_api.domain.moneda import Moneda


def pesos(monto: str) -> Dinero:
    return Dinero(Decimal(monto), Moneda.ARS)


def test_calcula_el_total_con_todos_los_costos_informados() -> None:
    desglose = DesgloseCosto(
        alquiler=pesos('650000'),
        expensas=pesos('85000'),
        abl=pesos('12000'),
        seguro_caucion=pesos('180000'),
        duracion_contrato_meses=24,
    )

    assert desglose.total == pesos('754500')
    assert desglose.faltantes == []
    assert desglose.componentes_informados[
        'seguro_caucion_prorrateado'
    ] == pesos('7500')


def test_informa_los_componentes_que_faltan() -> None:
    desglose = DesgloseCosto(alquiler=pesos('650000'))

    assert desglose.componentes_informados == {
        'alquiler': pesos('650000'),
    }
    assert desglose.faltantes == [
        'expensas',
        'abl',
        'seguro_caucion',
    ]
    assert desglose.total == pesos('650000')


def test_cero_es_un_valor_informado_y_no_un_faltante() -> None:
    desglose = DesgloseCosto(
        alquiler=pesos('650000'),
        expensas=pesos('0'),
    )

    assert desglose.componentes_informados['expensas'] == pesos('0')
    assert desglose.faltantes == ['abl', 'seguro_caucion']


def test_seguro_sin_duracion_se_marca_como_incompleto() -> None:
    desglose = DesgloseCosto(
        alquiler=pesos('650000'),
        seguro_caucion=pesos('180000'),
    )

    assert 'duracion_contrato_meses' in desglose.faltantes
    assert 'seguro_caucion_prorrateado' not in desglose.componentes_informados
